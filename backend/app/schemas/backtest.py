from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

class BacktestRequest(BaseModel):
    name: Optional[str] = None
    strategy_type: str  # SMA_CROSS, RSI_MEAN_REVERSION, MACD, MOMENTUM, BOLLINGER_BREAKOUT
    symbol: str
    start_date: date
    end_date: date
    initial_cash: float = 1000000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    parameters: Dict[str, Any] = {}

class BacktestTradeRecord(BaseModel):
    symbol: str
    side: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float
    holding_period_days: int

class EquityPoint(BaseModel):
    date: str
    equity: float
    benchmark_equity: float
    drawdown_pct: float
    cash: float
    holdings_value: float

class MonthlyReturnMatrix(BaseModel):
    year: int
    returns: Dict[int, float]  # month -> return_pct
    total_year: float

class BacktestResponse(BaseModel):
    id: Optional[int] = None
    name: str
    strategy_type: str
    symbol: str
    start_date: date
    end_date: date
    initial_cash: float
    final_equity: float
    total_return_pct: float
    benchmark_return_pct: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    parameters: Dict[str, Any]
    equity_curve: List[EquityPoint]
    trades: List[BacktestTradeRecord]
    monthly_matrix: List[MonthlyReturnMatrix]

class GridOptimizationRequest(BaseModel):
    strategy_type: str
    symbol: str
    start_date: date
    end_date: date
    initial_cash: float = 1000000.0
    parameter_grid: Dict[str, List[Any]]

class GridResultItem(BaseModel):
    parameters: Dict[str, Any]
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int

class GridOptimizationResponse(BaseModel):
    strategy_type: str
    symbol: str
    total_combinations: int
    results: List[GridResultItem]
    best_parameters_by_sharpe: Dict[str, Any]
    best_parameters_by_return: Dict[str, Any]
