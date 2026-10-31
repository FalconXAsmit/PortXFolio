from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.core.deps import require_roles
from backend.app.models.user import User
from backend.app.models.market import Symbol, Price
from backend.app.models.portfolio import Portfolio
from backend.app.models.order import Order, Trade
from backend.app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin & System"])

@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]

@router.get("/stats")
def get_system_stats(
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar()
    total_symbols = db.query(func.count(Symbol.id)).scalar()
    total_prices = db.query(func.count(Price.id)).scalar()
    total_portfolios = db.query(func.count(Portfolio.id)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    total_trades = db.query(func.count(Trade.id)).scalar()

    return {
        "total_users": total_users,
        "total_symbols": total_symbols,
        "total_prices": total_prices,
        "total_portfolios": total_portfolios,
        "total_orders": total_orders,
        "total_trades": total_trades
    }
