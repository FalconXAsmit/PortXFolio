# Data Profile: Cleaned Stock Data (Portfolix)

## 1. Executive Summary
- **Primary Data Asset**: `cleaned_stock_data.csv` (and raw `stock_data.csv`)
- **Total Records**: 83,981 rows
- **Total Symbols**: 20 Top Indian Equities (National Stock Exchange - Nifty 50 constituents)
- **Temporal Coverage**: 2009-09-29 to 2026-09-28 (~17 years of daily trading history)
- **Data Frequency**: Daily trading session records (excluding NSE market holidays and weekends)
- **Price Adjustment**: Auto-adjusted prices (Split-adjusted and dividend-adjusted OHLC via Yahoo Finance API).

---

## 2. Schema Specification & Data Types

| Column Name | Ingested Type | Target SQL Type | Description | Nullable | Validation Rules |
|-------------|---------------|-----------------|-------------|----------|------------------|
| `Date`      | `str` (ISO-8601) | `DATE` / `TIMESTAMP` | Trading calendar date | No | Valid date format `YYYY-MM-DD` |
| `Symbol`    | `str`         | `VARCHAR(20)`   | Ticker symbol (NSE) | No | Uppercase alphanumeric |
| `Open`      | `float64`     | `NUMERIC(14, 4)`| Session opening price (adjusted) | Yes (2 anomalies) | Value > 0 |
| `High`      | `float64`     | `NUMERIC(14, 4)`| Session intraday high (adjusted) | Yes (2 anomalies) | Value >= max(Open, Close) |
| `Low`       | `float64`     | `NUMERIC(14, 4)`| Session intraday low (adjusted)  | Yes (2 anomalies) | Value <= min(Open, Close), Value > 0 |
| `Close`     | `float64`     | `NUMERIC(14, 4)`| Session closing price (adjusted) | Yes (2 anomalies) | Value > 0 |
| `Volume`    | `int64`       | `BIGINT`        | Total trading shares/contracts   | No | Value >= 0 |

---

## 3. Data Quality & Anomaly Analysis

### 3.1 Missing Value Inspection
- **Total Nulls**: Exactly 2 rows exhibit missing price data (`Open`, `High`, `Low`, `Close` are `NaN` with valid `Volume`):
  - `2026-09-28` for `HCLTECH` (Volume: 476,363)
  - `2026-09-28` for `NESTLEIND` (Volume: 181,094)
- **ETL Remediation**: The ETL pipeline rejects/drops incomplete price rows with an audit log entry or imputes forward-fill for end-of-series if configured.

### 3.2 Duplicate Checks
- **Exact Row Duplicates**: 0
- **Composite Key (`Symbol`, `Date`) Duplicates**: 0
- **Uniqueness Guarantee**: The dataset provides strict uniqueness on `(Symbol, Date)`.

### 3.3 Integrity & Sanity Checks
- **OHLC Consistency**: 
  - `High < Open` or `High < Close`: **0 occurrences** (100% valid)
  - `Low > Open` or `Low > Close`: **0 occurrences** (100% valid)
- **Non-positive Prices**: **0 occurrences** for all valid price rows.
- **Negative Volume**: **0 occurrences**.
- **Zero Volume Records**: 258 rows (0.3% of records, typically during market halts, special trading sessions like Muhurat trading with zero volume reported in secondary feeds, or illiquidity on specific off-days).

---

## 4. Symbol Universe & Sector Taxonomy

| Symbol | Company Name | Sector | Industry | Record Count | Price Range (INR) |
|---|---|---|---|---|---|
| **ASIANPAINT** | Asian Paints Ltd | Consumer Discretionary | Paints & Coatings | 4,199 | 119.48 - 3,430.49 |
| **AXISBANK** | Axis Bank Ltd | Financial Services | Banking - Private | 4,199 | 147.71 - 1,401.92 |
| **BAJFINANCE** | Bajaj Finance Ltd | Financial Services | NBFC | 4,199 | 2.02 - 1,158.80 |
| **BHARTIARTL** | Bharti Airtel Ltd | Telecommunications | Telecom Services | 4,199 | 200.63 - 2,135.82 |
| **HCLTECH** | HCL Technologies Ltd | Information Technology | IT Services | 4,200 | 46.82 - 1,853.42 |
| **HDFCBANK** | HDFC Bank Ltd | Financial Services | Banking - Private | 4,199 | 67.75 - 996.42 |
| **HINDUNILVR** | Hindustan Unilever Ltd | Consumer Staples | FMCG | 4,199 | 161.73 - 2,909.86 |
| **ICICIBANK** | ICICI Bank Ltd | Financial Services | Banking - Private | 4,199 | 100.97 - 1,464.85 |
| **INFY** | Infosys Ltd | Information Technology | IT Services | 4,199 | 178.39 - 1,901.08 |
| **ITC** | ITC Ltd | Consumer Staples | Diversified FMCG | 4,199 | 44.27 - 463.95 |
| **KOTAKBANK** | Kotak Mahindra Bank Ltd | Financial Services | Banking - Private | 4,199 | 33.36 - 452.46 |
| **LT** | Larsen & Toubro Ltd | Industrials | Infrastructure / EPC | 4,199 | 351.21 - 4,375.36 |
| **MARUTI** | Maruti Suzuki India Ltd | Consumer Discretionary | Automobile | 4,199 | 809.75 - 17,120.06 |
| **NESTLEIND** | Nestle India Ltd | Consumer Staples | FMCG - Food Products | 4,199 | 102.35 - 1,540.00 |
| **RELIANCE** | Reliance Industries Ltd | Energy & Conglomerate | Oil, Gas & Retail | 4,199 | 139.07 - 1,584.97 |
| **SBIN** | State Bank of India | Financial Services | Banking - PSU | 4,199 | 127.14 - 1,206.06 |
| **SUNPHARMA** | Sun Pharma Industries Ltd | Healthcare | Pharmaceuticals | 4,199 | 117.54 - 2,001.10 |
| **TCS** | Tata Consultancy Services Ltd | Information Technology | IT Services | 4,199 | 192.10 - 4,230.71 |
| **TITAN** | Titan Company Ltd | Consumer Discretionary | Luxury & Jewelry | 4,199 | 56.54 - 5,169.20 |
| **WIPRO** | Wipro Ltd | Information Technology | IT Services | 4,199 | 49.68 - 329.53 |

---

## 5. Architectural Implications for Database & Engines

1. **Storage Precision**:
   - Store prices with `Numeric(14, 4)` and monetary values with `Numeric(18, 4)` to eliminate floating-point arithmetic errors.
   - Volume stored as `BigInteger`.
2. **Indexing Strategy**:
   - Composite unique index on `(symbol_id, date)` or `(symbol, date)`.
   - Clustered / secondary index on `date` for cross-sectional market calculations and multi-asset correlation matrices.
3. **Analytics Window Calculations**:
   - Precompute or dynamically calculate technical indicators using rolling vectorised pandas/numpy windows with caching on date ranges.
4. **Idempotent Ingestion**:
   - Support `UPSERT` / `ON CONFLICT (symbol, date) DO UPDATE` so ingestion scripts can run multiple times safely without generating duplicate records.
