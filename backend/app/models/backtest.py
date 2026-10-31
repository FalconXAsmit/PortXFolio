from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    strategy_type = Column(String(50), nullable=False, index=True)  # SMA_CROSS, RSI_MEAN_REVERSION, MACD, MOMENTUM, BOLLINGER_BREAKOUT
    symbol_or_universe = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_cash = Column(Numeric(18, 4), nullable=False)
    final_equity = Column(Numeric(18, 4), nullable=False)
    total_return_pct = Column(Numeric(10, 4), nullable=False)
    benchmark_return_pct = Column(Numeric(10, 4), nullable=True)
    cagr = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    calmar_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown_pct = Column(Numeric(10, 4), nullable=True)
    win_rate = Column(Numeric(10, 4), nullable=True)
    profit_factor = Column(Numeric(10, 4), nullable=True)
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    parameters_json = Column(Text, nullable=True)  # Strategy params as JSON string
    equity_curve_json = Column(Text, nullable=True)  # Daily equity history as JSON string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="backtests")
    trades = relationship("BacktestTrade", back_populates="backtest", cascade="all, delete-orphan")

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    entry_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(14, 4), nullable=False)
    exit_price = Column(Numeric(14, 4), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    pnl = Column(Numeric(18, 4), nullable=False)
    return_pct = Column(Numeric(10, 4), nullable=False)
    holding_period_days = Column(Integer, default=1, nullable=False)

    # Relationships
    backtest = relationship("Backtest", back_populates="trades")
