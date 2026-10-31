import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.database import SessionLocal
from backend.app.models import User, Portfolio, Holding, Order, Trade, Transaction, Watchlist, Alert, Backtest, Symbol, Price
from backend.app.services.trading_engine import TradingEngine
from backend.app.schemas.order import OrderCreate

def seed_demo_data():
    print("Seeding demo portfolio, orders, watchlists, and alerts...")
    db = SessionLocal()
    trader = db.query(User).filter(User.email == "trader@portfolix.com").first()
    if not trader:
        print("Trader user not found, please run scripts/ingest_csv.py first.")
        db.close()
        return

    portfolio = db.query(Portfolio).filter(Portfolio.user_id == trader.id).first()
    if not portfolio:
        portfolio = Portfolio(
            user_id=trader.id,
            name="Alpha Momentum Growth",
            description="Core multi-sector algorithmic strategy portfolio",
            initial_cash=1000000.0,
            cash_balance=1000000.0,
            currency="INR"
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    engine = TradingEngine(db)

    # Place initial demo trades if portfolio has no trades yet
    trade_count = db.query(Trade).filter(Trade.portfolio_id == portfolio.id).count()
    if trade_count == 0:
        demo_orders = [
            {"symbol": "RELIANCE", "side": "BUY", "quantity": Decimal("100"), "order_type": "MARKET"},
            {"symbol": "TCS", "side": "BUY", "quantity": Decimal("50"), "order_type": "MARKET"},
            {"symbol": "HDFCBANK", "side": "BUY", "quantity": Decimal("200"), "order_type": "MARKET"},
            {"symbol": "INFY", "side": "BUY", "quantity": Decimal("150"), "order_type": "MARKET"},
            {"symbol": "ICICIBANK", "side": "BUY", "quantity": Decimal("100"), "order_type": "MARKET"},
            {"symbol": "BHARTIARTL", "side": "BUY", "quantity": Decimal("100"), "order_type": "MARKET"},
            {"symbol": "TITAN", "side": "BUY", "quantity": Decimal("30"), "order_type": "MARKET"},
        ]
        for o in demo_orders:
            try:
                order_in = OrderCreate(
                    symbol=o["symbol"],
                    portfolio_id=portfolio.id,
                    side=o["side"],
                    quantity=o["quantity"],
                    order_type=o["order_type"]
                )
                engine.place_order(trader.id, order_in)
                print(f"Executed demo order: BUY {o['quantity']} {o['symbol']}")
            except Exception as e:
                print(f"Failed demo order for {o['symbol']}: {e}")

    # Ensure demo watchlists
    wl = db.query(Watchlist).filter(Watchlist.user_id == trader.id, Watchlist.name == "Tech & Banking Leaders").first()
    if not wl:
        from backend.app.schemas.alert import WatchlistCreate
        from backend.app.services.alert_service import AlertService
        alert_service = AlertService(db)
        alert_service.create_watchlist(
            trader.id,
            WatchlistCreate(
                name="Tech & Banking Leaders",
                symbols=["TCS", "INFY", "HCLTECH", "HDFCBANK", "ICICIBANK", "KOTAKBANK"]
            )
        )
        print("Created demo watchlist 'Tech & Banking Leaders'.")

    # Ensure demo alerts
    alert = db.query(Alert).filter(Alert.user_id == trader.id).first()
    if not alert:
        from backend.app.schemas.alert import AlertCreate
        from backend.app.services.alert_service import AlertService
        alert_service = AlertService(db)
        alert_service.create_alert(
            trader.id,
            AlertCreate(
                symbol="RELIANCE",
                condition_type="PRICE_ABOVE",
                target_value=Decimal("1500.00"),
                notes="Breakout above 1500 resistance level"
            )
        )
        alert_service.create_alert(
            trader.id,
            AlertCreate(
                symbol="TCS",
                condition_type="PRICE_BELOW",
                target_value=Decimal("3000.00"),
                notes="Dip buy threshold"
            )
        )
        print("Created demo price alerts.")

    db.close()
    print("Demo data seeding completed successfully!")

if __name__ == "__main__":
    seed_demo_data()
