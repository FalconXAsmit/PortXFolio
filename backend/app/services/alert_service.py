from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.alert import Alert, Watchlist, WatchlistItem, AlertConditionType
from backend.app.models.market import Symbol, Price
from backend.app.schemas.alert import AlertCreate, AlertResponse, WatchlistCreate, WatchlistResponse
from backend.app.repositories.alert_repo import AlertRepository
from backend.app.repositories.market_repo import MarketRepository

class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.alert_repo = AlertRepository(db)
        self.market_repo = MarketRepository(db)

    def create_alert(self, user_id: int, alert_in: AlertCreate) -> AlertResponse:
        symbol = self.market_repo.get_symbol_by_ticker(alert_in.symbol)
        if not symbol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {alert_in.symbol} not found")

        alert = Alert(
            user_id=user_id,
            symbol_id=symbol.id,
            condition_type=alert_in.condition_type,
            target_value=alert_in.target_value,
            notes=alert_in.notes,
            is_active=True,
            is_triggered=False
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        return AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            symbol_id=alert.symbol_id,
            ticker=symbol.ticker,
            symbol_name=symbol.name,
            condition_type=alert.condition_type,
            target_value=alert.target_value,
            is_triggered=alert.is_triggered,
            triggered_at=alert.triggered_at,
            is_active=alert.is_active,
            notes=alert.notes,
            created_at=alert.created_at
        )

    def list_user_alerts(self, user_id: int) -> List[AlertResponse]:
        alerts = self.alert_repo.list_alerts_by_user(user_id)
        return [
            AlertResponse(
                id=a.id,
                user_id=a.user_id,
                symbol_id=a.symbol_id,
                ticker=a.symbol.ticker,
                symbol_name=a.symbol.name,
                condition_type=a.condition_type,
                target_value=a.target_value,
                is_triggered=a.is_triggered,
                triggered_at=a.triggered_at,
                is_active=a.is_active,
                notes=a.notes,
                created_at=a.created_at
            )
            for a in alerts
        ]

    def delete_alert(self, user_id: int, alert_id: int) -> bool:
        alert = self.db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user_id).first()
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        self.db.delete(alert)
        self.db.commit()
        return True

    def check_all_active_alerts(self) -> int:
        active_alerts = self.alert_repo.list_active_alerts()
        triggered_count = 0

        for alert in active_alerts:
            latest = self.market_repo.get_latest_price(alert.symbol_id)
            if not latest:
                continue

            current_price = latest.close
            cond = alert.condition_type.upper()
            target = alert.target_value

            should_trigger = False
            if cond == "PRICE_ABOVE" and current_price >= target:
                should_trigger = True
            elif cond == "PRICE_BELOW" and current_price <= target:
                should_trigger = True

            if should_trigger:
                alert.is_triggered = True
                alert.triggered_at = datetime.now(timezone.utc)
                triggered_count += 1

        self.db.commit()
        return triggered_count

    def create_watchlist(self, user_id: int, wl_in: WatchlistCreate) -> WatchlistResponse:
        wl = Watchlist(user_id=user_id, name=wl_in.name)
        self.db.add(wl)
        self.db.flush()

        symbols_added = []
        if wl_in.symbols:
            for s_ticker in wl_in.symbols:
                sym = self.market_repo.get_symbol_by_ticker(s_ticker)
                if sym:
                    self.alert_repo.add_watchlist_item(wl.id, sym.id)
                    symbols_added.append(sym.ticker)

        self.db.commit()
        self.db.refresh(wl)
        return WatchlistResponse(
            id=wl.id,
            user_id=wl.user_id,
            name=wl.name,
            created_at=wl.created_at,
            symbols=symbols_added
        )

    def list_user_watchlists(self, user_id: int) -> List[WatchlistResponse]:
        wls = self.alert_repo.list_watchlists_by_user(user_id)
        results = []
        for w in wls:
            syms = [item.symbol.ticker for item in w.items if item.symbol]
            results.append(WatchlistResponse(
                id=w.id,
                user_id=w.user_id,
                name=w.name,
                created_at=w.created_at,
                symbols=syms
            ))
        return results
