from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date

class ForecastRequest(BaseModel):
    symbol: str
    model_type: str = "GRADIENT_BOOSTING"  # GRADIENT_BOOSTING, RIDGE, ARIMA, EXPONENTIAL_SMOOTHING
    forecast_days: int = Field(default=30, ge=5, le=180)
    lookback_years: int = Field(default=3, ge=1, le=10)

class ForecastDataPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    predicted: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    is_forecast: bool = False

class ForecastMetrics(BaseModel):
    rmse: float
    mae: float
    mape: float
    directional_accuracy_pct: float
    r_squared: float
    test_samples_count: int

class QuantitativeSignal(BaseModel):
    signal_type: str  # STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
    confidence_score: float  # 0 to 100
    expected_30d_return_pct: float
    momentum_score: float
    trend_strength: str
    summary_reasoning: str

class ForecastResponse(BaseModel):
    symbol: str
    model_type: str
    forecast_horizon_days: int
    train_end_date: str
    forecast_end_date: str
    current_price: float
    predicted_target_price: float
    projected_return_pct: float
    metrics: ForecastMetrics
    series: List[ForecastDataPoint]
    signal: QuantitativeSignal
    disclaimer: str = "DISCLAIMER: Model outputs are quantitative statistical projections generated for educational and simulation purposes only. They do not constitute financial, investment, or trading advice."
