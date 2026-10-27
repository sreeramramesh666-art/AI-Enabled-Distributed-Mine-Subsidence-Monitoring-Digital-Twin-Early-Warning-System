import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.db.database import Base, engine, SessionLocal
from backend.app.realtime.websocket_manager import ws_manager
from backend.app.simulator.engine import simulator_engine
from backend.app.ingestion.mqtt_client import mqtt_gateway

# Import API routes
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.nodes import router as nodes_router
from backend.app.api.routes.telemetry import router as telemetry_router
from backend.app.api.routes.alerts import router as alerts_router
from backend.app.api.routes.analytics import router as analytics_router
from backend.app.api.routes.reports import router as reports_router
from backend.app.api.routes.simulator import router as simulator_router
from backend.app.api.routes.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    # Populate default nodes if empty
    db = SessionLocal()
    try:
        simulator_engine.ensure_default_nodes(db)
    finally:
        db.close()

    # Initialize MQTT client if enabled
    mqtt_gateway.initialize()
    mqtt_gateway.start(loop=asyncio.get_running_loop())

    # Optional simulator autostart
    if settings.SIMULATOR_AUTOSTART:
        await simulator_engine.start()

    yield

    # Shutdown
    logger.info("Initiating graceful shutdown...")
    if simulator_engine.is_running:
        await simulator_engine.stop()
    mqtt_gateway.stop()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SIH26025 Mine Subsidence Monitoring & Early-Warning Industrial Geotechnical System",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket streaming endpoint
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for ping/pong or client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client terminated: {e}")
        ws_manager.disconnect(websocket)


# Register API v1 routes
api_prefix = "/api/v1"
app.include_router(health_router, prefix=api_prefix)
app.include_router(nodes_router, prefix=api_prefix)
app.include_router(telemetry_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(simulator_router, prefix=api_prefix)
app.include_router(settings_router, prefix=api_prefix)


@app.get("/")
def root_redirect():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "api_v1": "/api/v1/health"
    }
