"""
PortXFolio — Streamlit Quantitative Trading & Risk Workstation
"""

import os
from datetime import datetime, date, timedelta
from decimal import Decimal
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import httpx

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PortXFolio — Quant Trading Station",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Production Custom Styling
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', -apple-system, monospace;
    font-weight: 700;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    height: 38px;
    padding-top: 6px;
    padding-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# Auto-bootstrap FastAPI backend when running locally or on Streamlit Community Cloud
def _ensure_backend_service():
    import socket
    import threading
    import time
    from urllib.parse import urlparse
    from pathlib import Path

    parsed = urlparse(API_BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000

    if host in ["127.0.0.1", "localhost", "0.0.0.0"]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex((host, port)) == 0:
                return

        # Ensure database exists if missing
        db_file = Path(__file__).resolve().parent / "portfolix.db"
        if not db_file.exists():
            try:
                from scripts.ingest_csv import run_ingestion
                run_ingestion()
            except Exception as e:
                print(f"[AutoStart] DB initialization note: {e}")

        def _run_server():
            import uvicorn
            from backend.app.main import app as fastapi_app
            uvicorn.run(fastapi_app, host=host, port=port, log_level="warning")

        srv_thread = threading.Thread(target=_run_server, daemon=True)
        srv_thread.start()

        for _ in range(12):
            time.sleep(0.5)
            try:
                with httpx.Client(timeout=1.0) as client:
                    if client.get(f"{API_BASE_URL}/health").status_code == 200:
                        break
            except Exception:
                pass

_ensure_backend_service()

# Initialize Session State
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "selected_portfolio_id" not in st.session_state:
    st.session_state["selected_portfolio_id"] = None

# -----------------------------------------------------------------------------
# API Client Helper Functions
# -----------------------------------------------------------------------------
def get_headers():
    headers = {"Content-Type": "application/json"}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state['token']}"
    return headers

def api_get(endpoint: str, params=None):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=get_headers(), params=params)
            if resp.status_code == 200:
                return resp.json(), None
            elif resp.status_code == 401:
                st.session_state["token"] = None
                st.session_state["user"] = None
                return None, "Session expired. Please log in again."
            else:
                detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type") == "application/json" else resp.text
                return None, f"Error {resp.status_code}: {detail}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def api_post(endpoint: str, data=None):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=get_headers(), json=data)
            if resp.status_code in [200, 201]:
                return resp.json(), None
            elif resp.status_code == 401:
                st.session_state["token"] = None
                st.session_state["user"] = None
                return None, "Session expired. Please log in again."
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                return None, f"Error {resp.status_code}: {detail}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def api_delete(endpoint: str):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.delete(url, headers=get_headers())
            if resp.status_code in [200, 204]:
                return True, None
            else:
                detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type") == "application/json" else resp.text
                return False, f"Error {resp.status_code}: {detail}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

# -----------------------------------------------------------------------------
# Sidebar: Brand, Authentication & Portfolio Selector
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🌐 PortXFolio")
    st.caption("Quantitative Trading & Risk Management Station")
    
    st.divider()

    # Authentication Block
    if not st.session_state.get("token"):
        st.subheader("Account Sign In")
        auth_tab_in, auth_tab_up = st.tabs(["Sign In", "Register"])

        with auth_tab_in:
            email_in = st.text_input("Email", key="auth_email")
            pass_in = st.text_input("Password", type="password", key="auth_pass")
            if st.button("Sign In", type="primary", use_container_width=True):
                if not email_in or not pass_in:
                    st.error("Please enter email and password.")
                else:
                    res, err = api_post("/auth/login/json", {"email": email_in, "password": pass_in})
                    if res and "access_token" in res:
                        st.session_state["token"] = res["access_token"]
                        user_data, _ = api_get("/auth/me")
                        st.session_state["user"] = user_data
                        st.rerun()
                    else:
                        st.error(err or "Invalid credentials")

            st.markdown("---")
            if st.button("⚡ Explore Demo Trader Account", use_container_width=True):
                res, err = api_post("/auth/login/json", {"email": "trader@portfolix.com", "password": "trader123!"})
                if res and "access_token" in res:
                    st.session_state["token"] = res["access_token"]
                    user_data, _ = api_get("/auth/me")
                    st.session_state["user"] = user_data
                    st.rerun()
                else:
                    st.error(err or "Demo login unavailable")

        with auth_tab_up:
            name_in = st.text_input("Full Name", key="auth_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not reg_email or not reg_pass or not name_in:
                    st.error("Please fill in all fields.")
                else:
                    res, err = api_post("/auth/register", {"email": reg_email, "password": reg_pass, "full_name": name_in})
                    if res:
                        st.success("Account created successfully! Signing in...")
                        log_res, _ = api_post("/auth/login/json", {"email": reg_email, "password": reg_pass})
                        if log_res and "access_token" in log_res:
                            st.session_state["token"] = log_res["access_token"]
                            st.session_state["user"] = res
                            st.rerun()
                    else:
                        st.error(err or "Registration failed")
    else:
        user = st.session_state["user"] or {}
        st.markdown(f"**{user.get('full_name', 'Trader')}**")
        st.caption(f"{user.get('email', '')}")
        if st.button("Sign Out", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["user"] = None
            st.session_state["selected_portfolio_id"] = None
            st.rerun()

    st.divider()

    # Portfolio Selection
    user_portfolios = []
    if st.session_state.get("token"):
        p_list, _ = api_get("/portfolios")
        if p_list:
            user_portfolios = p_list
            p_options = {p["id"]: f"{p['name']} (₹{float(p['total_equity']):,.0f})" for p in user_portfolios}
            current_id = st.session_state.get("selected_portfolio_id")
            if current_id not in p_options:
                current_id = user_portfolios[0]["id"]
                st.session_state["selected_portfolio_id"] = current_id

            selected_id = st.selectbox(
                "Active Portfolio Book",
                options=list(p_options.keys()),
                format_func=lambda x: p_options[x],
                index=list(p_options.keys()).index(current_id)
            )
            st.session_state["selected_portfolio_id"] = selected_id
        else:
            st.info("No portfolios found. Create one in the Portfolios tab.")

    st.divider()

    # Navigation Menu
    menu_options = [
        "📊 Dashboard",
        "📈 Market Explorer",
        "⚡ Trading Terminal",
        "💼 Portfolios & MPT",
        "🧪 Backtest Studio",
        "🤖 ML Forecast Studio",
        "🔔 Alerts & Watchlists",
        "📑 Reports & Blotter"
    ]
    selected_page = st.radio("Navigation", menu_options, index=0)

# Fetch symbols list for dropdowns
symbols_data, _ = api_get("/market/symbols?limit=100")
available_symbols = [s["ticker"] for s in symbols_data] if symbols_data else [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "AXISBANK", "LT", "HINDUNILVR", "KOTAKBANK", "BAJFINANCE", "MARUTI",
    "ASIANPAINT", "HCLTECH", "SUNPHARMA", "WIPRO", "NESTLEIND", "TITAN"
]

# -----------------------------------------------------------------------------
# PAGE 1: 📊 DASHBOARD
# -----------------------------------------------------------------------------
if selected_page == "📊 Dashboard":
    st.header("📊 Executive Portfolio & Market Dashboard")
    
    # Active Portfolio Overview
    active_pid = st.session_state.get("selected_portfolio_id")
    if active_pid and st.session_state.get("token"):
        p_detail, _ = api_get(f"/portfolios/{active_pid}")
        if p_detail:
            equity = float(p_detail.get("total_equity", 0))
            cash = float(p_detail.get("cash_balance", 0))
            holdings_val = float(p_detail.get("holdings_value", 0))
            unrealized = float(p_detail.get("unrealized_pnl", 0))
            unrealized_pct = float(p_detail.get("total_pnl_pct", 0))

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Equity", f"₹{equity:,.2f}")
            m2.metric("Available Cash", f"₹{cash:,.2f}")
            m3.metric("Invested Holdings", f"₹{holdings_val:,.2f}")
            m4.metric("Total Return", f"₹{unrealized:,.2f}", f"{unrealized_pct:+.2f}%")

            st.divider()

            # Holdings breakdown & Equity Curve
            col_chart, col_holdings = st.columns([3, 2])
            
            with col_chart:
                st.subheader("Historical Performance vs. Benchmark")
                perf, _ = api_get(f"/portfolios/{active_pid}/performance")
                if perf and perf.get("equity_curve"):
                    df_perf = pd.DataFrame(perf["equity_curve"])
                    if not df_perf.empty and "date" in df_perf:
                        df_perf["date"] = pd.to_datetime(df_perf["date"])
                        
                        eq_col = "portfolio_equity" if "portfolio_equity" in df_perf else ("equity" if "equity" in df_perf else None)
                        if eq_col:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=df_perf["date"], y=df_perf[eq_col],
                                mode="lines", name="Portfolio Equity (₹)",
                                line=dict(color="#0284C7", width=2.5)
                            ))
                            if "benchmark_equity" in df_perf:
                                fig.add_trace(go.Scatter(
                                    x=df_perf["date"], y=df_perf["benchmark_equity"],
                                    mode="lines", name="Benchmark (₹)",
                                    line=dict(color="#94A3B8", width=1.5, dash="dot")
                                ))
                            fig.update_layout(
                                margin=dict(l=0, r=0, t=20, b=0),
                                height=320,
                                xaxis_title="Date",
                                yaxis_title="Equity (INR)",
                                hovermode="x unified"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Performance curve is updating.")
                    else:
                        st.info("Performance curve will populate as historical trades are registered.")
                else:
                    st.info("Performance curve will populate as historical trades are registered.")

            with col_holdings:
                st.subheader("Portfolio Allocation")
                holdings = p_detail.get("holdings", [])
                if holdings:
                    labels = [h["ticker"] for h in holdings]
                    values = [float(h["market_value"]) for h in holdings]
                    if cash > 0:
                        labels.append("CASH")
                        values.append(cash)
                    fig_pie = px.pie(names=labels, values=values, hole=0.45)
                    fig_pie.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=320)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No active equity positions in this portfolio book.")
    else:
        st.warning("Please sign in or select a portfolio from the sidebar to inspect real-time book values.")

    st.divider()

    # Market Movers (Gainers and Losers)
    st.subheader("Market Movers (20 Bluechips)")
    if symbols_data:
        df_sym = pd.DataFrame(symbols_data)
        df_sym["change_pct_1d"] = pd.to_numeric(df_sym["change_pct_1d"], errors="coerce").fillna(0.0)
        df_sym["latest_price"] = pd.to_numeric(df_sym["latest_price"], errors="coerce").fillna(0.0)
        
        top_gainers = df_sym.sort_values(by="change_pct_1d", ascending=False).head(5)
        top_losers = df_sym.sort_values(by="change_pct_1d", ascending=True).head(5)

        col_g, col_l = st.columns(2)
        with col_g:
            st.markdown("🟢 **Top Gainers (1D)**")
            st.dataframe(
                top_gainers[["ticker", "name", "latest_price", "change_pct_1d"]].rename(
                    columns={"ticker": "Ticker", "name": "Company", "latest_price": "Price (₹)", "change_pct_1d": "Change %"}
                ),
                use_container_width=True,
                hide_index=True
            )
        with col_l:
            st.markdown("🔴 **Top Losers (1D)**")
            st.dataframe(
                top_losers[["ticker", "name", "latest_price", "change_pct_1d"]].rename(
                    columns={"ticker": "Ticker", "name": "Company", "latest_price": "Price (₹)", "change_pct_1d": "Change %"}
                ),
                use_container_width=True,
                hide_index=True
            )

# -----------------------------------------------------------------------------
# PAGE 2: 📈 MARKET EXPLORER
# -----------------------------------------------------------------------------
elif selected_page == "📈 Market Explorer":
    st.header("📈 Technical Market Explorer & Quantitative Analytics")
    
    col_sel, col_range, col_ind = st.columns([2, 2, 3])
    with col_sel:
        selected_ticker = st.selectbox("Select Asset Symbol", available_symbols, index=0)
    with col_range:
        lookback_bars = st.selectbox("Historical Bars", [100, 250, 500, 1000], index=1)
    with col_ind:
        indicators_toggle = st.multiselect("Overlay Indicators", ["SMA 20", "SMA 50", "Bollinger Bands", "VWAP"], default=["SMA 20", "Bollinger Bands"])

    # Fetch price history and indicators
    prices_raw, p_err = api_get(f"/market/prices/{selected_ticker}?limit={lookback_bars}")
    indicators_raw, _ = api_get(f"/market/indicators/{selected_ticker}")
    stats_raw, _ = api_get(f"/market/stats/{selected_ticker}")

    if prices_raw and len(prices_raw) > 0:
        df_prices = pd.DataFrame(prices_raw)
        df_prices["date"] = pd.to_datetime(df_prices["date"])
        df_prices.sort_values("date", inplace=True)
        
        # Interactive Candlestick Chart with Plotly
        fig_candle = go.Figure()
        fig_candle.add_trace(go.Candlestick(
            x=df_prices["date"],
            open=df_prices["open"],
            high=df_prices["high"],
            low=df_prices["low"],
            close=df_prices["close"],
            name="OHLC",
            increasing_line_color="#10B981",
            decreasing_line_color="#F43F5E"
        ))

        # Add SMA, Bollinger Bands, and VWAP if available
        if indicators_raw and "indicators" in indicators_raw:
            inds = indicators_raw["indicators"]
            
            # 1. SMA Overlays
            if "sma" in inds and isinstance(inds["sma"], list):
                df_sma = pd.DataFrame(inds["sma"])
                if not df_sma.empty and "date" in df_sma:
                    df_sma["date"] = pd.to_datetime(df_sma["date"])
                    if "SMA 20" in indicators_toggle and "sma20" in df_sma:
                        fig_candle.add_trace(go.Scatter(x=df_sma["date"], y=df_sma["sma20"], mode="lines", name="SMA 20", line=dict(color="#0284C7", width=1.5)))
                    if "SMA 50" in indicators_toggle and "sma50" in df_sma:
                        fig_candle.add_trace(go.Scatter(x=df_sma["date"], y=df_sma["sma50"], mode="lines", name="SMA 50", line=dict(color="#D97706", width=1.5)))

            # 2. Bollinger Bands
            if "bollinger" in inds and isinstance(inds["bollinger"], list):
                df_bb = pd.DataFrame(inds["bollinger"])
                if not df_bb.empty and "date" in df_bb and "Bollinger Bands" in indicators_toggle:
                    df_bb["date"] = pd.to_datetime(df_bb["date"])
                    if "upper" in df_bb:
                        fig_candle.add_trace(go.Scatter(x=df_bb["date"], y=df_bb["upper"], mode="lines", name="BB Upper", line=dict(color="#8B5CF6", width=1, dash="dot")))
                    if "lower" in df_bb:
                        fig_candle.add_trace(go.Scatter(x=df_bb["date"], y=df_bb["lower"], mode="lines", name="BB Lower", line=dict(color="#8B5CF6", width=1, dash="dot")))

            # 3. VWAP
            if "vwap" in inds and isinstance(inds["vwap"], list):
                df_vwap = pd.DataFrame(inds["vwap"])
                if not df_vwap.empty and "date" in df_vwap and "VWAP" in indicators_toggle:
                    df_vwap["date"] = pd.to_datetime(df_vwap["date"])
                    if "value" in df_vwap:
                        fig_candle.add_trace(go.Scatter(x=df_vwap["date"], y=df_vwap["value"], mode="lines", name="VWAP", line=dict(color="#EC4899", width=1.5)))

        fig_candle.update_layout(
            title=f"{selected_ticker} Daily Candlestick & Volume Chart",
            xaxis_rangeslider_visible=False,
            height=480,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig_candle, use_container_width=True)

        # Risk & Volatility Metrics
        if stats_raw:
            st.subheader(f"Statistical Risk Profile — {selected_ticker}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Annualized Return", f"{float(stats_raw.get('annualized_return', 0))*100:.2f}%")
            c2.metric("Annualized Volatility", f"{float(stats_raw.get('annualized_volatility', 0))*100:.2f}%")
            c3.metric("Sharpe Ratio", f"{float(stats_raw.get('sharpe_ratio', 0)):.2f}")
            c4.metric("Sortino Ratio", f"{float(stats_raw.get('sortino_ratio', 0)):.2f}")
            c5.metric("Max Drawdown", f"{float(stats_raw.get('max_drawdown', 0))*100:.2f}%")
    else:
        st.warning(f"Could not load price history for {selected_ticker}: {p_err}")

    st.divider()

    # Cross-Asset Correlation Heatmap
    st.subheader("Cross-Asset Correlation Heatmap")
    default_corr_syms = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "BHARTIARTL", "ITC"]
    corr_selection = st.multiselect("Select Assets for Correlation Matrix", available_symbols, default=default_corr_syms)
    
    if len(corr_selection) >= 2:
        corr_data, _ = api_get(f"/market/correlations?symbols={','.join(corr_selection)}")
        if corr_data and "matrix" in corr_data:
            matrix = corr_data["matrix"]
            syms = corr_data["symbols"]
            fig_corr = px.imshow(
                matrix,
                x=syms,
                y=syms,
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                text_auto=".2f"
            )
            fig_corr.update_layout(height=420, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_corr, use_container_width=True)

# -----------------------------------------------------------------------------
# PAGE 3: ⚡ TRADING TERMINAL
# -----------------------------------------------------------------------------
elif selected_page == "⚡ Trading Terminal":
    st.header("⚡ Paper Trading Execution Desk")
    active_pid = st.session_state.get("selected_portfolio_id")
    
    if not st.session_state.get("token") or not active_pid:
        st.warning("Please sign in and select a portfolio in the sidebar to execute orders.")
    else:
        order_col, holdings_col = st.columns([1, 2])

        with order_col:
            st.subheader("Submit Simulated Order")
            with st.form("order_entry_form"):
                order_sym = st.selectbox("Symbol", available_symbols)
                order_side = st.radio("Side", ["BUY", "SELL"], horizontal=True)
                order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP_LOSS"])
                order_qty = st.number_input("Shares Quantity", min_value=1, value=10, step=1)
                
                limit_p = None
                stop_p = None
                if order_type == "LIMIT":
                    limit_p = st.number_input("Limit Price (₹)", min_value=1.0, value=1000.0, step=5.0)
                elif order_type == "STOP_LOSS":
                    stop_p = st.number_input("Stop Loss Price (₹)", min_value=1.0, value=900.0, step=5.0)

                # Pre-trade Live Preview
                preview_btn = st.form_submit_button("Preview Order Impact")
                submit_btn = st.form_submit_button("🚨 Execute Order", type="primary")

            if preview_btn or submit_btn:
                preview_req = {
                    "symbol": order_sym,
                    "portfolio_id": active_pid,
                    "side": order_side,
                    "quantity": float(order_qty),
                    "order_type": order_type,
                    "price": float(limit_p) if limit_p else None
                }
                prev_data, prev_err = api_post("/orders/preview", preview_req)
                if prev_data:
                    st.info(
                        f"**Estimated Price:** ₹{prev_data['estimated_price']:,.2f}\n\n"
                        f"**Gross Value:** ₹{prev_data['estimated_gross']:,.2f} | **Commission:** ₹{prev_data['estimated_commission']:,.2f}\n\n"
                        f"**Est. Slippage:** ₹{prev_data['estimated_slippage']:,.2f} | **Total:** ₹{prev_data['estimated_total']:,.2f}\n\n"
                        f"**Cash After:** ₹{prev_data['cash_balance_after']:,.2f}"
                    )
                    if not prev_data["can_execute"]:
                        st.error(f"Execution Blocked: {prev_data.get('rejection_reason')}")
                else:
                    st.error(prev_err)

            if submit_btn:
                order_payload = {
                    "symbol": order_sym,
                    "portfolio_id": active_pid,
                    "side": order_side,
                    "quantity": float(order_qty),
                    "order_type": order_type,
                    "price": float(limit_p) if limit_p else None,
                    "stop_price": float(stop_p) if stop_p else None,
                    "time_in_force": "GTC"
                }
                res, err = api_post("/orders", order_payload)
                if res:
                    st.success(f"Order #{res['id']} {res['status']}: {res['side']} {res['quantity']} {res['ticker']}")
                    st.rerun()
                else:
                    st.error(f"Order failed: {err}")

        with holdings_col:
            st.subheader("Active Positions in Portfolio")
            p_data, _ = api_get(f"/portfolios/{active_pid}")
            if p_data and p_data.get("holdings"):
                df_h = pd.DataFrame(p_data["holdings"])
                st.dataframe(
                    df_h[["ticker", "name", "quantity", "average_buy_price", "current_price", "market_value", "unrealized_pnl", "unrealized_pnl_pct"]].rename(
                        columns={
                            "ticker": "Symbol", "name": "Name", "quantity": "Qty",
                            "average_buy_price": "Avg Buy (₹)", "current_price": "Price (₹)",
                            "market_value": "Market Val (₹)", "unrealized_pnl": "P&L (₹)",
                            "unrealized_pnl_pct": "P&L %"
                        }
                    ),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No active equity holdings.")

            st.divider()

            # Trade Blotter & Execution History
            st.subheader("Recent Execution Blotter")
            trades_data, _ = api_get(f"/orders/trades?portfolio_id={active_pid}&limit=25")
            if trades_data:
                df_t = pd.DataFrame(trades_data)
                st.dataframe(
                    df_t[["ticker", "side", "quantity", "execution_price", "commission", "slippage", "realized_pnl", "executed_at"]].rename(
                        columns={
                            "ticker": "Symbol", "side": "Side", "quantity": "Shares",
                            "execution_price": "Fill Price (₹)", "commission": "Comm (₹)",
                            "slippage": "Slippage (₹)", "realized_pnl": "Realized PnL",
                            "executed_at": "Executed At"
                        }
                    ),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No executed trades recorded yet.")

# -----------------------------------------------------------------------------
# PAGE 4: 💼 PORTFOLIOS & MPT STUDIO
# -----------------------------------------------------------------------------
elif selected_page == "💼 Portfolios & MPT":
    st.header("💼 Modern Portfolio Theory (MPT) & Risk Analytics")
    active_pid = st.session_state.get("selected_portfolio_id")

    tab_overview, tab_mpt, tab_rebalance, tab_manage = st.tabs([
        "Portfolio Risk Deck", "MPT SLSQP Optimizer", "Rebalance Calculator", "Manage Books & Cash"
    ])

    with tab_overview:
        if active_pid:
            p_data, _ = api_get(f"/portfolios/{active_pid}")
            perf_data, _ = api_get(f"/portfolios/{active_pid}/performance")
            
            if perf_data and "risk_metrics" in perf_data:
                rm = perf_data["risk_metrics"]
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Annualized Return", f"{float(rm.get('annualized_return', 0))*100:.2f}%")
                r2.metric("Annualized Volatility", f"{float(rm.get('annualized_volatility', 0))*100:.2f}%")
                r3.metric("Sharpe Ratio", f"{float(rm.get('sharpe_ratio', 0)):.2f}")
                r4.metric("Sortino Ratio", f"{float(rm.get('sortino_ratio', 0)):.2f}")

                r5, r6, r7, r8 = st.columns(4)
                r5.metric("Value at Risk (VaR 95%)", f"{float(rm.get('var_95', 0))*100:.2f}%")
                r6.metric("Conditional VaR (CVaR)", f"{float(rm.get('cvar_95', 0))*100:.2f}%")
                r7.metric("Maximum Drawdown", f"{float(rm.get('max_drawdown', 0))*100:.2f}%")
                r8.metric("Calmar Ratio", f"{float(rm.get('calmar_ratio', 0)):.2f}")
            else:
                st.info("Risk metrics require historical trading performance data.")
        else:
            st.warning("Please sign in and select a portfolio.")

    with tab_mpt:
        st.subheader("SciPy SLSQP Modern Portfolio Optimization")
        st.caption("Solves for optimal quadratic risk-return allocations across assets.")
        
        mpt_syms = st.multiselect(
            "Select Asset Universe (min 2)",
            available_symbols,
            default=["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        )
        rf_rate = st.slider("Risk-Free Benchmark Rate (%)", min_value=0.0, max_value=12.0, value=6.0, step=0.25) / 100.0

        if st.button("🚀 Solve MPT Optimization", type="primary"):
            if len(mpt_syms) < 2:
                st.error("Please select at least 2 assets.")
            else:
                with st.spinner("Computing quadratic tangency & risk parity allocations..."):
                    opt_res, opt_err = api_post("/portfolios/optimize", {
                        "symbols": mpt_syms,
                        "risk_free_rate": rf_rate
                    })
                    if opt_res:
                        # 3 Portfolios Display
                        c_ms, c_mv, c_rp = st.columns(3)
                        
                        with c_ms:
                            st.markdown("🎯 **Max Sharpe Portfolio**")
                            ms = opt_res["max_sharpe"]
                            st.write(f"**Exp. Return:** {ms['expected_return']*100:.2f}%")
                            st.write(f"**Volatility:** {ms['volatility']*100:.2f}%")
                            st.write(f"**Sharpe Ratio:** {ms['sharpe_ratio']:.2f}")
                            df_ms_w = pd.DataFrame([{"Asset": k, "Weight": f"{float(v)*100:.1f}%"} for k, v in ms["weights"].items() if float(v) > 0.001])
                            st.dataframe(df_ms_w, use_container_width=True, hide_index=True)

                        with c_mv:
                            st.markdown("🛡️ **Minimum Variance**")
                            mv = opt_res["min_variance"]
                            st.write(f"**Exp. Return:** {mv['expected_return']*100:.2f}%")
                            st.write(f"**Volatility:** {mv['volatility']*100:.2f}%")
                            st.write(f"**Sharpe Ratio:** {mv['sharpe_ratio']:.2f}")
                            df_mv_w = pd.DataFrame([{"Asset": k, "Weight": f"{float(v)*100:.1f}%"} for k, v in mv["weights"].items() if float(v) > 0.001])
                            st.dataframe(df_mv_w, use_container_width=True, hide_index=True)

                        with c_rp:
                            st.markdown("⚖️ **Risk Parity (ERC)**")
                            rp = opt_res["risk_parity"]
                            st.write(f"**Exp. Return:** {rp['expected_return']*100:.2f}%")
                            st.write(f"**Volatility:** {rp['volatility']*100:.2f}%")
                            st.write(f"**Sharpe Ratio:** {rp['sharpe_ratio']:.2f}")
                            df_rp_w = pd.DataFrame([{"Asset": k, "Weight": f"{float(v)*100:.1f}%"} for k, v in rp["weights"].items() if float(v) > 0.001])
                            st.dataframe(df_rp_w, use_container_width=True, hide_index=True)

                        # Plot Efficient Frontier Curve
                        if opt_res.get("frontier_curve"):
                            df_front = pd.DataFrame(opt_res["frontier_curve"])
                            fig_mpt = go.Figure()
                            fig_mpt.add_trace(go.Scatter(
                                x=df_front["volatility"] * 100,
                                y=df_front["expected_return"] * 100,
                                mode="lines+markers",
                                name="Efficient Frontier",
                                line=dict(color="#0284C7", width=2)
                            ))
                            fig_mpt.add_trace(go.Scatter(
                                x=[ms["volatility"] * 100],
                                y=[ms["expected_return"] * 100],
                                mode="markers",
                                name="Max Sharpe (Tangency)",
                                marker=dict(size=14, color="#10B981", symbol="star")
                            ))
                            fig_mpt.add_trace(go.Scatter(
                                x=[mv["volatility"] * 100],
                                y=[mv["expected_return"] * 100],
                                mode="markers",
                                name="Min Variance",
                                marker=dict(size=12, color="#8B5CF6", symbol="diamond")
                            ))
                            fig_mpt.update_layout(
                                title="MPT Efficient Frontier Curve (Risk vs. Return)",
                                xaxis_title="Annualized Volatility (%)",
                                yaxis_title="Annualized Expected Return (%)",
                                height=420,
                                margin=dict(l=0, r=0, t=40, b=0)
                            )
                            st.plotly_chart(fig_mpt, use_container_width=True)
                    else:
                        st.error(opt_err)

    with tab_rebalance:
        st.subheader("Target Asset Allocation & Delta Rebalancer")
        if active_pid:
            st.caption("Specify desired percentage weight targets for assets in this portfolio book.")
            col_target1, col_target2 = st.columns(2)
            with col_target1:
                reb_sym1 = st.selectbox("Asset 1", available_symbols, index=0, key="reb_s1")
                reb_w1 = st.number_input("Target % Weight 1", min_value=0.0, max_value=100.0, value=50.0, step=5.0)
            with col_target2:
                reb_sym2 = st.selectbox("Asset 2", available_symbols, index=1, key="reb_s2")
                reb_w2 = st.number_input("Target % Weight 2", min_value=0.0, max_value=100.0, value=50.0, step=5.0)

            if st.button("Compute Rebalance Orders", type="primary"):
                reb_payload = {
                    "targets": [
                        {"symbol": reb_sym1, "target_weight_pct": float(reb_w1)},
                        {"symbol": reb_sym2, "target_weight_pct": float(reb_w2)}
                    ]
                }
                reb_res, reb_err = api_post(f"/portfolios/{active_pid}/rebalance", reb_payload)
                if reb_res and "actions" in reb_res:
                    st.success(f"Rebalance plan computed! Buy Value: ₹{reb_res['total_buy_value']:,.2f} | Sell Value: ₹{reb_res['total_sell_value']:,.2f}")
                    df_actions = pd.DataFrame(reb_res["actions"])
                    st.dataframe(df_actions, use_container_width=True)
                else:
                    st.error(reb_err)
        else:
            st.warning("Please select a portfolio book.")

    with tab_manage:
        st.subheader("Manage Portfolios & Capital Flow")
        col_new_p, col_cash_flow = st.columns(2)
        
        with col_new_p:
            st.markdown("#### Create New Portfolio Book")
            new_p_name = st.text_input("Portfolio Name", value="Momentum Alpha Book")
            new_p_desc = st.text_input("Description", value="Quantitative systematic equity book")
            new_p_cash = st.number_input("Initial Capital (INR)", min_value=10000.0, value=1000000.0, step=50000.0)
            if st.button("Create Portfolio"):
                res, err = api_post("/portfolios", {
                    "name": new_p_name,
                    "description": new_p_desc,
                    "initial_cash": float(new_p_cash)
                })
                if res:
                    st.success(f"Created portfolio: {res['name']} (#{res['id']})")
                    st.session_state["selected_portfolio_id"] = res["id"]
                    st.rerun()
                else:
                    st.error(err)

        with col_cash_flow:
            if active_pid:
                st.markdown("#### Deposit / Withdraw Capital")
                transfer_type = st.radio("Transfer Type", ["Deposit", "Withdrawal"], horizontal=True)
                transfer_amt = st.number_input("Amount (INR)", min_value=100.0, value=50000.0, step=1000.0)
                transfer_notes = st.text_input("Notes", value="Periodic capital re-allocation")
                
                if st.button("Submit Cash Transfer"):
                    endpoint = f"/portfolios/{active_pid}/deposit" if transfer_type == "Deposit" else f"/portfolios/{active_pid}/withdraw"
                    res, err = api_post(endpoint, {"amount": float(transfer_amt), "notes": transfer_notes})
                    if res:
                        st.success(f"{transfer_type} completed! New balance: ₹{res['cash_balance']:,.2f}")
                        st.rerun()
                    else:
                        st.error(err)

# -----------------------------------------------------------------------------
# PAGE 5: 🧪 BACKTEST STUDIO
# -----------------------------------------------------------------------------
elif selected_page == "🧪 Backtest Studio":
    st.header("🧪 Event-Driven Strategy Backtesting Lab")
    st.caption("Bar-by-bar historical strategy simulation with realistic slippage and commissions.")

    col_cfg1, col_cfg2, col_cfg3 = st.columns([2, 2, 2])
    with col_cfg1:
        bt_strategy = st.selectbox("Strategy Algorithm", ["SMA_CROSS", "RSI_MEAN_REVERSION", "MACD", "MOMENTUM"])
        bt_symbol = st.selectbox("Asset Symbol", available_symbols, index=0)
    with col_cfg2:
        bt_start = st.date_input("Start Date", value=date(2021, 1, 1))
        bt_end = st.date_input("End Date", value=date(2026, 9, 28))
    with col_cfg3:
        bt_cash = st.number_input("Starting Capital (₹)", min_value=10000.0, value=1000000.0, step=50000.0)

    # Strategy Parameters
    st.markdown("#### Strategy Parameters")
    bt_params = {}
    if bt_strategy == "SMA_CROSS":
        p1, p2 = st.columns(2)
        bt_params["fast_period"] = p1.slider("Fast SMA Period", 5, 50, 20)
        bt_params["slow_period"] = p2.slider("Slow SMA Period", 20, 200, 50)
    elif bt_strategy == "RSI_MEAN_REVERSION":
        p1, p2, p3 = st.columns(3)
        bt_params["rsi_period"] = p1.slider("RSI Period", 5, 30, 14)
        bt_params["oversold_threshold"] = p2.slider("Oversold Buy Threshold", 15, 40, 30)
        bt_params["overbought_threshold"] = p3.slider("Overbought Sell Threshold", 60, 85, 70)
    elif bt_strategy == "MACD":
        p1, p2, p3 = st.columns(3)
        bt_params["fast_period"] = p1.slider("Fast EMA", 8, 20, 12)
        bt_params["slow_period"] = p2.slider("Slow EMA", 20, 40, 26)
        bt_params["signal_period"] = p3.slider("Signal Period", 5, 15, 9)
    else:  # MOMENTUM
        bt_params["lookback_period"] = st.slider("Momentum Lookback Period (Days)", 10, 120, 30)

    if st.button("🚀 Run Event-Driven Simulation", type="primary"):
        if not st.session_state.get("token"):
            st.error("Please sign in to run and record strategy backtests.")
        else:
            with st.spinner("Executing simulation bar-by-bar..."):
                bt_req = {
                    "strategy_type": bt_strategy,
                    "symbol": bt_symbol,
                    "start_date": bt_start.isoformat(),
                    "end_date": bt_end.isoformat(),
                    "initial_cash": float(bt_cash),
                    "parameters": bt_params
                }
                bt_res, bt_err = api_post("/backtests/run", bt_req)
                if bt_res:
                    st.success(f"Backtest completed successfully! Total Return: {bt_res['total_return_pct']:+.2f}%")
                    
                    # KPIs
                    k1, k2, k3, k4, k5, k6 = st.columns(6)
                    k1.metric("Final Equity", f"₹{bt_res['final_equity']:,.2f}")
                    k2.metric("CAGR", f"{bt_res.get('cagr', 0):.2f}%")
                    k3.metric("Sharpe Ratio", f"{bt_res.get('sharpe_ratio', 0):.2f}")
                    k4.metric("Max Drawdown", f"{bt_res.get('max_drawdown_pct', 0):.2f}%")
                    k5.metric("Win Rate", f"{bt_res.get('win_rate', 0):.1f}%")
                    k6.metric("Total Trades", f"{bt_res.get('total_trades', 0)}")

                    # Cumulative Equity Curve Chart
                    if bt_res.get("equity_curve"):
                        df_eq = pd.DataFrame(bt_res["equity_curve"])
                        df_eq["date"] = pd.to_datetime(df_eq["date"])
                        
                        fig_bt = go.Figure()
                        fig_bt.add_trace(go.Scatter(
                            x=df_eq["date"], y=df_eq["equity"],
                            mode="lines", name="Strategy Equity",
                            line=dict(color="#10B981", width=2.5)
                        ))
                        bm_col = "benchmark_equity" if "benchmark_equity" in df_eq else ("benchmark" if "benchmark" in df_eq else None)
                        if bm_col:
                            fig_bt.add_trace(go.Scatter(
                                x=df_eq["date"], y=df_eq[bm_col],
                                mode="lines", name="Buy & Hold Benchmark",
                                line=dict(color="#94A3B8", width=1.5, dash="dot")
                            ))
                        fig_bt.update_layout(
                            title=f"{bt_strategy} on {bt_symbol} — Cumulative Equity Progression",
                            xaxis_title="Date",
                            yaxis_title="Portfolio Equity (₹)",
                            height=400,
                            margin=dict(l=0, r=0, t=40, b=0)
                        )
                        st.plotly_chart(fig_bt, use_container_width=True)

                    # Trade Log Table
                    if bt_res.get("trades"):
                        st.subheader("Simulated Trade Executions")
                        df_trades = pd.DataFrame(bt_res["trades"])
                        st.dataframe(df_trades, use_container_width=True)
                else:
                    st.error(bt_err)

# -----------------------------------------------------------------------------
# PAGE 6: 🤖 ML FORECAST STUDIO
# -----------------------------------------------------------------------------
elif selected_page == "🤖 ML Forecast Studio":
    st.header("🤖 Machine Learning Price Forecasting & Alpha Signals")
    st.caption("Generates out-of-sample forward projections with 95% statistical confidence cones.")

    c_fc1, c_fc2, c_fc3 = st.columns(3)
    with c_fc1:
        fc_sym = st.selectbox("Asset Symbol", available_symbols, index=0)
        fc_model = st.selectbox("Forecasting Algorithm", ["GRADIENT_BOOSTING", "RIDGE", "ARIMA", "EXPONENTIAL_SMOOTHING"])
    with c_fc2:
        fc_days = st.slider("Forecast Horizon (Trading Days)", 10, 90, 30)
    with c_fc3:
        fc_lookback = st.slider("Training Lookback (Years)", 1, 8, 3)

    if st.button("🔮 Generate ML Forecast", type="primary"):
        with st.spinner(f"Fitting {fc_model} model and generating {fc_days}-day projections..."):
            fc_req = {
                "symbol": fc_sym,
                "model_type": fc_model,
                "forecast_days": fc_days,
                "lookback_years": fc_lookback
            }
            fc_res, fc_err = api_post("/forecasts/generate", fc_req)
            if fc_res:
                sig = fc_res.get("signal", {})
                met = fc_res.get("metrics", {})
                
                # Signal Badge & Projection Card
                st.subheader(f"Signal: {sig.get('signal_type', 'NEUTRAL')}")
                st.write(sig.get("reasoning", ""))
                
                col_met1, col_met2, col_met3, col_met4 = st.columns(4)
                col_met1.metric("Current Price", f"₹{fc_res['current_price']:,.2f}")
                col_met2.metric("Target Projected Price", f"₹{fc_res['predicted_target_price']:,.2f}", f"{fc_res['projected_return_pct']:+.2f}%")
                col_met3.metric("Directional Accuracy", f"{met.get('directional_accuracy_pct', 0):.1f}%")
                col_met4.metric("RMSE Error", f"₹{met.get('rmse', 0):.2f}")

                # Forecast Path & Confidence Cones
                if fc_res.get("series"):
                    df_series = pd.DataFrame(fc_res["series"])
                    df_series["date"] = pd.to_datetime(df_series["date"])
                    
                    fig_fc = go.Figure()
                    # Actuals
                    fig_fc.add_trace(go.Scatter(
                        x=df_series["date"], y=df_series["actual"],
                        mode="lines", name="Historical Actual Close",
                        line=dict(color="#10B981", width=2)
                    ))
                    # Predicted
                    fig_fc.add_trace(go.Scatter(
                        x=df_series["date"], y=df_series["predicted"],
                        mode="lines", name="Predicted Trajectory",
                        line=dict(color="#0284C7", width=2.5, dash="dash")
                    ))
                    # 95% Upper / Lower Bands
                    if "upper_bound" in df_series and "lower_bound" in df_series:
                        fig_fc.add_trace(go.Scatter(
                            x=df_series["date"], y=df_series["upper_bound"],
                            mode="lines", name="95% Upper Bound",
                            line=dict(color="#BAE6FD", width=1, dash="dot")
                        ))
                        fig_fc.add_trace(go.Scatter(
                            x=df_series["date"], y=df_series["lower_bound"],
                            mode="lines", name="95% Lower Bound",
                            fill="tonexty", fillcolor="rgba(186, 230, 253, 0.2)",
                            line=dict(color="#BAE6FD", width=1, dash="dot")
                        ))
                    
                    fig_fc.update_layout(
                        title=f"{fc_sym} {fc_days}-Day ML Forecast with Confidence Envelope",
                        xaxis_title="Date",
                        yaxis_title="Price (INR)",
                        height=420,
                        margin=dict(l=0, r=0, t=40, b=0)
                    )
                    st.plotly_chart(fig_fc, use_container_width=True)

                st.caption(f"⚠️ {fc_res.get('disclaimer', '')}")
            else:
                st.error(fc_err)

# -----------------------------------------------------------------------------
# PAGE 7: 🔔 ALERTS & WATCHLISTS
# -----------------------------------------------------------------------------
elif selected_page == "🔔 Alerts & Watchlists":
    st.header("🔔 Price Alerts & Custom Market Watchlists")
    
    if not st.session_state.get("token"):
        st.warning("Please sign in to manage alerts and watchlists.")
    else:
        col_alert_form, col_alert_list = st.columns([1, 2])
        
        with col_alert_form:
            st.subheader("Set Price / Technical Alert")
            with st.form("create_alert_form"):
                a_sym = st.selectbox("Symbol", available_symbols)
                a_type = st.selectbox("Condition", ["PRICE_ABOVE", "PRICE_BELOW", "RSI_OVERBOUGHT", "RSI_OVERSOLD"])
                a_val = st.number_input("Target Value Threshold", min_value=1.0, value=1500.0, step=10.0)
                a_notes = st.text_input("Alert Notes", value="Key resistance level breakout")
                if st.form_submit_button("Create Alert", type="primary"):
                    res, err = api_post("/alerts", {
                        "symbol": a_sym,
                        "condition_type": a_type,
                        "target_value": float(a_val),
                        "notes": a_notes
                    })
                    if res:
                        st.success("Alert configured!")
                        st.rerun()
                    else:
                        st.error(err)

        with col_alert_list:
            st.subheader("Active Trigger Rules")
            if st.button("⚡ Evaluate Active Alerts Now"):
                chk_res, _ = api_post("/alerts/check")
                if chk_res:
                    st.info(f"Check completed: {chk_res.get('triggered_alerts_count', 0)} alerts triggered.")

            alerts_data, _ = api_get("/alerts")
            if alerts_data:
                for a in alerts_data:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    status_pill = "🔔 ACTIVE" if a.get("is_active") and not a.get("is_triggered") else "⚡ TRIGGERED"
                    c1.write(f"**{a['ticker']}**: {a['condition_type']} `{a['target_value']}` — *{a.get('notes', '')}*")
                    c2.caption(status_pill)
                    if c3.button("Delete", key=f"del_a_{a['id']}"):
                        api_delete(f"/alerts/{a['id']}")
                        st.rerun()
            else:
                st.info("No active alerts set.")

        st.divider()

        # Watchlists
        st.subheader("Personal Watchlists")
        wl_data, _ = api_get("/alerts/watchlists")
        if wl_data:
            for wl in wl_data:
                st.markdown(f"📁 **{wl['name']}**")
                st.write(", ".join(wl.get("symbols", [])))
        else:
            st.info("No watchlists created.")

# -----------------------------------------------------------------------------
# PAGE 8: 📑 REPORTS & BLOTTER
# -----------------------------------------------------------------------------
elif selected_page == "📑 Reports & Blotter":
    st.header("📑 Institutional Reports & Blotter Exports")
    active_pid = st.session_state.get("selected_portfolio_id")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Portfolio Holdings Blotter (CSV)")
        st.write("Export complete book valuation including average cost basis, market value, and unrealized profit/loss.")
        if active_pid:
            csv_url = f"{API_BASE_URL}/reports/portfolio/{active_pid}/csv"
            st.link_button("📥 Download Portfolio CSV", csv_url, use_container_width=True)
        else:
            st.info("Select a portfolio from the sidebar to export holdings.")

    with col_r2:
        st.subheader("Executed Trades Blotter (CSV)")
        st.write("Export simulated trade execution ledger containing fill timestamps, prices, commissions, and slippage.")
        if st.session_state.get("token"):
            trades_csv_url = f"{API_BASE_URL}/reports/trades/csv"
            st.link_button("📥 Download Trade Blotter CSV", trades_csv_url, use_container_width=True)
        else:
            st.info("Please sign in to export your trade ledger.")

