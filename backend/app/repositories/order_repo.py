from typing import Optional, List
from sqlalchemy.orm import Session
from decimal import Decimal
from backend.app.models.order import Order, Trade, OrderStatus

class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def list_by_portfolio_id(
        self,
        portfolio_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Order]:
        query = self.db.query(Order).filter(Order.portfolio_id == portfolio_id)
        if status:
            query = query.filter(Order.status == status)
        return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    def list_trades_by_portfolio_id(
        self,
        portfolio_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        return self.db.query(Trade)\
            .filter(Trade.portfolio_id == portfolio_id)\
            .order_by(Trade.executed_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    def list_trades_by_user_id(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[Trade]:
        return self.db.query(Trade)\
            .join(Order)\
            .join(Order.portfolio)\
            .filter(Order.portfolio.has(user_id=user_id))\
            .order_by(Trade.executed_at.desc())\
            .limit(limit)\
            .all()
