from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.alert import AlertCreate, AlertResponse, WatchlistCreate, WatchlistResponse
from backend.app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts & Watchlists"])

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    return service.create_alert(current_user.id, alert_in)

@router.get("", response_model=List[AlertResponse])
def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    return service.list_user_alerts(current_user.id)

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    service.delete_alert(current_user.id, alert_id)

@router.post("/check", response_model=dict)
def trigger_alert_check(db: Session = Depends(get_db)):
    service = AlertService(db)
    triggered = service.check_all_active_alerts()
    return {"status": "success", "triggered_alerts_count": triggered}

@router.post("/watchlists", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    wl_in: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    return service.create_watchlist(current_user.id, wl_in)

@router.get("/watchlists", response_model=List[WatchlistResponse])
def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    return service.list_user_watchlists(current_user.id)
