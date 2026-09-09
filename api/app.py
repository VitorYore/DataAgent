import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.analysis import AnalysisRunner

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

    return app


app = create_app()
