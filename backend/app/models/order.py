from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TimeInForce(str, enum.Enum):
    GTC = "GTC"  # Good 'til Cancelled
    DAY = "DAY"  # Day order
    IOC = "IOC"  # Immediate or Cancel

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_type = Column(String(20), default=OrderType.MARKET.value, nullable=False)
    side = Column(String(10), nullable=False)  # BUY / SELL
    status = Column(String(20), default=OrderStatus.PENDING.value, nullable=False, index=True)
    quantity = Column(Numeric(14, 4), nullable=False)
    filled_quantity = Column(Numeric(14, 4), default=0.0, nullable=False)
    price = Column(Numeric(14, 4), nullable=True)  # Limit price
    stop_price = Column(Numeric(14, 4), nullable=True)  # Trigger / Stop price
    time_in_force = Column(String(10), default=TimeInForce.GTC.value, nullable=False)
    reject_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    portfolio = relationship("Portfolio", back_populates="orders")
    symbol = relationship("Symbol", back_populates="orders")
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="RESTRICT"), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    execution_price = Column(Numeric(14, 4), nullable=False)
    commission = Column(Numeric(14, 4), default=0.0, nullable=False)
    slippage = Column(Numeric(14, 4), default=0.0, nullable=False)
    realized_pnl = Column(Numeric(18, 4), default=0.0, nullable=False)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    order = relationship("Order", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")
    symbol = relationship("Symbol", back_populates="trades")
