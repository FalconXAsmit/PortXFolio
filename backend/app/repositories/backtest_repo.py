from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.backtest import Backtest, BacktestTrade

class BacktestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, backtest_id: int) -> Optional[Backtest]:
        return self.db.query(Backtest).filter(Backtest.id == backtest_id).first()

    def list_by_user_id(self, user_id: int, skip: int = 0, limit: int = 50) -> List[Backtest]:
        return self.db.query(Backtest)\
            .filter(Backtest.user_id == user_id)\
            .order_by(Backtest.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    def delete(self, backtest_id: int, user_id: int) -> bool:
        bt = self.db.query(Backtest).filter(Backtest.id == backtest_id, Backtest.user_id == user_id).first()
        if bt:
            self.db.delete(bt)
            self.db.commit()
            return True
        return False
