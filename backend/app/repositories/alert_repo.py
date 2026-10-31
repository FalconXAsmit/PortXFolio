from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.models.alert import Alert, Watchlist, WatchlistItem

class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_alert_by_id(self, alert_id: int) -> Optional[Alert]:
        return self.db.query(Alert).filter(Alert.id == alert_id).first()

    def list_alerts_by_user(self, user_id: int) -> List[Alert]:
        return self.db.query(Alert).filter(Alert.user_id == user_id).order_by(Alert.created_at.desc()).all()

    def list_active_alerts(self) -> List[Alert]:
        return self.db.query(Alert).filter(Alert.is_active == True, Alert.is_triggered == False).all()

    def mark_triggered(self, alert_id: int):
        alert = self.get_alert_by_id(alert_id)
        if alert:
            alert.is_triggered = True
            alert.triggered_at = datetime.now(timezone.utc)
            self.db.commit()

    def get_watchlist_by_id(self, watchlist_id: int) -> Optional[Watchlist]:
        return self.db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()

    def list_watchlists_by_user(self, user_id: int) -> List[Watchlist]:
        return self.db.query(Watchlist).filter(Watchlist.user_id == user_id).all()

    def add_watchlist_item(self, watchlist_id: int, symbol_id: int) -> WatchlistItem:
        existing = self.db.query(WatchlistItem)\
            .filter(WatchlistItem.watchlist_id == watchlist_id, WatchlistItem.symbol_id == symbol_id)\
            .first()
        if existing:
            return existing
        item = WatchlistItem(watchlist_id=watchlist_id, symbol_id=symbol_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
