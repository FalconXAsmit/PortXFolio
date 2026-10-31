import yfinance as yf
import pandas as pd

stocks = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "AXISBANK.NS",
    "LT.NS",
    "HINDUNILVR.NS",
    "KOTAKBANK.NS",
    "BAJFINANCE.NS",
    "MARUTI.NS",
    "ASIANPAINT.NS",
    "HCLTECH.NS",
    "SUNPHARMA.NS",
    "WIPRO.NS",
    "NESTLEIND.NS",
    "TITAN.NS",
]

start_date = "2009-09-29"
end_date = "2026-09-29"

all_data = []
for ticker in stocks:
    print(f"Downloading data for {ticker}...")
    df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)

    if df.empty:
        print(f"No data found for {ticker}. Skipping...")
        continue

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df["Symbol"] = ticker.replace(".NS", "")
    df = df[[
        "Date",
        "Symbol",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]]
    all_data.append(df)

if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    final_df = final_df.sort_values(by=["Date", "Symbol"])
    final_df = final_df.drop_duplicates(subset=["Date", "Symbol"])
    final_df.to_csv("data/stock_data.csv", index=False)
    print("Data saved to data/stock_data.csv")
