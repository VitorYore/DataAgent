import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.analysis import AnalysisRunner
from src.history.analysis_history import listar_historico, obter_analise, comparar_analises
from src.history.history_index import listar_indice, obter_resumo
from src.analytics.comparison import comparar_resumos
from src.ingestion.report_normalizer import StructuralReviewRequired

REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "resumo_executivo.json"


def create_app(report_path: Path = REPORT_PATH, uploads_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="DataAgent API", version="0.7.0")
    # Origens locais explícitas; rever antes do deploy.
    app.add_middleware(
        CORSMiddleware,
        # Vite pode escolher 5174 quando 5173 já está ocupada.
        allow_origins=[
            "http://localhost:5173", "http://127.0.0.1:5173",
            "http://localhost:5174", "http://127.0.0.1:5174",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )
    runner = AnalysisRunner(uploads_path or REPORT_PATH.parents[1] / "data/uploads", report_path)
    app.state.analysis_runner = runner

    @app.exception_handler(StructuralReviewRequired)
    async def structural_review(request, error):
        return JSONResponse(status_code=422, content={'detail': error.detalhe_publico(), 'diagnostico_estrutural': error.diagnostico})

    def ler_historico(limit=None, offset=0):
        try:
            return listar_indice(runner.history, limit=limit, offset=offset)
        except (OSError, ValueError):
            logging.getLogger('uvicorn.error').exception('Falha ao ler histórico')
            raise HTTPException(500, 'Não foi possível ler o histórico de análises.')

    @app.get('/api/analysis/history')
    def history(limit: int | None = None, offset: int = 0):
        return JSONResponse(ler_historico(limit, offset), headers={'Cache-Control': 'no-store'})

    @app.get('/api/analysis/history/{analysis_id}')
    def history_item(analysis_id: str):
        try:
            return obter_analise(analysis_id, runner.history)
        except FileNotFoundError:
            raise HTTPException(404, 'Análise não encontrada.')
        except (OSError, ValueError):
            logging.getLogger('uvicorn.error').exception('Falha ao ler análise histórica')
            raise HTTPException(500, 'Não foi possível ler a análise histórica.')

    @app.get('/api/analysis/compare')
    def comparison(left: str | None = None, right: str | None = None):
        registros = ler_historico()
        by_id = {item['id']: item for item in registros}
        if left is not None or right is not None:
            left_item, right_item = by_id.get(left or ''), by_id.get(right or '')
            if left and left == right:
                raise HTTPException(400, 'Selecione duas análises diferentes.')
            if left_item is None or right_item is None:
                raise HTTPException(404, 'Uma das análises selecionadas não foi encontrada.')
        else:
            left_item = registros[1] if len(registros) > 1 else None
            right_item = registros[0] if registros else None
        if left_item is None or right_item is None:
            return JSONResponse(comparar_analises(right_item, left_item), headers={'Cache-Control': 'no-store'})
        try:
            left_summary = obter_resumo(left_item['id'], runner.history)
            right_summary = obter_resumo(right_item['id'], runner.history)
        except FileNotFoundError:
            return JSONResponse(comparar_analises(right_item, left_item), headers={'Cache-Control': 'no-store'})
        result = comparar_resumos(left_summary, right_summary, left_item, right_item)
        result['status'] = 'disponivel'
        result['metricas'] = comparar_analises(right_item, left_item).get('metricas', {})
        return JSONResponse(result, headers={'Cache-Control': 'no-store'})

    @app.middleware("http")
    async def log_analysis_request(request, call_next):
        if request.method != "POST" or request.url.path != "/api/analysis":
            return await call_next(request)
        logger = logging.getLogger("uvicorn.error")
        logger.info("POST /api/analysis recebido: origin=%s content-length=%s",
                    request.headers.get("origin"), request.headers.get("content-length"))
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("POST /api/analysis falhou antes de preparar a resposta")
            raise
        logger.info("POST /api/analysis resposta HTTP %s", response.status_code)
        return response

    @app.get("/api/analysis/status")
    def analysis_status():
        return {"status": runner.status}

    @app.post("/api/analysis")
    def analyze(files: list[UploadFile] = File(default=[])):
        return runner.analyze(files)

    @app.get("/api/analysis/{analysis_id}/mapping")
    def pending_mapping(analysis_id: str):
        return runner.get_mapping(analysis_id)

    @app.post("/api/analysis/{analysis_id}/mapping")
    def confirm_mapping(analysis_id: str, payload: dict = Body(...)):
        mappings = payload.get("mappings") if isinstance(payload, dict) else None
        if not isinstance(mappings, dict):
            raise HTTPException(422, "O corpo deve conter o objeto mappings.")
        return runner.confirm_mapping(analysis_id, mappings)

    @app.get("/api/analysis/{analysis_id}/entities")
    def entities(analysis_id: str):
        return JSONResponse(runner.get_entities(analysis_id), headers={"Cache-Control": "no-store"})

    @app.post("/api/analysis/{analysis_id}/entities")
    def decide_entities(analysis_id: str, payload: dict = Body(...)):
        return runner.decide_entity(analysis_id, payload)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "DataAgent API"}

    @app.get("/api/analysis/latest")
    def latest_analysis():
        try:
            with report_path.open(encoding="utf-8") as report:
                content = json.load(report)
            if not isinstance(content, dict):
                raise ValueError("O relatório deve ser um objeto JSON.")
            return JSONResponse(content=content, headers={"Cache-Control": "no-store"})
        except FileNotFoundError as error:
            raise HTTPException(404, "Nenhuma análise disponível.") from error
        except (ValueError, UnicodeError) as error:
            raise HTTPException(500, "O arquivo da análise contém JSON inválido.") from error
        except OSError as error:
            raise HTTPException(500, "Não foi possível ler o arquivo da análise.") from error

    @app.get('/api/analysis/{analysis_id}')
    def analysis_detail(analysis_id: str):
        try:
            return JSONResponse(obter_resumo(analysis_id, runner.history), headers={'Cache-Control': 'no-store'})
        except FileNotFoundError:
            raise HTTPException(404, 'Relatório completo da análise não encontrado.')
        except (OSError, ValueError):
            logging.getLogger('uvicorn.error').exception('Falha ao abrir relatório histórico %s', analysis_id)
            raise HTTPException(500, 'Não foi possível abrir a análise histórica.')

    return app


app = create_app()
