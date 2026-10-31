import pytest

def test_health_check_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["app_name"] == "Portfolix"

def test_market_symbols_endpoint(client):
    res = client.get("/api/v1/market/symbols")
    assert res.status_code == 200
    symbols = res.json()
    assert isinstance(symbols, list)
    assert len(symbols) > 0

def test_market_symbol_detail_endpoint(client):
    res = client.get("/api/v1/market/symbols/RELIANCE")
    assert res.status_code == 200
    data = res.json()
    assert data["ticker"] == "RELIANCE"
    assert data["exchange"] == "NSE"

def test_technical_indicators_endpoint(client):
    res = client.get("/api/v1/market/indicators/RELIANCE")
    assert res.status_code == 200
    data = res.json()
    assert "indicators" in data
    assert "rsi" in data["indicators"]
    assert "sma" in data["indicators"]

def test_correlation_matrix_endpoint(client):
    res = client.get("/api/v1/market/correlations?symbols=RELIANCE,TCS,INFY")
    assert res.status_code == 200
    data = res.json()
    assert len(data["symbols"]) == 3
    assert len(data["matrix"]) == 3

def test_portfolio_endpoints(client, auth_headers):
    # 1. List portfolios
    res = client.get("/api/v1/portfolios", headers=auth_headers)
    assert res.status_code == 200
    portfolios = res.json()
    assert len(portfolios) > 0
    p_id = portfolios[0]["id"]

    # 2. Get details
    detail_res = client.get(f"/api/v1/portfolios/{p_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == p_id

    # 3. Performance
    perf_res = client.get(f"/api/v1/portfolios/{p_id}/performance", headers=auth_headers)
    assert perf_res.status_code == 200
    assert "equity_curve" in perf_res.json()
    assert "risk_metrics" in perf_res.json()
