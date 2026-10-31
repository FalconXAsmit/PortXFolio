from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

class PriceRecord(BaseModel):
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    class Config:
        from_attributes = True

class PriceValidationSchema(BaseModel):
    """Used by ETL pipeline for strict data validation"""
    Date: date
    Symbol: str
    Open: float = Field(gt=0)
    High: float = Field(gt=0)
    Low: float = Field(gt=0)
    Close: float = Field(gt=0)
    Volume: int = Field(ge=0)

class SymbolBase(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: str = "NSE"
    currency: str = "INR"

class SymbolResponse(SymbolBase):
    id: int
    is_active: bool
    latest_price: Optional[Decimal] = None
    change_pct_1d: Optional[float] = None
    volume_1d: Optional[int] = None

    class Config:
        from_attributes = True

class SymbolDetailResponse(SymbolResponse):
    first_date: Optional[date] = None
    last_date: Optional[date] = None
    total_records: Optional[int] = None
    min_price_all_time: Optional[Decimal] = None
    max_price_all_time: Optional[Decimal] = None

class IndicatorValue(BaseModel):
    date: str
    value: Optional[float] = None
    # For multi-value indicators like Bollinger Bands or MACD
    upper: Optional[float] = None
    middle: Optional[float] = None
    lower: Optional[float] = None
    macd: Optional[float] = None
    signal: Optional[float] = None
    hist: Optional[float] = None

class IndicatorsResponse(BaseModel):
    symbol: str
    timeframe: str
    indicators: Dict[str, List[Dict[str, Any]]]

class MarketStatsResponse(BaseModel):
    symbol: str
    mean_daily_return: float
    annualized_return: float
    annualized_volatility: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    beta_vs_benchmark: float
    skewness: float
    kurtosis: float
    current_rsi_14: Optional[float] = None
    current_sma_50: Optional[float] = None
    current_sma_200: Optional[float] = None

class CorrelationMatrixResponse(BaseModel):
    symbols: List[str]
    matrix: List[List[float]]
    start_date: str
    end_date: str
