import pytest
import numpy as np
import pandas as pd
from decimal import Decimal
from backend.app.services.portfolio_service import PortfolioService
from backend.app.schemas.portfolio import OptimizationRequest, RebalanceRequest, RebalanceTarget
from backend.app.models import User, Portfolio, Symbol, Price

def test_markowitz_optimization(db_session):
    service = PortfolioService(db_session)
    
    # Run optimization on 3 tickers
    req = OptimizationRequest(
        symbols=["RELIANCE", "TCS", "INFY"],
        risk_free_rate=0.06
    )
    res = service.optimize_portfolio(req)

    assert "max_sharpe" in res.model_dump()
    assert "min_variance" in res.model_dump()
    assert "risk_parity" in res.model_dump()
    assert len(res.frontier_curve) > 0

    # Verify weights sum to approximately 1.0 (100%)
    ms_weights = res.max_sharpe["weights"]
    total_w = sum(ms_weights.values())
    assert abs(total_w - 1.0) < 0.01

    mv_weights = res.min_variance["weights"]
    total_mv = sum(mv_weights.values())
    assert abs(total_mv - 1.0) < 0.01

def test_portfolio_rebalance_plan(db_session):
    user = db_session.query(User).filter(User.email == "test_trader@portfolix.com").first()
    portfolio = db_session.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    service = PortfolioService(db_session)

    # Rebalance target: 50% RELIANCE, 50% TCS
    reb_req = RebalanceRequest(
        targets=[
            RebalanceTarget(symbol="RELIANCE", target_weight_pct=50.0),
            RebalanceTarget(symbol="TCS", target_weight_pct=50.0)
        ]
    )
    plan = service.calculate_rebalance_plan(user.id, portfolio.id, reb_req)

    assert plan.portfolio_id == portfolio.id
    assert len(plan.actions) >= 2
    assert plan.total_equity > Decimal("0")
    for act in plan.actions:
        assert act.action in ["BUY", "SELL", "HOLD"]
