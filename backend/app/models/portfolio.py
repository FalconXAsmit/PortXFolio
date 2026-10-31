from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
    FEE = "FEE"
    DIVIDEND = "DIVIDEND"

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    initial_cash = Column(Numeric(18, 4), default=1000000.0, nullable=False)
    cash_balance = Column(Numeric(18, 4), default=1000000.0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Numeric(14, 4), default=0.0, nullable=False)
    average_buy_price = Column(Numeric(14, 4), default=0.0, nullable=False)
    total_invested = Column(Numeric(18, 4), default=0.0, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    symbol = relationship("Symbol", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol_id", name="uq_portfolio_symbol"),
    )

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # DEPOSIT, WITHDRAWAL, BUY, SELL, FEE
    amount = Column(Numeric(18, 4), nullable=False)  # signed or absolute amount
    balance_after = Column(Numeric(18, 4), nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
