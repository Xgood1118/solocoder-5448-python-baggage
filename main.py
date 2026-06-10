from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import settings
from app.modules.baggage import router as baggage_router
from app.modules.flight import router as flight_router
from app.modules.scan import router as scan_router
from app.modules.claim import router as claim_router
from app.modules.lost import router as lost_router
from app.modules.statistics import router as statistics_router
from app.modules.simulator import router as simulator_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[START] Baggage Tracking Service on port {settings.PORT}")
    print(f"[INFO]  Environment: {settings.ENV}")
    print(f"[INFO]  Lost threshold: {settings.LOST_THRESHOLD_MINUTES} minutes")
    print(f"[INFO]  Domestic delay compensation: {settings.DELAY_DOMESTIC_HOURS}h")
    print(f"[INFO]  International delay compensation: {settings.DELAY_INTL_HOURS}h")
    yield
    print("[STOP] Baggage Tracking Service shutting down...")


app = FastAPI(
    title="Baggage Tracking API",
    description="航空公司行李全程追踪后端服务 - 从值机到离场全链路追踪",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(baggage_router)
app.include_router(flight_router)
app.include_router(scan_router)
app.include_router(claim_router)
app.include_router(lost_router)
app.include_router(statistics_router)
app.include_router(simulator_router)


@app.get("/")
async def root():
    return {
        "service": "Baggage Tracking API",
        "version": "1.0.0",
        "status": "running",
        "modules": ["baggage", "flight", "scan", "claim", "lost", "statistics", "simulator"],
    }


@app.get("/health")
async def health_check():
    from app.storage.memory import storage
    return {
        "status": "healthy",
        "baggage_count": storage.stats_baggage_count(),
        "flight_count": storage.stats_flight_count(),
        "scan_count": storage.stats_scan_count(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
