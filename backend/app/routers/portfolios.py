from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.portfolio import (
    PortfolioCreate, PortfolioResponse, PortfolioDepositWithdraw,
    PortfolioPerformanceResponse, OptimizationRequest, OptimizationResponse,
    RebalanceRequest, RebalanceResponse, TransactionResponse
)
from backend.app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["Portfolios & Risk Analytics"])

@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    portfolio_in: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.create_portfolio(current_user.id, portfolio_in)

@router.get("", response_model=List[PortfolioResponse])
def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.list_user_portfolios(current_user.id)

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.get_portfolio_details(current_user.id, portfolio_id)

@router.post("/{portfolio_id}/deposit", response_model=PortfolioResponse)
def deposit_cash(
    portfolio_id: int,
    req: PortfolioDepositWithdraw,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.deposit_or_withdraw(current_user.id, portfolio_id, req.amount, is_deposit=True, notes=req.notes)

@router.post("/{portfolio_id}/withdraw", response_model=PortfolioResponse)
def withdraw_cash(
    portfolio_id: int,
    req: PortfolioDepositWithdraw,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.deposit_or_withdraw(current_user.id, portfolio_id, req.amount, is_deposit=False, notes=req.notes)

@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformanceResponse)
def get_portfolio_performance(
    portfolio_id: int,
    risk_free_rate: float = Query(0.06, ge=0.0, le=0.20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.get_portfolio_performance(current_user.id, portfolio_id, risk_free_rate=risk_free_rate)

@router.get("/{portfolio_id}/transactions", response_model=List[TransactionResponse])
def get_portfolio_transactions(
    portfolio_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    # verify ownership
    service.get_portfolio_details(current_user.id, portfolio_id)
    txs = service.portfolio_repo.list_transactions(portfolio_id, limit=limit)
    return [TransactionResponse.model_validate(t) for t in txs]

@router.post("/optimize", response_model=OptimizationResponse)
def optimize_portfolio(
    req: OptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.optimize_portfolio(req)

@router.post("/{portfolio_id}/rebalance", response_model=RebalanceResponse)
def calculate_rebalance(
    portfolio_id: int,
    req: RebalanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PortfolioService(db)
    return service.calculate_rebalance_plan(current_user.id, portfolio_id, req)
