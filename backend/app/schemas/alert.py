from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class AlertCreate(BaseModel):
    symbol: str
    condition_type: str  # PRICE_ABOVE, PRICE_BELOW, RSI_OVERBOUGHT, RSI_OVERSOLD, SMA_CROSS_ABOVE, SMA_CROSS_BELOW
    target_value: Decimal = Field(..., gt=0)
    notes: Optional[str] = None

class AlertResponse(BaseModel):
    id: int
    user_id: int
    symbol_id: int
    ticker: str
    symbol_name: str
    condition_type: str
    target_value: Decimal
    is_triggered: bool
    triggered_at: Optional[datetime]
    is_active: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class WatchlistItemCreate(BaseModel):
    symbol: str

class WatchlistCreate(BaseModel):
    name: str
    symbols: Optional[List[str]] = []

class WatchlistResponse(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: datetime
    symbols: List[str] = []

    class Config:
        from_attributes = True
