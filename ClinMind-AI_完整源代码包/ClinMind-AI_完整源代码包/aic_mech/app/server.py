"""ClinMind-AI FastAPI Application Server.

Mounts static UI assets, API routing endpoints, WebSocket telemetry feeds,
and configures CORS and error handling.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import config

from app.api.routes_case import router as case_router
from app.api.routes_action import router as action_router
from app.api.routes_eval import router as eval_router
from app.api.routes_config import router as config_router
from app.api.websocket_feed import router as ws_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI web application."""
    app = FastAPI(
        title="ClinMind-AI: 临床决策思维推演与OSCE智能评测系统",
        description="国家级医科临床竞赛系统 - 1Hz血流动力学引擎与拓扑GED思维复盘评测平台",
        version="1.0.0"
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API Routers
    app.include_router(case_router)
    app.include_router(action_router)
    app.include_router(eval_router)
    app.include_router(config_router)
    app.include_router(ws_router)

    # Ensure static directory exists
    config.STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Mount static assets directory
    app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="static")

    @app.get("/")
    async def root():
        """Redirect home route to the emergency room dashboard."""
        return RedirectResponse(url="/static/index.html")

    return app


app = create_app()
