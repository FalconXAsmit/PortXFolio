from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])

@router.get("/portfolio/{portfolio_id}/csv")
def export_portfolio_csv(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    return service.export_portfolio_csv(current_user.id, portfolio_id)

@router.get("/trades/csv")
def export_trades_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    return service.export_trades_csv(current_user.id)
