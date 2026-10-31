import os
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "cleaned_stock_data.csv"

# 20 NSE Bluechips with realistic base prices
STOCKS_BASE = {
    "RELIANCE": 1400.0,
    "TCS": 3200.0,
    "HDFCBANK": 1500.0,
    "INFY": 1450.0,
    "ICICIBANK": 950.0,
    "SBIN": 600.0,
    "BHARTIARTL": 1150.0,
    "ITC": 420.0,
    "AXISBANK": 1020.0,
    "LT": 3400.0,
    "HINDUNILVR": 2400.0,
    "KOTAKBANK": 1750.0,
    "BAJFINANCE": 6800.0,
    "MARUTI": 11500.0,
    "ASIANPAINT": 2900.0,
    "HCLTECH": 1550.0,
    "SUNPHARMA": 1600.0,
    "WIPRO": 480.0,
    "NESTLEIND": 2450.0,
    "TITAN": 3350.0,
}

def generate_data():
    if OUTPUT_FILE.exists():
        print(f"Data file already exists at {OUTPUT_FILE}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating historical stock dataset for 20 NSE bluechips...")

    start_date = datetime(2020, 1, 1)
    end_date = datetime(2026, 9, 28)
    
    # Generate business trading days (weekdays)
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    num_days = len(dates)

    np.random.seed(42)
    all_rows = []

    for symbol, base_price in STOCKS_BASE.items():
        # Geometric brownian motion with positive drift
        daily_drift = 0.0004  # ~10% annual
        daily_vol = 0.015     # ~24% annual vol
        shocks = np.random.normal(daily_drift, daily_vol, num_days)
        price_multipliers = np.exp(shocks)
        
        prices = [base_price]
        for m in price_multipliers[:-1]:
            prices.append(max(10.0, prices[-1] * m))
        
        for d, close_p in zip(dates, prices):
            intraday_vol = np.random.uniform(0.005, 0.02)
            open_p = close_p * (1.0 + np.random.uniform(-0.008, 0.008))
            high_p = max(open_p, close_p) * (1.0 + intraday_vol)
            low_p = min(open_p, close_p) * (1.0 - intraday_vol)
            volume = int(np.random.lognormal(mean=12.5, sigma=0.6))
            
            all_rows.append({
                "Date": d.strftime("%Y-%m-%d"),
                "Symbol": symbol,
                "Open": round(float(open_p), 2),
                "High": round(float(high_p), 2),
                "Low": round(float(low_p), 2),
                "Close": round(float(close_p), 2),
                "Volume": volume
            })

    df = pd.DataFrame(all_rows)
    df.sort_values(by=["Date", "Symbol"], inplace=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Successfully generated {len(df):,} price records across {len(STOCKS_BASE)} symbols saved to:\n  {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_data()

