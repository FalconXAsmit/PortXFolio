from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.forecast import ForecastRequest, ForecastResponse
from backend.app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecasts", tags=["Quantitative Forecasting & ML Signals"])

@router.post("/generate", response_model=ForecastResponse)
def generate_forecast(
    req: ForecastRequest,
    db: Session = Depends(get_db)
):
    service = ForecastService(db)
    return service.generate_forecast(req)
