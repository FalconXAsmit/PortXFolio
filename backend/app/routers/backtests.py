from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
import json

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.backtest import (
    BacktestRequest, BacktestResponse, BacktestTradeRecord,
    EquityPoint, GridOptimizationRequest, GridOptimizationResponse
)
from backend.app.services.backtest_engine import BacktestEngine
from backend.app.repositories.backtest_repo import BacktestRepository

router = APIRouter(prefix="/backtests", tags=["Strategy Backtesting"])

@router.post("/run", response_model=BacktestResponse)
def run_backtest(
    req: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    engine = BacktestEngine(db)
    return engine.run_backtest(current_user.id, req)

@router.post("/optimize", response_model=GridOptimizationResponse)
def run_grid_optimization(
    req: GridOptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    engine = BacktestEngine(db)
    return engine.run_grid_optimization(req)

@router.get("", response_model=List[BacktestResponse])
def list_user_backtests(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = BacktestRepository(db)
    bts = repo.list_by_user_id(current_user.id, skip=skip, limit=limit)
    results = []
    for b in bts:
        eq_curve = [EquityPoint(**pt) for pt in json.loads(b.equity_curve_json)] if b.equity_curve_json else []
        trades = [
            BacktestTradeRecord(
                symbol=t.symbol,
                side=t.side,
                entry_date=t.entry_date,
                exit_date=t.exit_date,
                entry_price=float(t.entry_price),
                exit_price=float(t.exit_price),
                quantity=float(t.quantity),
                pnl=float(t.pnl),
                return_pct=float(t.return_pct),
                holding_period_days=t.holding_period_days
            )
            for t in b.trades
        ]
        results.append(BacktestResponse(
            id=b.id,
            name=b.name,
            strategy_type=b.strategy_type,
            symbol=b.symbol_or_universe,
            start_date=b.start_date,
            end_date=b.end_date,
            initial_cash=float(b.initial_cash),
            final_equity=float(b.final_equity),
            total_return_pct=float(b.total_return_pct),
            benchmark_return_pct=float(b.benchmark_return_pct or 0.0),
            cagr=float(b.cagr or 0.0),
            sharpe_ratio=float(b.sharpe_ratio or 0.0),
            sortino_ratio=float(b.sortino_ratio or 0.0),
            calmar_ratio=float(b.calmar_ratio or 0.0),
            max_drawdown_pct=float(b.max_drawdown_pct or 0.0),
            win_rate=float(b.win_rate or 0.0),
            profit_factor=float(b.profit_factor or 0.0),
            total_trades=b.total_trades,
            winning_trades=b.winning_trades,
            losing_trades=b.losing_trades,
            parameters=json.loads(b.parameters_json) if b.parameters_json else {},
            equity_curve=eq_curve,
            trades=trades,
            monthly_matrix=[]
        ))
    return results

@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = BacktestRepository(db)
    success = repo.delete(backtest_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")
