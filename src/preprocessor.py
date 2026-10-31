import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "stock_data.csv"
)

PROCESSED_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

PROCESSED_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

# Loading data into the project

print("Loading dataset....")
df = pd.read_csv(INPUT_FILE)
print(f"Loaded {len(df):,} rows")

# Cleaning the raw data from duplicates and all
df["Date"] = pd.to_datetime(df["Date"])

# Sort data
df = df.sort_values(
    ["Symbol", "Date"]
).reset_index(drop=True)

# Remove exact duplicates
df = df.drop_duplicates()

# Missing values
print("\nMissing values:")

print(
    df.isnull().sum()
)

# Invalid Prices!!
print("\nChecking price data...")

invalid_prices = (
    (df["Open"] <= 0)
    | (df["High"] <= 0)
    | (df["Low"] <= 0)
    | (df["Close"] <= 0)
)

print(
    f"Invalid price rows: "
    f"{invalid_prices.sum()}"
)

# OHLC Consistency
invalid_ohlc = (
    (df["High"] < df["Open"])
    | (df["High"] < df["Close"])
    | (df["Low"] > df["Open"])
    | (df["Low"] > df["Close"])
)

print(
    f"Invalid OHLC rows: "
    f"{invalid_ohlc.sum()}"
)

# Zero Volume 
zero_volume = df["Volume"] <= 0

print(
    f"Zero-volume rows: "
    f"{zero_volume.sum()}"
)

# Display Dataset Sumarry
print("\n" + "=" * 60)
print("DATASET SUMMARY")
print("=" * 60)

print(
    f"Rows: {len(df):,}"
)

print(
    f"Stocks: {df['Symbol'].nunique()}"
)

print(
    f"Start date: {df['Date'].min().date()}"
)

print(
    f"End date: {df['Date'].max().date()}"
)

# Stock Summary
print("\nRows per stock:")

stock_summary = (
    df.groupby("Symbol")
      .agg(
          Records=("Date", "count"),
          Start_Date=("Date", "min"),
          End_Date=("Date", "max"),
          Avg_Close=("Close", "mean"),
          Min_Close=("Close", "min"),
          Max_Close=("Close", "max")
      )
      .sort_index()
)

print(stock_summary)

# Save clean data
output_file = (
    PROCESSED_FOLDER
    / "cleaned_stock_data.csv"
)

df.to_csv(
    output_file,
    index=False
)


print("\n" + "=" * 60)
print("PREPROCESSING COMPLETE")
print("=" * 60)

print(
    f"Saved cleaned dataset to:\n{output_file}"
)