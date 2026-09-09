"""Upload isolado e execução síncrona do pipeline existente."""
import json
import logging
import os
import re
import shutil
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import perf_counter

from fastapi import HTTPException, UploadFile
from main import executar_dataagent
from src.reports.analysis_report import converter_para_json

logger = logging.getLogger("uvicorn.error")
EXTENSIONS = {".csv", ".xlsx", ".xls"}


class AnalysisRunner:
    def __init__(self, uploads: Path, report: Path):
        self.uploads = uploads.resolve()
        self.report = report.resolve()
        self.lock = threading.Lock()
        self.status = "idle"

    def analyze(self, files: list[UploadFile]) -> dict:
        started = perf_counter()
        logger.info("Upload recebido: arquivos=%s nomes=%r", len(files), [file.filename for file in files])
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, "Uma análise já está em andamento.")
        self.status = "processing"
        try:
            if not files:
                raise HTTPException(400, "Envie pelo menos um arquivo.")
            names = []
            for upload in files:
                original = upload.filename or ""
                # Rejeitar caminhos evita ambiguidades entre Windows e POSIX.
                if "/" in original or "\\" in original or ":" in original:
                    raise HTTPException(400, "Nome de arquivo inválido.")
                name = re.sub(r"[^\w. -]", "_", original).strip(" .")
                path = Path(name)
                if not name or path.suffix.lower() not in EXTENSIONS:
                    raise HTTPException(400, "Selecione apenas arquivos CSV, XLSX ou XLS.")
                if path.stem.upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
                    raise HTTPException(400, "Nome de arquivo inválido.")
                if path.stem.casefold() in {Path(n).stem.casefold() for n in names}:
                    raise HTTPException(400, "Os arquivos devem ter nomes de tabela diferentes.")
                names.append(name)

            self.uploads.mkdir(parents=True, exist_ok=True)
            # Um subdiretório por requisição. Nunca apagar samples nem uploads alheios.
            keep_uploads = os.getenv("DATAAGENT_KEEP_UPLOADS") == "1"
            with TemporaryDirectory(prefix="analysis-", dir=self.uploads, delete=not keep_uploads) as directory:
                workspace = Path(directory).resolve()
                if not workspace.is_relative_to(self.uploads):
                    raise RuntimeError("Diretório de análise fora da raiz de uploads.")
                inputs = workspace / "input"
                if keep_uploads:
                    logger.info("Diagnóstico: pasta temporária será preservada em %s", workspace)
                inputs.mkdir()
                for upload, name in zip(files, names):
                    destination = (inputs / name).resolve()
                    if destination.parent != inputs:
                        raise HTTPException(400, "Nome de arquivo inválido.")
                    with destination.open("xb") as output:
                        shutil.copyfileobj(upload.file, output, length=1024 * 1024)
                    if destination.stat().st_size == 0:
                        raise HTTPException(400, f"O arquivo {name} está vazio.")
                    logger.info("Arquivo salvo: caminho=%s bytes=%s", destination, destination.stat().st_size)
                logger.info("Pipeline iniciado: entrada=%s", inputs)
                summary = executar_dataagent(inputs, workspace, estrito=True)
                logger.info("Pipeline finalizado: duracao=%.3fs", perf_counter() - started)
                # Validar serialização antes de substituir a última análise.
                encoded = json.dumps(summary, ensure_ascii=False, indent=4, default=converter_para_json, allow_nan=False)
                summary = json.loads(encoded)
                if not isinstance(summary, dict):
                    raise RuntimeError("O pipeline não retornou um resumo.")
                self.report.parent.mkdir(parents=True, exist_ok=True)
                for name in ("diagnostico.json", "analise.json"):
                    shutil.copyfile(workspace / "reports" / name, self.report.parent / name)
                processed = self.report.parent.parent / "data" / "processed"
                processed.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(workspace / "data/processed/vendas_tratadas.csv", processed / "vendas_tratadas.csv")
                # Rename no mesmo diretório: GET vê o resumo antigo ou o novo completo.
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
            self.status = "completed"
            logger.info("Resposta de análise preparada: status=success arquivos=%s duracao=%.3fs", len(files), perf_counter() - started)
            return {"status": "success", "files_processed": len(files), "summary": summary}
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
            for upload in files:
                upload.file.close()
            self.lock.release()
