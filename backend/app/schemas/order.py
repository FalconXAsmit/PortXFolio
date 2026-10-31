from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class OrderCreate(BaseModel):
    symbol: str
    portfolio_id: int
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT
    side: str  # BUY, SELL
    quantity: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(default=None, gt=0)  # Limit price
    stop_price: Optional[Decimal] = Field(default=None, gt=0)  # Stop price
    time_in_force: str = "GTC"  # GTC, DAY, IOC

class OrderResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol_id: int
    ticker: str
    symbol_name: str
    order_type: str
    side: str
    status: str
    quantity: Decimal
    filled_quantity: Decimal
    price: Optional[Decimal]
    stop_price: Optional[Decimal]
    time_in_force: str
    reject_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class TradeResponse(BaseModel):
    id: int
    order_id: int
    portfolio_id: int
    symbol_id: int
    ticker: str
    symbol_name: str
    side: str
    quantity: Decimal
    execution_price: Decimal
    commission: Decimal
    slippage: Decimal
    realized_pnl: Decimal
    executed_at: datetime

    class Config:
        from_attributes = True

class OrderPreviewRequest(BaseModel):
    symbol: str
    portfolio_id: int
    side: str
    quantity: Decimal
    order_type: str = "MARKET"
    price: Optional[Decimal] = None

class OrderPreviewResponse(BaseModel):
    symbol: str
    side: str
    quantity: Decimal
    estimated_price: Decimal
    estimated_gross: Decimal
    estimated_commission: Decimal
    estimated_slippage: Decimal
    estimated_total: Decimal
    can_execute: bool
    rejection_reason: Optional[str] = None
    cash_balance_before: Decimal
    cash_balance_after: Decimal
