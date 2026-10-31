import pytest
from decimal import Decimal
from backend.app.models import User, Portfolio, Holding, Order, Trade, Symbol, Price, OrderStatus, OrderType, OrderSide
from backend.app.services.trading_engine import TradingEngine
from backend.app.schemas.order import OrderCreate, OrderPreviewRequest

def test_trading_engine_buy_and_sell(db_session):
    # Setup test user and portfolio
    user = db_session.query(User).filter(User.email == "test_trader@portfolix.com").first()
    portfolio = db_session.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    initial_cash = portfolio.cash_balance

    # Ensure symbol and price exist in test DB
    symbol = db_session.query(Symbol).filter(Symbol.ticker == "RELIANCE").first()
    if not symbol:
        symbol = Symbol(ticker="RELIANCE", name="Reliance Industries Ltd", exchange="NSE", currency="INR")
        db_session.add(symbol)
        db_session.flush()

    price_rec = db_session.query(Price).filter(Price.symbol_id == symbol.id).first()
    if not price_rec:
        price_rec = Price(
            symbol_id=symbol.id,
            date=db_session.query(Price.date).first() or "2026-09-28",
            open=Decimal("1500.00"),
            high=Decimal("1520.00"),
            low=Decimal("1490.00"),
            close=Decimal("1500.00"),
            volume=100000
        )
        db_session.add(price_rec)
        db_session.commit()

    engine = TradingEngine(db_session)

    # 1. Preview BUY order
    prev_req = OrderPreviewRequest(
        symbol="RELIANCE",
        portfolio_id=portfolio.id,
        side="BUY",
        quantity=Decimal("10")
    )
    preview = engine.preview_order(user.id, prev_req)
    assert preview.can_execute is True
    assert preview.estimated_gross > 0
    assert preview.estimated_commission > 0

    # 2. Place BUY order
    buy_in = OrderCreate(
        symbol="RELIANCE",
        portfolio_id=portfolio.id,
        order_type="MARKET",
        side="BUY",
        quantity=Decimal("10")
    )
    buy_order = engine.place_order(user.id, buy_in)
    assert buy_order.status == OrderStatus.FILLED.value
    assert buy_order.filled_quantity == Decimal("10")

    # Verify cash deducted and holding created
    db_session.refresh(portfolio)
    assert portfolio.cash_balance < initial_cash
    
    holding = db_session.query(Holding).filter(Holding.portfolio_id == portfolio.id, Holding.symbol_id == symbol.id).first()
    assert holding is not None
    assert holding.quantity >= Decimal("10")
    assert holding.average_buy_price > Decimal("0")

    # 3. Place SELL order
    prev_cash = portfolio.cash_balance
    sell_in = OrderCreate(
        symbol="RELIANCE",
        portfolio_id=portfolio.id,
        order_type="MARKET",
        side="SELL",
        quantity=Decimal("5")
    )
    sell_order = engine.place_order(user.id, sell_in)
    assert sell_order.status == OrderStatus.FILLED.value

    db_session.refresh(portfolio)
    assert portfolio.cash_balance > prev_cash

    # 4. Attempt to oversell (reject test)
    oversell_in = OrderCreate(
        symbol="RELIANCE",
        portfolio_id=portfolio.id,
        order_type="MARKET",
        side="SELL",
        quantity=Decimal("999999")
    )
    oversell_order = engine.place_order(user.id, oversell_in)
    assert oversell_order.status == OrderStatus.REJECTED.value
    assert "Insufficient holding" in oversell_order.reject_reason

def test_trading_engine_insufficient_funds(db_session):
    user = db_session.query(User).filter(User.email == "test_trader@portfolix.com").first()
    portfolio = db_session.query(Portfolio).filter(Portfolio.user_id == user.id).first()

    engine = TradingEngine(db_session)
    # Order requiring way more cash than balance
    huge_order = OrderCreate(
        symbol="RELIANCE",
        portfolio_id=portfolio.id,
        order_type="MARKET",
        side="BUY",
        quantity=Decimal("100000000")
    )
    res = engine.place_order(user.id, huge_order)
    assert res.status == OrderStatus.REJECTED.value
    assert "Insufficient cash" in res.reject_reason
