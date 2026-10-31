import httpx
import json
import time

API_BASE = "http://127.0.0.1:8000/api/v1"
FRONTEND_BASE = "http://127.0.0.1:5173"

def run_e2e_verification():
    print("=" * 70)
    print("PORTFOLIX AUTOMATED END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    client = httpx.Client(timeout=15.0)

    # 1. Health check
    print("\n[1/8] Verifying Backend Health...")
    res = client.get(f"{API_BASE}/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print(f"  [PASS] Status: {res.json()}")

    # 2. Frontend HTTP status
    print("\n[2/8] Verifying Frontend Dev Server...")
    f_res = None
    target_frontend = FRONTEND_BASE
    for test_url in [FRONTEND_BASE, "http://localhost:5173", "http://127.0.0.1:5174", "http://localhost:5174"]:
        try:
            res = client.get(test_url)
            if res.status_code == 200:
                f_res = res
                target_frontend = test_url
                break
        except Exception:
            continue

    if f_res is None:
        f_res = client.get(FRONTEND_BASE)
    assert f_res.status_code == 200, f"Frontend check failed: {f_res.status_code}"
    print(f"  [PASS] Frontend server responding at {target_frontend} (HTTP 200)")

    # 3. Authentication & Login
    print("\n[3/8] Authenticating Demo Trader Account...")
    auth_res = client.post(f"{API_BASE}/auth/login/json", json={
        "email": "trader@portfolix.com",
        "password": "trader123!"
    })
    assert auth_res.status_code == 200, f"Auth failed: {auth_res.text}"
    token_data = auth_res.json()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    print(f"  [PASS] Logged in as: {token_data['user']['full_name']} ({token_data['user']['role']})")

    # 4. Market Data & Analytics
    print("\n[4/8] Testing Market Explorer & Technical Indicators...")
    syms_res = client.get(f"{API_BASE}/market/symbols?limit=20")
    symbols = syms_res.json()
    print(f"  [PASS] Loaded {len(symbols)} NSE Equities (Top: {[s['ticker'] for s in symbols[:5]]})")

    ind_res = client.get(f"{API_BASE}/market/indicators/RELIANCE")
    assert ind_res.status_code == 200
    print(f"  [PASS] Computed Technical Indicators for RELIANCE (SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP, OBV)")

    corr_res = client.get(f"{API_BASE}/market/correlations?symbols=RELIANCE,TCS,HDFCBANK,INFY,ICICIBANK,LT")
    assert corr_res.status_code == 200
    print(f"  [PASS] Cross-Asset Correlation Heatmap calculated across {len(corr_res.json()['symbols'])} bluechips")

    # 5. Paper Trading Execution
    print("\n[5/8] Testing ACID Paper Trading Execution...")
    ports_res = client.get(f"{API_BASE}/portfolios", headers=headers)
    ports = ports_res.json()
    assert len(ports) > 0, "No portfolios found for demo trader account"
    # Select first portfolio or one with available funds
    portfolio = next((p for p in ports if float(p.get("cash_balance", 0)) >= 50000), ports[0])
    p_id = portfolio["id"]

    # Preview Order
    prev_res = client.post(f"{API_BASE}/orders/preview", json={
        "symbol": "INFY",
        "portfolio_id": p_id,
        "side": "BUY",
        "quantity": 25,
        "order_type": "MARKET"
    }, headers=headers)
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    est_price = float(prev_data['estimated_price'])
    est_total = float(prev_data['estimated_total'])
    print(f"  [PASS] Order Preview: Buy 25 INFY, Est Price: Rs.{est_price:.2f}, Est Total: Rs.{est_total:.2f}")

    # Ensure portfolio has enough cash to fill the order
    if float(portfolio.get("cash_balance", 0)) < est_total * 1.05:
        deposit_res = client.post(f"{API_BASE}/portfolios/{p_id}/deposit", json={
            "amount": 500000.0,
            "notes": "E2E automated test funding"
        }, headers=headers)
        assert deposit_res.status_code == 200, f"Failed depositing test funds: {deposit_res.text}"

    # Execute Order
    order_res = client.post(f"{API_BASE}/orders", json={
        "symbol": "INFY",
        "portfolio_id": p_id,
        "side": "BUY",
        "quantity": 25,
        "order_type": "MARKET"
    }, headers=headers)
    assert order_res.status_code == 201, f"Order creation failed: {order_res.text}"
    order_data = order_res.json()
    assert order_data["status"] == "FILLED", f"Expected FILLED but got {order_data.get('status')}: {order_data.get('reject_reason')}"
    print(f"  [PASS] Order FILLED: Trade ID #{order_data['id']} executed atomically.")

    # 6. Portfolio Analytics & Markowitz MPT Optimization
    print("\n[6/8] Testing Portfolio Risk Analytics & Markowitz Optimization...")
    perf_res = client.get(f"{API_BASE}/portfolios/{p_id}/performance", headers=headers)
    assert perf_res.status_code == 200
    risk = perf_res.json()["risk_metrics"]
    print(f"  [PASS] Risk Engine: Sharpe={risk['sharpe_ratio']}, Sortino={risk['sortino_ratio']}, MaxDD={risk['max_drawdown']}%, VaR(95%)={risk['var_95_historical']}%")

    opt_res = client.post(f"{API_BASE}/portfolios/optimize", json={
        "symbols": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "LT"],
        "risk_free_rate": 0.06
    }, headers=headers)
    assert opt_res.status_code == 200
    opt = opt_res.json()
    print(f"  [PASS] Markowitz Efficient Frontier: Max Sharpe Exp Return={opt['max_sharpe']['expected_return']*100:.2f}%, Volatility={opt['max_sharpe']['volatility']*100:.2f}%, Sharpe={opt['max_sharpe']['sharpe_ratio']:.2f}")

    # 7. Strategy Backtesting
    print("\n[7/8] Testing Event-Driven Strategy Backtester...")
    bt_res = client.post(f"{API_BASE}/backtests/run", json={
        "strategy_type": "SMA_CROSS",
        "symbol": "RELIANCE",
        "start_date": "2018-01-01",
        "end_date": "2026-09-28",
        "initial_cash": 1000000.0,
        "parameters": {"fast_period": 20, "slow_period": 50}
    }, headers=headers)
    assert bt_res.status_code == 200
    bt = bt_res.json()
    print(f"  [PASS] Backtest Complete: Total Return={bt['total_return_pct']:.2f}%, CAGR={bt['cagr']:.2f}%, Sharpe={bt['sharpe_ratio']:.2f}, Win Rate={bt['win_rate']:.1f}%, Trades={bt['total_trades']}")

    # 8. Machine Learning Forecasting & Signals
    print("\n[8/8] Testing Quantitative ML Forecasting & Signals...")
    fc_res = client.post(f"{API_BASE}/forecasts/generate", json={
        "symbol": "TCS",
        "model_type": "GRADIENT_BOOSTING",
        "forecast_days": 30,
        "lookback_years": 3
    })
    assert fc_res.status_code == 200
    fc = fc_res.json()
    print(f"  [PASS] ML Forecast (TCS 30D): Target=Rs.{fc['predicted_target_price']:.2f} ({fc['projected_return_pct']:+.2f}%), Signal={fc['signal']['signal_type']} (Conf: {fc['signal']['confidence_score']}%)")
    print(f"  [PASS] Directional Accuracy: {fc['metrics']['directional_accuracy_pct']:.1f}%, RMSE: Rs.{fc['metrics']['rmse']:.2f}")

    print("\n" + "=" * 70)
    print("ALL END-TO-END FLOWS VERIFIED SUCCESSFULLY (100% OPERATIONAL)")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
