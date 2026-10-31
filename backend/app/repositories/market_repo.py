from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from decimal import Decimal
from backend.app.models.market import Symbol, Price

class MarketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_symbol_by_id(self, symbol_id: int) -> Optional[Symbol]:
        return self.db.query(Symbol).filter(Symbol.id == symbol_id).first()

    def get_symbol_by_ticker(self, ticker: str) -> Optional[Symbol]:
        return self.db.query(Symbol).filter(Symbol.ticker.ilike(ticker.strip())).first()

    def list_symbols(
        self,
        sector: Optional[str] = None,
        search: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[Symbol]:
        query = self.db.query(Symbol).filter(Symbol.is_active == is_active)
        if sector:
            query = query.filter(Symbol.sector.ilike(f"%{sector}%"))
        if search:
            query = query.filter(
                (Symbol.ticker.ilike(f"%{search}%")) |
                (Symbol.name.ilike(f"%{search}%"))
            )
        return query.order_by(Symbol.ticker).offset(skip).limit(limit).all()

    def get_latest_price(self, symbol_id: int) -> Optional[Price]:
        return self.db.query(Price)\
            .filter(Price.symbol_id == symbol_id)\
            .order_by(desc(Price.date))\
            .first()

    def get_previous_price(self, symbol_id: int, before_date: date) -> Optional[Price]:
        return self.db.query(Price)\
            .filter(and_(Price.symbol_id == symbol_id, Price.date < before_date))\
            .order_by(desc(Price.date))\
            .first()

    def get_price_history(
        self,
        symbol_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Price]:
        query = self.db.query(Price).filter(Price.symbol_id == symbol_id)
        if start_date:
            query = query.filter(Price.date >= start_date)
        if end_date:
            query = query.filter(Price.date <= end_date)
        query = query.order_by(Price.date.asc())
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_price_history_for_tickers(
        self,
        tickers: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Price]:
        query = self.db.query(Price).join(Symbol).filter(Symbol.ticker.in_([t.upper() for t in tickers]))
        if start_date:
            query = query.filter(Price.date >= start_date)
        if end_date:
            query = query.filter(Price.date <= end_date)
        return query.order_by(Price.date.asc()).all()

    def get_symbol_summary(self, symbol_id: int) -> Dict[str, Any]:
        stats = self.db.query(
            func.min(Price.date).label("first_date"),
            func.max(Price.date).label("last_date"),
            func.count(Price.id).label("total_records"),
            func.min(Price.low).label("min_price"),
            func.max(Price.high).label("max_price")
        ).filter(Price.symbol_id == symbol_id).first()

        latest = self.get_latest_price(symbol_id)
        prev = self.get_previous_price(symbol_id, latest.date) if latest else None
        
        change_pct = None
        if latest and prev and prev.close > 0:
            change_pct = float((latest.close - prev.close) / prev.close * 100)

        return {
            "first_date": stats.first_date if stats else None,
            "last_date": stats.last_date if stats else None,
            "total_records": stats.total_records if stats else 0,
            "min_price_all_time": stats.min_price if stats else None,
            "max_price_all_time": stats.max_price if stats else None,
            "latest_price": latest.close if latest else None,
            "change_pct_1d": change_pct,
            "volume_1d": latest.volume if latest else None
        }

    def list_all_sectors(self) -> List[str]:
        sectors = self.db.query(Symbol.sector).distinct().filter(Symbol.sector.isnot(None)).all()
        return [s[0] for s in sectors if s[0]]
