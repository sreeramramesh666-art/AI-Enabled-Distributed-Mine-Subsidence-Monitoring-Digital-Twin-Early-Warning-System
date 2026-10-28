import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
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
from backend.app.api.routes.audit import router as audit_router
from backend.app.api.routes.experiments import router as experiments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    # Populate default demonstration nodes if empty
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


# Structured Request Logging & Request-ID Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.perf_counter()

    # Attach request_id to logger context
    extra = {
        "request_id": req_id,
        "client_ip": request.client.host if request.client else "unknown"
    }

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        extra["duration_ms"] = round(duration_ms, 2)

        # Log requests except health probes to avoid noise
        if not request.url.path.endswith("/health") and not request.url.path.endswith("/health/liveness"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code}",
                extra=extra
            )

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        extra["duration_ms"] = round(duration_ms, 2)
        logger.error(
            f"Unhandled exception during {request.method} {request.url.path}: {e}",
            exc_info=True,
            extra=extra
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error occurred processing request."},
            headers={"X-Request-ID": req_id}
        )


# WebSocket streaming endpoint
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
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
app.include_router(audit_router, prefix=api_prefix)
app.include_router(experiments_router, prefix=api_prefix)


@app.get("/")
def root_redirect():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "api_v1": "/api/v1/health"
    }
