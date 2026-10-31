from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

class PortfolioBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    initial_cash: Decimal = Field(default=Decimal("1000000.00"), gt=0)

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioDepositWithdraw(BaseModel):
    amount: Decimal = Field(..., gt=0)
    notes: Optional[str] = None

class HoldingResponse(BaseModel):
    id: int
    symbol_id: int
    ticker: str
    name: str
    sector: Optional[str] = None
    quantity: Decimal
    average_buy_price: Decimal
    current_price: Decimal
    market_value: Decimal
    total_invested: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float
    weight_pct: float

    class Config:
        from_attributes = True

class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    initial_cash: Decimal
    cash_balance: Decimal
    holdings_value: Decimal
    total_equity: Decimal
    total_pnl: Decimal
    total_pnl_pct: float
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    holdings: List[HoldingResponse] = []

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class RiskMetricsResponse(BaseModel):
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    annualized_return: float
    annualized_volatility: float
    var_95_parametric: float
    var_95_historical: float
    cvar_95_historical: float
    beta: float
    alpha: float
    r_squared: float

class PerformancePoint(BaseModel):
    date: str
    portfolio_equity: float
    benchmark_equity: float
    portfolio_return_pct: float
    benchmark_return_pct: float

class MonthlyReturnItem(BaseModel):
    year: int
    month: int
    return_pct: float

class PortfolioPerformanceResponse(BaseModel):
    portfolio_id: int
    start_date: str
    end_date: str
    equity_curve: List[PerformancePoint]
    monthly_returns: List[MonthlyReturnItem]
    risk_metrics: RiskMetricsResponse

class OptimizationRequest(BaseModel):
    symbols: List[str]
    target_return: Optional[float] = None
    risk_free_rate: float = 0.06  # 6% baseline for INR/risk-free

class OptimizedPortfolioItem(BaseModel):
    symbol: str
    weight: float

class EfficientFrontierPoint(BaseModel):
    volatility: float
    expected_return: float
    sharpe: float
    weights: Dict[str, float]

class OptimizationResponse(BaseModel):
    max_sharpe: Dict[str, Any]
    min_variance: Dict[str, Any]
    risk_parity: Dict[str, Any]
    frontier_curve: List[EfficientFrontierPoint]

class RebalanceTarget(BaseModel):
    symbol: str
    target_weight_pct: float

class RebalanceRequest(BaseModel):
    targets: List[RebalanceTarget]

class RebalanceAction(BaseModel):
    symbol: str
    action: str  # BUY / SELL / HOLD
    current_quantity: Decimal
    target_quantity: Decimal
    quantity_delta: Decimal
    current_price: Decimal
    estimated_cost: Decimal
    current_weight_pct: float
    target_weight_pct: float

class RebalanceResponse(BaseModel):
    portfolio_id: int
    total_equity: Decimal
    available_cash: Decimal
    actions: List[RebalanceAction]
    total_buy_value: Decimal
    total_sell_value: Decimal
