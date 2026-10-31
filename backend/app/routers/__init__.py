from backend.app.routers.auth import router as auth_router
from backend.app.routers.market import router as market_router
from backend.app.routers.orders import router as orders_router
from backend.app.routers.portfolios import router as portfolios_router
from backend.app.routers.backtests import router as backtests_router
from backend.app.routers.forecasts import router as forecasts_router
from backend.app.routers.alerts import router as alerts_router
from backend.app.routers.reports import router as reports_router
from backend.app.routers.health import router as health_router
from backend.app.routers.admin import router as admin_router

__all__ = [
    "auth_router",
    "market_router",
    "orders_router",
    "portfolios_router",
    "backtests_router",
    "forecasts_router",
    "alerts_router",
    "reports_router",
    "health_router",
    "admin_router"
]
