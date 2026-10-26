"""应用装配：只负责创建实例、挂中间件、挂路由与静态资源，不含业务逻辑。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.routes import router
from app.core import config as cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def _mount_frontend(app: FastAPI) -> None:
    if not FRONTEND_DIR.exists():
        return
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")


def create_app() -> FastAPI:
    # 生产环境不暴露 /docs 与 /openapi.json，对外契约只以 docs/openapi.yaml 为准
    app = FastAPI(
        title=cfg.APP_NAME,
        version=cfg.APP_VERSION,
        docs_url=None if cfg.IS_PROD else "/docs",
        redoc_url=None if cfg.IS_PROD else "/redoc",
        openapi_url=None if cfg.IS_PROD else "/openapi.json",
    )

    if cfg.IS_PROD and not cfg.CORS_ALLOW_ORIGINS:
        logger.warning("APP_ENV=%s 且 CORS_ALLOW_ORIGINS 为空：将不放行任何跨域来源", cfg.APP_ENV)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.CORS_ALLOW_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
        allow_credentials=False,
    )

    register_exception_handlers(app)
    app.include_router(router)
    _mount_frontend(app)
    return app


app = create_app()
