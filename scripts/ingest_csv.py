import os
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
from pydantic import ValidationError
from decimal import Decimal

# Ensure backend path is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models import Symbol, Price, User, Portfolio, AuditLog, UserRole
from backend.app.core.security import get_password_hash
from backend.app.schemas.market import PriceValidationSchema

# Sector & Company metadata for the 20 NSE bluechip equities
NSE_EQUITY_METADATA = {
    "ASIANPAINT": {
        "name": "Asian Paints Ltd",
        "sector": "Consumer Discretionary",
        "industry": "Paints & Coatings",
        "exchange": "NSE",
        "currency": "INR"
    },
    "AXISBANK": {
        "name": "Axis Bank Ltd",
        "sector": "Financial Services",
        "industry": "Private Sector Banking",
        "exchange": "NSE",
        "currency": "INR"
    },
    "BAJFINANCE": {
        "name": "Bajaj Finance Ltd",
        "sector": "Financial Services",
        "industry": "Non-Banking Financial Company",
        "exchange": "NSE",
        "currency": "INR"
    },
    "BHARTIARTL": {
        "name": "Bharti Airtel Ltd",
        "sector": "Telecommunications",
        "industry": "Telecom Services",
        "exchange": "NSE",
        "currency": "INR"
    },
    "HCLTECH": {
        "name": "HCL Technologies Ltd",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "exchange": "NSE",
        "currency": "INR"
    },
    "HDFCBANK": {
        "name": "HDFC Bank Ltd",
        "sector": "Financial Services",
        "industry": "Private Sector Banking",
        "exchange": "NSE",
        "currency": "INR"
    },
    "HINDUNILVR": {
        "name": "Hindustan Unilever Ltd",
        "sector": "Consumer Staples",
        "industry": "FMCG",
        "exchange": "NSE",
        "currency": "INR"
    },
    "ICICIBANK": {
        "name": "ICICI Bank Ltd",
        "sector": "Financial Services",
        "industry": "Private Sector Banking",
        "exchange": "NSE",
        "currency": "INR"
    },
    "INFY": {
        "name": "Infosys Ltd",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "exchange": "NSE",
        "currency": "INR"
    },
    "ITC": {
        "name": "ITC Ltd",
        "sector": "Consumer Staples",
        "industry": "Diversified FMCG",
        "exchange": "NSE",
        "currency": "INR"
    },
    "KOTAKBANK": {
        "name": "Kotak Mahindra Bank Ltd",
        "sector": "Financial Services",
        "industry": "Private Sector Banking",
        "exchange": "NSE",
        "currency": "INR"
    },
    "LT": {
        "name": "Larsen & Toubro Ltd",
        "sector": "Industrials",
        "industry": "Engineering & Construction",
        "exchange": "NSE",
        "currency": "INR"
    },
    "MARUTI": {
        "name": "Maruti Suzuki India Ltd",
        "sector": "Consumer Discretionary",
        "industry": "Automobiles",
        "exchange": "NSE",
        "currency": "INR"
    },
    "NESTLEIND": {
        "name": "Nestle India Ltd",
        "sector": "Consumer Staples",
        "industry": "Food & Beverages",
        "exchange": "NSE",
        "currency": "INR"
    },
    "RELIANCE": {
        "name": "Reliance Industries Ltd",
        "sector": "Energy",
        "industry": "Oil, Gas & Diversified",
        "exchange": "NSE",
        "currency": "INR"
    },
    "SBIN": {
        "name": "State Bank of India",
        "sector": "Financial Services",
        "industry": "Public Sector Banking",
        "exchange": "NSE",
        "currency": "INR"
    },
    "SUNPHARMA": {
        "name": "Sun Pharmaceutical Industries Ltd",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "exchange": "NSE",
        "currency": "INR"
    },
    "TCS": {
        "name": "Tata Consultancy Services Ltd",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "exchange": "NSE",
        "currency": "INR"
    },
    "TITAN": {
        "name": "Titan Company Ltd",
        "sector": "Consumer Discretionary",
        "industry": "Gems, Jewelry & Watches",
        "exchange": "NSE",
        "currency": "INR"
    },
    "WIPRO": {
        "name": "Wipro Ltd",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "exchange": "NSE",
        "currency": "INR"
    }
}

def locate_csv_file() -> Path:
    candidates = [
        PROJECT_ROOT / "data" / "processed" / "cleaned_stock_data.csv",
        PROJECT_ROOT / "cleaned_stock_data.csv",
        PROJECT_ROOT / "data" / "stock_data.csv"
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not locate stock data CSV in candidates: {candidates}")

def run_ingestion(csv_path: Path = None, batch_size: int = 5000):
    start_time = time.time()
    print("=" * 70)
    print("PORTFOLIX IDEMPOTENT ETL INGESTION PIPELINE")
    print("=" * 70)

    # 1. Initialize schema
    print("\n[1/5] Ensuring Database Tables Exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if csv_path is None:
        csv_path = locate_csv_file()
    print(f"Reading data source from: {csv_path}")

    # 2. Read dataset
    df = pd.read_csv(csv_path)
    total_raw_rows = len(df)
    print(f"Loaded {total_raw_rows:,} raw records from CSV")

    # 3. Populate / Sync Symbols
    print("\n[2/5] Synchronizing Symbol Universe & Sectors...")
    unique_tickers = df["Symbol"].dropna().unique().tolist()
    symbol_map = {} # ticker -> Symbol model

    for ticker in unique_tickers:
        ticker_str = str(ticker).strip().upper()
        meta = NSE_EQUITY_METADATA.get(ticker_str, {
            "name": f"{ticker_str} India Ltd",
            "sector": "Diversified",
            "industry": "General",
            "exchange": "NSE",
            "currency": "INR"
        })
        symbol = db.query(Symbol).filter(Symbol.ticker == ticker_str).first()
        if not symbol:
            symbol = Symbol(
                ticker=ticker_str,
                name=meta["name"],
                sector=meta["sector"],
                industry=meta["industry"],
                exchange=meta["exchange"],
                currency=meta["currency"],
                is_active=True
            )
            db.add(symbol)
            db.flush()
        else:
            # Update metadata if exists
            symbol.name = meta["name"]
            symbol.sector = meta["sector"]
            symbol.industry = meta["industry"]
        symbol_map[ticker_str] = symbol

    db.commit()
    print(f"Verified {len(symbol_map)} symbols in database.")

    # 4. Validate and Process Price Records
    print("\n[3/5] Validating Price Records via Pydantic & Cleaning...")
    valid_records = []
    skipped_anomalies = []
    zero_vol_count = 0

    for idx, row in df.iterrows():
        try:
            # Check for NaN prices first
            if pd.isna(row.get("Open")) or pd.isna(row.get("High")) or pd.isna(row.get("Low")) or pd.isna(row.get("Close")):
                skipped_anomalies.append(f"Row {idx}: Symbol={row.get('Symbol')} Date={row.get('Date')} has NaN prices.")
                continue

            parsed_date = pd.to_datetime(row["Date"]).date()
            symbol_str = str(row["Symbol"]).strip().upper()

            # Pydantic schema validation
            validated = PriceValidationSchema(
                Date=parsed_date,
                Symbol=symbol_str,
                Open=float(row["Open"]),
                High=float(row["High"]),
                Low=float(row["Low"]),
                Close=float(row["Close"]),
                Volume=int(row["Volume"]) if not pd.isna(row.get("Volume")) else 0
            )

            if validated.Volume == 0:
                zero_vol_count += 1

            sym = symbol_map.get(symbol_str)
            if not sym:
                continue

            valid_records.append({
                "symbol_id": sym.id,
                "date": validated.Date,
                "open": round(Decimal(str(validated.Open)), 4),
                "high": round(Decimal(str(validated.High)), 4),
                "low": round(Decimal(str(validated.Low)), 4),
                "close": round(Decimal(str(validated.Close)), 4),
                "volume": validated.Volume
            })
        except (ValidationError, Exception) as e:
            skipped_anomalies.append(f"Row {idx} Symbol={row.get('Symbol')} Date={row.get('Date')} validation error: {str(e)}")

    print(f"Validation summary: {len(valid_records):,} valid records, {len(skipped_anomalies)} anomalies skipped.")

    # 5. Idempotent Ingestion using Batch Loading
    print("\n[4/5] Ingesting Price Records (Idempotent)...")
    # Check existing (symbol_id, date) pairs to guarantee true idempotency
    existing_pairs = set(
        db.query(Price.symbol_id, Price.date).all()
    )
    print(f"Found {len(existing_pairs):,} existing price records in database.")

    to_insert = []
    for rec in valid_records:
        pair = (rec["symbol_id"], rec["date"])
        if pair not in existing_pairs:
            to_insert.append(rec)
            existing_pairs.add(pair)

    print(f"Records to insert: {len(to_insert):,}")

    # Perform batch insert
    inserted_count = 0
    if to_insert:
        for i in range(0, len(to_insert), batch_size):
            batch = to_insert[i:i + batch_size]
            db.bulk_insert_mappings(Price, batch)
            db.commit()
            inserted_count += len(batch)
            print(f"  Inserted {inserted_count:,} / {len(to_insert):,} records...")

    # 6. Ensure default seed users & demo portfolio
    print("\n[5/5] Ensuring Default Users and Demo Portfolios...")
    demo_trader = db.query(User).filter(User.email == "trader@portfolix.com").first()
    if not demo_trader:
        demo_trader = User(
            email="trader@portfolix.com",
            hashed_password=get_password_hash("trader123!"),
            full_name="Alex Mercer (Quant Trader)",
            role=UserRole.TRADER.value,
            is_active=True
        )
        db.add(demo_trader)
        db.flush()

        # Create demo portfolio
        demo_portfolio = Portfolio(
            user_id=demo_trader.id,
            name="Alpha Growth Portfolio",
            description="Multi-asset long-term algorithmic paper portfolio",
            initial_cash=1000000.0,
            cash_balance=1000000.0,
            currency="INR"
        )
        db.add(demo_portfolio)
        db.commit()

    admin_user = db.query(User).filter(User.email == "admin@portfolix.com").first()
    if not admin_user:
        admin_user = User(
            email="admin@portfolix.com",
            hashed_password=get_password_hash("admin123!"),
            full_name="System Administrator",
            role=UserRole.ADMIN.value,
            is_active=True
        )
        db.add(admin_user)
        db.commit()

    elapsed = time.time() - start_time
    total_db_prices = db.query(Price).count()
    db.close()

    # Generate Data Quality Summary Report
    print("\n" + "=" * 70)
    print("DATA QUALITY & INGESTION REPORT")
    print("=" * 70)
    print(f"Total Raw CSV Records    : {total_raw_rows:,}")
    print(f"Validated Valid Records  : {len(valid_records):,}")
    print(f"Anomalies Filtered Out   : {len(skipped_anomalies)}")
    for a in skipped_anomalies:
        print(f"   -> {a}")
    print(f"Zero-Volume Records      : {zero_vol_count:,}")
    print(f"New Records Inserted     : {inserted_count:,}")
    print(f"Total Records in DB      : {total_db_prices:,}")
    print(f"Time Taken               : {elapsed:.2f}s")
    print("=" * 70)
    print("ETL Ingestion Complete Successfully!")

if __name__ == "__main__":
    run_ingestion()
