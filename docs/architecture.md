# Portfolix System Architecture & Quantitative Design

## 1. Executive Summary
**Portfolix** is a high-performance, full-stack quantitative trading and portfolio management platform built with Python (FastAPI, SQLAlchemy 2.0, NumPy, SciPy, Scikit-Learn) and React 19 (TypeScript, Vite, Tailwind CSS, TradingView Lightweight Charts). It operates on 17 years (2009–2026) of historical equity data across 20 National Stock Exchange (NSE) bluechips.

```mermaid
graph TD
    subgraph Client ["Client Tier (React 19 + TypeScript)"]
        UI[Glassmorphic UI / Dashboard / Terminal]
        TVC[TradingView Lightweight Charts v5]
        Recharts[Risk & Markowitz Visualizer]
        State[TanStack Query + Auth Context]
    end

    subgraph API ["API & Routing Tier (FastAPI + Pydantic v2)"]
        Gateway[FastAPI Gateway / CORS / OpenAPI]
        AuthMid[JWT Auth & RBAC Middleware]
        Routers[Routers: Market, Orders, Portfolios, Backtest, Forecast, Alerts, Reports, Admin]
    end

    subgraph Engines ["Quantitative Engine Tier (Python)"]
        TradingEngine["ACID Trading Engine (Row-Locks, Slippage, Cost Basis)"]
        RiskEngine["Portfolio & Risk Engine (Sharpe, Sortino, VaR/CVaR)"]
        OptEngine["Markowitz MPT Quadratic Optimizer (SciPy SLSQP)"]
        BacktestEngine["Event-Driven Backtest Simulator (No Lookahead)"]
        MLEngine["ML Forecasting Engine (GBM, Ridge, ARIMA, ExpSmooth)"]
        AlertEngine["Real-time Indicator & Price Alert Monitor"]
    end

    subgraph Storage ["Persistence & Data Tier"]
        DB[(SQLite / PostgreSQL Relational DB)]
        CSV[(Historical Dataset: 83,979 bars)]
        ETL["Idempotent ETL Pipeline (scripts/ingest_csv.py)"]
    end

    UI --> Gateway
    Gateway --> AuthMid
    AuthMid --> Routers
    Routers --> Engines
    Engines --> DB
    ETL --> DB
    CSV --> ETL
```

---

## 2. Core Quantitative & Engineering Engines

### 2.1. ACID Paper Trading Engine
- **Transaction Isolation & Row-Level Locking**: Uses `with_for_update()` on PostgreSQL / single-writer transactional blocks in SQLite to ensure atomic balance deduction and share allocations.
- **Strict Money Math**: Eliminates binary floating-point drift by storing all cash, execution prices, commissions, and balances as fixed-point `Numeric(18, 4)` and computing in Python via `decimal.Decimal`.
- **Execution Modeling**:
  - **Slippage**: Configurable basis-point penalty (default 5 bps = 0.05%) applied dynamically to simulate bid-ask spread and market impact.
  - **Commissions**: Configurable broker fee (default 0.03% or flat minimum).
  - **Order Types**: `MARKET`, `LIMIT`, `STOP_LOSS`, `TAKE_PROFIT`.
- **Accounting & Cost Basis**: Tracks running weighted average cost per share, updating Realized P&L on closing transactions and Unrealized MTM P&L on open positions.

### 2.2. Portfolio Analytics & Markowitz Modern Portfolio Theory (MPT)
- **Risk Metrics (Annualized with 252 trading days factor)**:
  - **Sharpe Ratio**: $\frac{R_p - R_f}{\sigma_p}$
  - **Sortino Ratio**: $\frac{R_p - R_f}{\sigma_{down}}$, where downside deviation considers only returns below the risk-free rate $R_f$.
  - **Calmar Ratio**: $\frac{CAGR}{|MaxDrawdown|}$
  - **Value at Risk (VaR 95%)**: Computed via Historical Simulation percentile and Parametric Gaussian method.
  - **Conditional VaR (CVaR / Expected Shortfall 95%)**: Mean return in the worst 5% tail.
- **Markowitz Optimization (SciPy `SLSQP`)**:
  - Solves $\min_w \frac{1}{2} w^T \Sigma w$ subject to $\sum w_i = 1$ and $w_i \ge 0$ (no short sales).
  - Generates the continuous **Efficient Frontier** across target return ranges.
  - Computes **Maximum Sharpe Ratio Portfolio**, **Minimum Variance Portfolio**, and **Risk Parity (Equal Risk Contribution)** weights.
  - Computes exact rebalancing trade orders from current holdings to target optimal weights.

### 2.3. Event-Driven Strategy Backtesting Engine
- **Bar-by-Bar Simulation**: Iterates forward chronologically across daily OHLCV bars with strictly **zero lookahead bias**.
- **Strategies Supported**:
  - Dual SMA/EMA Golden Cross / Death Cross
  - RSI Overbought / Oversold Mean Reversion with Trend Filter
  - MACD Signal Line Crossover
  - Multi-Timeframe Price Momentum & Breakout
- **Parameter Optimization**: Grid search across parameter spaces (e.g. fast/slow window lengths) to identify optimal parameter sets.
- **Analytics Output**: Equity curve time series, Drawdown series, monthly return heatmap matrix, trade log with individual P&L and duration, Sharpe, CAGR, Profit Factor, Win Rate, and Average Trade Return.

### 2.4. Quantitative ML Forecasting Engine
- **Feature Engineering**: Generates multi-lag returns ($t-1, t-2, t-5, t-10, t-21$), rolling volatility, RSI(14), MACD, and Bollinger %B.
- **Models**:
  - Gradient Boosted Trees (`HistGradientBoostingRegressor`)
  - Regularized Linear Ridge Regression (`Ridge`)
  - Auto-Regressive Integrated Moving Average (`ARIMA(p,d,q)`)
  - Holt-Winters Exponential Smoothing (`ExponentialSmoothing`)
- **Strict Validation**: Time-series cross-validation / rolling forward split (never random k-fold shuffle to prevent future data leakage).
- **Signal Generation**: Maps forecasted returns and confidence intervals into `STRONG_BUY`, `BUY`, `HOLD`, `SELL`, or `STRONG_SELL` with confidence scores and explicit model performance metrics (RMSE, MAE, MAPE, Directional Accuracy).

---

## 3. Database Schema

```mermaid
erDiagram
    USERS ||--o{ PORTFOLIOS : owns
    USERS ||--o{ WATCHLISTS : owns
    USERS ||--o{ ALERTS : creates
    USERS ||--o{ AUDIT_LOGS : records
    PORTFOLIOS ||--o{ HOLDINGS : contains
    PORTFOLIOS ||--o{ ORDERS : submits
    PORTFOLIOS ||--o{ TRADES : executes
    PORTFOLIOS ||--o{ TRANSACTIONS : logs
    SYMBOLS ||--o{ PRICES : has
    SYMBOLS ||--o{ HOLDINGS : referenced_by
    SYMBOLS ||--o{ ORDERS : targets
    SYMBOLS ||--o{ WATCHLIST_ITEMS : listed_in
    WATCHLISTS ||--o{ WATCHLIST_ITEMS : contains
    USERS ||--o{ BACKTESTS : runs
    BACKTESTS ||--o{ BACKTEST_TRADES : produces

    USERS {
        int id PK
        string email UK
        string hashed_password
        string full_name
        string role
        boolean is_active
        datetime created_at
    }

    SYMBOLS {
        string ticker PK
        string name
        string sector
        string exchange
        string currency
        boolean is_active
    }

    PRICES {
        int id PK
        string symbol FK
        date date
        decimal open
        decimal high
        decimal low
        decimal close
        decimal volume
        decimal adjusted_close
    }

    PORTFOLIOS {
        int id PK
        int user_id FK
        string name
        decimal cash_balance
        decimal initial_capital
        string currency
        datetime created_at
    }

    HOLDINGS {
        int id PK
        int portfolio_id FK
        string symbol FK
        decimal quantity
        decimal average_cost
        datetime updated_at
    }

    ORDERS {
        int id PK
        int portfolio_id FK
        string symbol FK
        string side
        string order_type
        decimal quantity
        decimal limit_price
        decimal stop_price
        string status
        datetime created_at
    }

    TRADES {
        int id PK
        int order_id FK
        int portfolio_id FK
        string symbol FK
        string side
        decimal quantity
        decimal execution_price
        decimal commission
        decimal slippage
        decimal realized_pnl
        datetime executed_at
    }
```

---

## 4. Security, RBAC & Compliance
1. **Authentication**: JWT token mechanism using Cryptographic `HS256` or `RS256` signatures, with token expiration, auto-refresh headers, and salted `bcrypt` password hashes.
2. **Role-Based Access Control (RBAC)**:
   - `admin`: Full system control, user provisioning, database health metrics, audit logs.
   - `trader`: Portfolio creation, paper order execution, backtest studio, ML forecasting studio, custom alerts.
   - `viewer`: Read-only market data exploration, charting, and indicator inspection.
3. **Mandatory Disclaimer**: Displayed prominently across the frontend footer, navigation modals, API swagger docs, and PDF/CSV exports clarifying that all signals, analytics, and simulated trades are strictly educational and not financial advice.
