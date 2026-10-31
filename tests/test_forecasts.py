import pytest
from backend.app.services.forecast_service import ForecastService
from backend.app.schemas.forecast import ForecastRequest

def test_ml_price_forecast(db_session):
    service = ForecastService(db_session)
    req = ForecastRequest(
        symbol="RELIANCE",
        model_type="GRADIENT_BOOSTING",
        forecast_days=15,
        lookback_years=3
    )
    res = service.generate_forecast(req)

    assert res.symbol == "RELIANCE"
    assert res.forecast_horizon_days == 15
    assert res.current_price > 0
    assert res.predicted_target_price > 0
    assert res.metrics.rmse >= 0
    assert res.metrics.mae >= 0
    assert res.metrics.directional_accuracy_pct >= 0
    assert len(res.series) > 15
    assert res.signal.signal_type in ["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]
    assert "DISCLAIMER" in res.disclaimer
