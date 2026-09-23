"""Upload isolado e execução retomável do pipeline DataAgent."""
import json
import logging
import re
import shutil
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import perf_counter

import pandas as pd
from fastapi import HTTPException, UploadFile

from main import executar_dataagent, executar_pipeline_analitico, continuar_analytics
from src.analytics.assisted_mapping import SemanticMappingRequired, conceitos_publicos, validar_mapeamentos
from src.history.analysis_history import novo_analysis_id, salvar_analise_historico, obter_analise
from src.history.history_index import persistir_resumo, obter_resumo, _atomic
from src.quality.entity_decisions import preparar_revisao, validar_decisao, registrar_decisao
from src.ingestion.report_normalizer import StructuralReviewRequired
from src.reports.analysis_report import converter_para_json

logger = logging.getLogger("uvicorn.error")
EXTENSIONS = {".csv", ".xlsx", ".xls"}
ANALYSIS_ID = re.compile(r"analysis_\d{8}_\d{12}_[0-9a-f]{32}")


class AnalysisRunner:
    def __init__(self, uploads: Path, report: Path):
        self.uploads = uploads.resolve()
        self.report = report.resolve()
        self.history = self.report.parent.parent / "data/analysis_history"
        self.lock = threading.Lock()
        self.status = "idle"

    def analyze(self, files: list[UploadFile]) -> dict:
        started = perf_counter()
        logger.info("Upload recebido: arquivos=%s nomes=%r", len(files), [file.filename for file in files])
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, "Uma análise já está em andamento.")
        self.status = "processing"
        workspace = None
        preserve_workspace = False
        try:
            if not files:
                raise HTTPException(400, "Envie pelo menos um arquivo.")
            names = self._validate_names(files)
            self.uploads.mkdir(parents=True, exist_ok=True)
            analysis_id = novo_analysis_id()
            workspace = self._workspace(analysis_id)
            workspace.mkdir(exist_ok=False)
            inputs = workspace / "input"
            inputs.mkdir()
            for upload, name in zip(files, names):
                destination = (inputs / name).resolve()
                if destination.parent != inputs:
                    raise HTTPException(400, "Nome de arquivo inválido.")
                with destination.open("xb") as output:
                    shutil.copyfileobj(upload.file, output, length=1024 * 1024)
                if destination.stat().st_size == 0:
                    raise HTTPException(400, f"O arquivo {name} está vazio.")
                logger.info("Arquivo salvo: analysis_id=%s nome=%s bytes=%s", analysis_id, name, destination.stat().st_size)
            logger.info("Pipeline iniciado: analysis_id=%s entrada=%s", analysis_id, inputs)
            summary = executar_dataagent(inputs, workspace, estrito=True, analysis_id=analysis_id)
            logger.info("Pipeline finalizado: analysis_id=%s duracao=%.3fs", analysis_id, perf_counter() - started)
            return self._complete(summary, workspace, names, analysis_id, len(files), started)
        except SemanticMappingRequired as error:
            if workspace is None:
                raise RuntimeError("Análise pendente sem diretório persistente.")
            preserve_workspace = True
            analysis_files = error.analysis_files or [{"nome": name, "linhas": None, "colunas": None} for name in names]
            context = {
                "analysis_id": analysis_id, "status": "mapping_required", "files": names,
                "files_processed": len(names), "analysis_files": analysis_files,
                "automatic_mappings": error.automatic_mappings,
                "detected_columns": error.detected_columns,
                "required_mappings": error.required_mappings,
            }
            error.dataframe.to_pickle(workspace / "working_dataframe.pkl")
            (workspace / "mapping_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
            self.status = "mapping_required"
            logger.info("Mapeamento pendente: analysis_id=%s colunas_ambíguas=%s", analysis_id, len(error.required_mappings))
            return {
                "status": "mapping_required", "analysis_id": analysis_id,
                "message": "Os dados foram estruturados, mas alguns campos precisam ser confirmados.",
                "detected_columns": error.detected_columns,
                "automatic_mappings": error.automatic_mappings,
                "required_mappings": error.required_mappings,
                "concepts": conceitos_publicos(),
            }
        except StructuralReviewRequired as error:
            self.status = "error"
            self.report.parent.mkdir(parents=True, exist_ok=True)
            (self.report.parent / "diagnostico_estrutural.json").write_text(json.dumps(error.diagnostico, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
            logger.warning("Análise interrompida para revisão estrutural: %s", self.report.parent / "diagnostico_estrutural.json")
            raise
        except HTTPException as error:
            self.status = "error"
            logger.warning("Upload rejeitado: HTTP %s detalhe=%s", error.status_code, error.detail)
            raise
        except ValueError as error:
            self.status = "error"
            logger.exception("Dados não puderam ser processados")
            raise HTTPException(422, "Os dados não puderam ser processados. Verifique os arquivos, colunas e relacionamentos.") from error
        except Exception as error:
            self.status = "error"
            logger.exception("Falha no pipeline DataAgent")
            raise HTTPException(500, "Ocorreu um erro interno durante a análise. Consulte o log do backend.") from error
        finally:
            if workspace is not None and workspace.exists() and not preserve_workspace:
                shutil.rmtree(workspace, ignore_errors=True)
            for upload in files:
                upload.file.close()
            self.lock.release()

    def get_mapping(self, analysis_id: str) -> dict:
        workspace = self._workspace(analysis_id)
        path = workspace / "mapping_context.json"
        if not path.is_file():
            raise HTTPException(404, "Mapeamento pendente não encontrado.")
        try:
            context = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            logger.exception("Contexto de mapeamento inválido: %s", analysis_id)
            raise HTTPException(500, "Não foi possível recuperar o mapeamento pendente.") from error
        if context.get("status") != "mapping_required":
            raise HTTPException(409, "Esta análise não aguarda mapeamento.")
        return {
            "status": context["status"], "analysis_id": analysis_id,
            "message": "Os dados foram estruturados, mas alguns campos precisam ser confirmados.",
            "detected_columns": context["detected_columns"],
            "automatic_mappings": context["automatic_mappings"],
            "required_mappings": context["required_mappings"], "concepts": conceitos_publicos(),
        }

    def confirm_mapping(self, analysis_id: str, mappings: dict) -> dict:
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, "Uma análise já está em andamento.")
        self.status = "processing"
        try:
            workspace = self._workspace(analysis_id)
            context_path = workspace / "mapping_context.json"
            dataframe_path = workspace / "working_dataframe.pkl"
            if not context_path.is_file() or not dataframe_path.is_file():
                raise HTTPException(404, "Mapeamento pendente não encontrado.")
            context = json.loads(context_path.read_text(encoding="utf-8"))
            if context.get("status") != "mapping_required":
                raise HTTPException(409, "Esta análise não aguarda mapeamento.")
            frame = pd.read_pickle(dataframe_path)
            try:
                confirmed = validar_mapeamentos(frame, mappings)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            started = perf_counter()
            summary = executar_pipeline_analitico(
                frame, origem="Dataset estruturado com mapeamento confirmado",
                diretorio_saida=workspace, arquivos_analisados=context["analysis_files"],
                analysis_id=analysis_id, semantic_mappings=confirmed,
                automatic_mappings=context.get("automatic_mappings", {}),
            )
            logger.info("Pipeline retomado: analysis_id=%s duracao=%.3fs", analysis_id, perf_counter() - started)
            result = self._complete(summary, workspace, context["files"], analysis_id, context["files_processed"], started)
            shutil.rmtree(workspace, ignore_errors=True)
            return result
        except HTTPException:
            self.status = "mapping_required"
            raise
        except ValueError as error:
            self.status = "mapping_required"
            logger.exception("Falha ao retomar pipeline com mapeamento")
            raise HTTPException(422, "Os campos confirmados não puderam ser analisados.") from error
        except Exception as error:
            self.status = "error"
            logger.exception("Falha ao retomar análise %s", analysis_id)
            raise HTTPException(500, "Ocorreu um erro interno durante a análise.") from error
        finally:
            self.lock.release()

    def get_entities(self, analysis_id: str) -> dict:
        self._workspace(analysis_id)
        try:
            summary = obter_resumo(analysis_id, self.history)
        except FileNotFoundError as error:
            raise HTTPException(404, "Análise concluída não encontrada.") from error
        report = summary.get("dados", {}).get("entity_resolution") or {}
        report = preparar_revisao(report, analysis_id)
        report["can_decide"] = (self.history / "working" / analysis_id / "entity_analysis.pkl").is_file()
        report["analysis_id"] = analysis_id
        return report

    def decide_entity(self, analysis_id: str, payload: dict) -> dict:
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, "Uma análise já está em andamento.")
        previous_status = self.status
        try:
            report = self.get_entities(analysis_id)
            candidate = validar_decisao(report, payload)
            previous = obter_resumo(analysis_id, self.history)
            record = obter_analise(analysis_id, self.history)
            if candidate["status"] != "pending":
                return {"status": "success", "files_processed": len(record["arquivos"]), "summary": previous}
            if not report["can_decide"]:
                raise HTTPException(409, "Esta análise antiga não tem intermediário salvo. Execute uma nova análise para aplicar decisões.")
            # O pickle é interno, criado pelo pipeline; nunca recebemos pickle do upload.
            saved = pd.read_pickle(self.history / "working" / analysis_id / "entity_analysis.pkl")
            updated = registrar_decisao(saved["dataframe"], report, payload)
            self.status = "processing"
            started = perf_counter()
            if payload["decision"] == "merge":
                with TemporaryDirectory(prefix="entities-", dir=self.uploads) as folder:
                    summary = continuar_analytics(saved["dataframe"], saved["contexto"], Path(folder), updated)
                if summary["kpis"] != previous["kpis"] or summary.get("temporal") != previous.get("temporal"):
                    raise ValueError("A decisão alteraria indicadores gerais. A análise anterior foi preservada.")
            else:
                summary = previous.copy()
                summary["dados"] = {**previous["dados"], "entity_resolution": updated}
            elapsed = perf_counter() - started
            summary = json.loads(json.dumps(summary, ensure_ascii=False, default=converter_para_json, allow_nan=False))
            record.update(kpis=summary["kpis"], score=summary["status_geral"].get("score"),
                          status=summary["status_geral"].get("status"))
            persistir_resumo(summary, record, self.history)
            if self.report.is_file():
                latest = json.loads(self.report.read_text(encoding="utf-8"))
                if latest.get("analysis_id") == analysis_id:
                    _atomic(self.report, summary)
            logger.info("Decisão de entidade aplicada: analysis_id=%s analytics=%.3fs", analysis_id, elapsed)
            return {"status": "success", "files_processed": len(record["arquivos"]),
                    "summary": summary, "analytics_seconds": round(elapsed, 3)}
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        finally:
            self.status = previous_status
            self.lock.release()

    def _validate_names(self, files: list[UploadFile]) -> list[str]:
        names = []
        for upload in files:
            original = upload.filename or ""
            if "/" in original or "\\" in original or ":" in original:
                raise HTTPException(400, "Nome de arquivo inválido.")
            name = re.sub(r"[^\w. -]", "_", original).strip(" .")
            path = Path(name)
            if not name or path.suffix.lower() not in EXTENSIONS:
                raise HTTPException(400, "Selecione apenas arquivos CSV, XLSX ou XLS.")
            if path.stem.upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
                raise HTTPException(400, "Nome de arquivo inválido.")
            if path.stem.casefold() in {Path(item).stem.casefold() for item in names}:
                raise HTTPException(400, "Os arquivos devem ter nomes de tabela diferentes.")
            names.append(name)
        return names

    def _workspace(self, analysis_id: str) -> Path:
        if not isinstance(analysis_id, str) or not ANALYSIS_ID.fullmatch(analysis_id):
            raise HTTPException(404, "Análise pendente não encontrada.")
        workspace = (self.uploads / analysis_id).resolve()
        if workspace.parent != self.uploads:
            raise HTTPException(404, "Análise pendente não encontrada.")
        return workspace

    def _complete(self, summary, workspace, names, analysis_id, files_processed, started):
        encoded = json.dumps(summary, ensure_ascii=False, indent=4, default=converter_para_json, allow_nan=False)
        summary = json.loads(encoded)
        if not isinstance(summary, dict):
            raise RuntimeError("Pipeline did not return a summary.")
        summary["analysis_id"] = analysis_id
        self.report.parent.mkdir(parents=True, exist_ok=True)
        for name in ("diagnostico.json", "analise.json"):
            shutil.copyfile(workspace / "reports" / name, self.report.parent / name)
        source = workspace / "data/processed/vendas_tratadas.csv"
        if source.is_file():
            processed = self.report.parent.parent / "data" / "processed"
            processed.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, processed / "vendas_tratadas.csv")
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.report.parent, suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                output.write(encoded)
            temporary.replace(self.report)
            logger.info("Resumo publicado: caminho=%s bytes=%s", self.report, self.report.stat().st_size)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        intermediate = workspace / "entity_analysis.pkl"
        if intermediate.is_file():
            archive = self.history / "working" / analysis_id
            archive.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(intermediate, archive / "entity_analysis.pkl")
        history_item = salvar_analise_historico(summary, names, self.history)
        persistir_resumo(summary, history_item, self.history)
        self.status = "completed"
        logger.info("Resposta de análise preparada: status=success arquivos=%s duracao=%.3fs", files_processed, perf_counter() - started)
        return {"status": "success", "files_processed": files_processed, "summary": summary}
