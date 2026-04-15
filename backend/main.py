"""
G-Mini Agent - Entry point del backend.
Levanta FastAPI + Socket.IO montado en ASGI.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Agregar el directorio raiz al path para imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import socketio
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api.routes import router as api_router
from backend.api.websocket_handler import sio, set_agent_core
from backend.automation.editor_bridge import get_editor_bridge
from backend.automation.extension_bridge import get_bridge
from backend.config import config
from backend.core.agent import AgentCore
from backend.core.gateway_service import get_gateway
from backend.core.scheduler import get_scheduler
from backend.utils.logger import logger  # noqa: F811 - configura loguru


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("=" * 60)
    logger.info("  G-Mini Agent - Backend Starting")
    logger.info(f"  Version: {config.get('app', 'version', default='0.1.0')}")
    logger.info("=" * 60)

    agent_core = AgentCore()
    await agent_core.initialize()
    set_agent_core(agent_core)
    logger.info("AgentCore inicializado y conectado al WebSocket handler")

    gateway = get_gateway()
    gateway.attach_socket_server(sio)
    gateway.attach_agent_core(agent_core)
    await gateway.initialize()
    logger.info("GatewayService inicializado")

    scheduler = get_scheduler()
    await scheduler.initialize()
    logger.info("SchedulerService inicializado")

    # Auto-create weekly budget report cron job if not exists
    try:
        existing_jobs = await scheduler.list_jobs()
        has_report_job = any(
            j.get("name") == "budget_weekly_report" for j in existing_jobs
        )
        if not has_report_job:
            await scheduler.create_job(
                name="budget_weekly_report",
                task_type="budget_weekly_report",
                payload={},
                trigger_type="cron",
                cron_expression="0 9 * * 1",  # Every Monday 9am UTC
                enabled=True,
            )
            logger.info("Job cron budget_weekly_report creado automáticamente")
        else:
            logger.debug("Job budget_weekly_report ya existe, saltando creación")
    except Exception as exc:
        logger.warning(f"No se pudo crear job budget_weekly_report: {exc}")

    try:
        yield
    finally:
        await scheduler.shutdown()
        await gateway.shutdown()
        # Cerrar sesiones MCP persistentes
        try:
            if agent_core._planner and hasattr(agent_core._planner, '_mcp_runtime'):
                agent_core._planner._mcp_runtime.shutdown()
                logger.info("MCPSessionPool cerrado correctamente")
        except Exception as exc:
            logger.warning(f"Error cerrando MCPSessionPool: {exc}")
        try:
            await agent_core.shutdown()
        except Exception as exc:
            logger.warning(f"No se pudo cerrar AgentCore limpiamente: {exc}")
        logger.info("G-Mini Agent - Backend Shutting Down")


def create_app() -> socketio.ASGIApp:
    """Crea y configura la aplicacion FastAPI + Socket.IO."""
    app = FastAPI(
        title="G-Mini Agent",
        version=config.get("app", "version", default="0.1.0"),
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("server", "cors_origins", default=["http://127.0.0.1:8765", "http://localhost:8765"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    ext_bridge = get_bridge()
    editor_bridge = get_editor_bridge()

    @app.websocket("/ws/extension")
    async def ws_extension(ws: WebSocket):
        await ext_bridge.handle_websocket(ws)

    @app.websocket("/ws/editor")
    async def ws_editor(ws: WebSocket):
        await editor_bridge.handle_websocket(ws)

    return socketio.ASGIApp(sio, other_asgi_app=app)


def main():
    """Entry point."""
    host = config.get("server", "host", default="127.0.0.1")
    port = config.get("server", "port", default=8765)

    logger.info(f"Iniciando servidor en {host}:{port}")
    app = create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
