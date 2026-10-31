from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.market import (
    SymbolResponse, SymbolDetailResponse, IndicatorsResponse,
    MarketStatsResponse, CorrelationMatrixResponse
)
from backend.app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["Market Data & Analytics"])

@router.get("/symbols", response_model=List[SymbolResponse])
def list_symbols(
    sector: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = MarketService(db)
    return service.list_symbols(sector=sector, search=search, skip=skip, limit=limit)

@router.get("/symbols/{ticker}", response_model=SymbolDetailResponse)
def get_symbol_detail(ticker: str, db: Session = Depends(get_db)):
    service = MarketService(db)
    detail = service.get_symbol_detail(ticker.upper())
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {ticker} not found")
    return detail

@router.get("/prices/{ticker}")
def get_price_history(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = Query(None, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    service = MarketService(db)
    return service.get_price_history(ticker.upper(), start_date=start_date, end_date=end_date, limit=limit)

@router.get("/indicators/{ticker}", response_model=IndicatorsResponse)
def get_indicators(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    service = MarketService(db)
    return service.calculate_technical_indicators(ticker.upper(), start_date=start_date, end_date=end_date)

@router.get("/stats/{ticker}", response_model=MarketStatsResponse)
def get_market_stats(
    ticker: str,
    risk_free_rate: float = Query(0.06, ge=0.0, le=0.20),
    db: Session = Depends(get_db)
):
    service = MarketService(db)
    stats = service.calculate_market_stats(ticker.upper(), risk_free_rate=risk_free_rate)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No stats available for symbol {ticker}")
    return stats

@router.get("/correlations", response_model=CorrelationMatrixResponse)
def get_correlation_matrix(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols list e.g. RELIANCE,TCS,INFY"),
    db: Session = Depends(get_db)
):
    service = MarketService(db)
    sym_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    return service.get_correlation_matrix(sym_list)

@router.get("/sectors", response_model=List[str])
def list_sectors(db: Session = Depends(get_db)):
    service = MarketService(db)
    return service.market_repo.list_all_sectors()
