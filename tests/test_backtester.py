import pytest
from datetime import date
from backend.app.services.backtest_engine import BacktestEngine
from backend.app.schemas.backtest import BacktestRequest, GridOptimizationRequest
from backend.app.models import User

def test_backtest_sma_crossover(db_session):
    user = db_session.query(User).filter(User.email == "test_trader@portfolix.com").first()
    engine = BacktestEngine(db_session)

    req = BacktestRequest(
        strategy_type="SMA_CROSS",
        symbol="RELIANCE",
        start_date=date(2020, 1, 1),
        end_date=date(2023, 1, 1),
        initial_cash=1000000.0,
        parameters={"fast_period": 20, "slow_period": 50}
    )
    result = engine.run_backtest(user.id, req)

    assert result.strategy_type == "SMA_CROSS"
    assert result.symbol == "RELIANCE"
    assert result.final_equity > 0
    assert len(result.equity_curve) > 0
    assert len(result.trades) >= 0
    assert result.max_drawdown_pct <= 0

def test_backtest_rsi_strategy(db_session):
    user = db_session.query(User).filter(User.email == "test_trader@portfolix.com").first()
    engine = BacktestEngine(db_session)

    req = BacktestRequest(
        strategy_type="RSI_MEAN_REVERSION",
        symbol="TCS",
        start_date=date(2021, 1, 1),
        end_date=date(2024, 1, 1),
        initial_cash=500000.0,
        parameters={"rsi_period": 14, "oversold_threshold": 35, "overbought_threshold": 65}
    )
    result = engine.run_backtest(user.id, req)

    assert result.strategy_type == "RSI_MEAN_REVERSION"
    assert result.final_equity > 0

def test_grid_optimization(db_session):
    engine = BacktestEngine(db_session)
    req = GridOptimizationRequest(
        strategy_type="SMA_CROSS",
        symbol="INFY",
        start_date=date(2022, 1, 1),
        end_date=date(2024, 1, 1),
        initial_cash=100000.0,
        parameter_grid={
            "fast_period": [10, 20],
            "slow_period": [40, 60]
        }
    )
    res = engine.run_grid_optimization(req)
    assert res.total_combinations == 4
    assert len(res.results) == 4
    assert "fast_period" in res.best_parameters_by_sharpe
