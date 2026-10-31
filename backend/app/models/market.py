from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), index=True, nullable=True)
    industry = Column(String(100), nullable=True)
    exchange = Column(String(50), default="NSE", nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    prices = relationship("Price", back_populates="symbol", cascade="all, delete-orphan")
    holdings = relationship("Holding", back_populates="symbol")
    orders = relationship("Order", back_populates="symbol")
    trades = relationship("Trade", back_populates="symbol")
    alerts = relationship("Alert", back_populates="symbol")

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Numeric(14, 4), nullable=False)
    high = Column(Numeric(14, 4), nullable=False)
    low = Column(Numeric(14, 4), nullable=False)
    close = Column(Numeric(14, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)

    # Relationships
    symbol = relationship("Symbol", back_populates="prices")

    __table_args__ = (
        UniqueConstraint("symbol_id", "date", name="uq_symbol_date"),
        Index("ix_price_symbol_date", "symbol_id", "date"),
    )
