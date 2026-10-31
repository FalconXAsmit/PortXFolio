from typing import Optional, List
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timezone
from backend.app.models.portfolio import Portfolio, Holding, Transaction, TransactionType
from backend.app.schemas.portfolio import PortfolioCreate

class PortfolioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, portfolio_id: int) -> Optional[Portfolio]:
        return self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    def list_by_user_id(self, user_id: int) -> List[Portfolio]:
        return self.db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc()).all()

    def create(self, user_id: int, obj_in: PortfolioCreate) -> Portfolio:
        db_obj = Portfolio(
            user_id=user_id,
            name=obj_in.name,
            description=obj_in.description,
            initial_cash=obj_in.initial_cash,
            cash_balance=obj_in.initial_cash,
            currency="INR"
        )
        self.db.add(db_obj)
        self.db.flush()

        # Initial deposit transaction
        tx = Transaction(
            portfolio_id=db_obj.id,
            type=TransactionType.DEPOSIT.value,
            amount=obj_in.initial_cash,
            balance_after=obj_in.initial_cash,
            notes="Initial portfolio funding"
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_holding(self, portfolio_id: int, symbol_id: int) -> Optional[Holding]:
        return self.db.query(Holding)\
            .filter(Holding.portfolio_id == portfolio_id, Holding.symbol_id == symbol_id)\
            .first()

    def list_holdings(self, portfolio_id: int) -> List[Holding]:
        return self.db.query(Holding).filter(Holding.portfolio_id == portfolio_id, Holding.quantity > 0).all()

    def add_transaction(
        self,
        portfolio_id: int,
        tx_type: str,
        amount: Decimal,
        balance_after: Decimal,
        notes: Optional[str] = None
    ) -> Transaction:
        tx = Transaction(
            portfolio_id=portfolio_id,
            type=tx_type,
            amount=amount,
            balance_after=balance_after,
            notes=notes
        )
        self.db.add(tx)
        return tx

    def list_transactions(self, portfolio_id: int, limit: int = 100) -> List[Transaction]:
        return self.db.query(Transaction)\
            .filter(Transaction.portfolio_id == portfolio_id)\
            .order_by(Transaction.created_at.desc())\
            .limit(limit)\
            .all()
