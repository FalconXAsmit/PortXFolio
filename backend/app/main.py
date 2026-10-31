from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.core.database import Base, engine
from backend.app.routers import (
    auth_router,
    market_router,
    orders_router,
    portfolios_router,
    backtests_router,
    forecasts_router,
    alerts_router,
    reports_router,
    health_router,
    admin_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    logger.info("Initializing Portfolix Platform...")
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema verified.")
    yield
    logger.info("Shutting down Portfolix Platform...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
# Portfolix: Advanced Stock Trading & Portfolio Management Platform

Production-grade quantitative finance platform featuring:
- **Market Data & Analytics**: Multi-timeframe OHLCV, 10+ technical indicators, cross-asset correlation matrices.
- **Paper Trading Engine**: ACID-compliant order lifecycle (Market/Limit/Stop/Take-Profit), realistic commission and slippage models, position margin safety.
- **Portfolio Analytics & Optimization**: Real-time Mark-to-Market P&L, Sharpe/Sortino/Calmar/VaR/CVaR risk engine, Markowitz Efficient Frontier, Risk Parity, target rebalancing.
- **Event-Driven Backtester**: Zero look-ahead bias strategy simulation, multi-parameter grid search.
- **Quantitative Forecasting & ML Signals**: Machine learning price projections, confidence bands, accuracy metrics.
- **Alerts, Watchlists & Reports**: Customizable threshold alerts, CSV/ledger export.

> **EDUCATIONAL DISCLAIMER**: Portfolix is designed for educational, simulation, and research purposes only. All calculations, signals, forecasts, and metrics do not constitute investment, financial, or trading advice.
    """,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing & disclaimer middleware
@app.middleware("http")
async def add_process_time_and_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-Disclaimer"] = "Portfolix is educational/simulation software, not financial advice."
    return response

# Include API Routers under /api/v1
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(market_router, prefix=settings.API_V1_STR)
app.include_router(orders_router, prefix=settings.API_V1_STR)
app.include_router(portfolios_router, prefix=settings.API_V1_STR)
app.include_router(backtests_router, prefix=settings.API_V1_STR)
app.include_router(forecasts_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(health_router, prefix=settings.API_V1_STR)

# Root status endpoint
@app.get("/")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": "/docs",
        "disclaimer": "Educational/simulation software, not investment advice."
    }
