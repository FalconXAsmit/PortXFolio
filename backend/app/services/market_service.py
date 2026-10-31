from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
from decimal import Decimal

from backend.app.repositories.market_repo import MarketRepository
from backend.app.schemas.market import (
    SymbolResponse, SymbolDetailResponse, PriceRecord,
    IndicatorsResponse, MarketStatsResponse, CorrelationMatrixResponse
)

class MarketService:
    def __init__(self, db: Session):
        self.db = db
        self.market_repo = MarketRepository(db)

    def list_symbols(
        self,
        sector: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SymbolResponse]:
        symbols = self.market_repo.list_symbols(sector=sector, search=search, skip=skip, limit=limit)
        results = []
        for s in symbols:
            summary = self.market_repo.get_symbol_summary(s.id)
            results.append(SymbolResponse(
                id=s.id,
                ticker=s.ticker,
                name=s.name,
                sector=s.sector,
                industry=s.industry,
                exchange=s.exchange,
                currency=s.currency,
                is_active=s.is_active,
                latest_price=summary.get("latest_price"),
                change_pct_1d=summary.get("change_pct_1d"),
                volume_1d=summary.get("volume_1d")
            ))
        return results

    def get_symbol_detail(self, ticker: str) -> Optional[SymbolDetailResponse]:
        symbol = self.market_repo.get_symbol_by_ticker(ticker)
        if not symbol:
            return None
        summary = self.market_repo.get_symbol_summary(symbol.id)
        return SymbolDetailResponse(
            id=symbol.id,
            ticker=symbol.ticker,
            name=symbol.name,
            sector=symbol.sector,
            industry=symbol.industry,
            exchange=symbol.exchange,
            currency=symbol.currency,
            is_active=symbol.is_active,
            latest_price=summary.get("latest_price"),
            change_pct_1d=summary.get("change_pct_1d"),
            volume_1d=summary.get("volume_1d"),
            first_date=summary.get("first_date"),
            last_date=summary.get("last_date"),
            total_records=summary.get("total_records"),
            min_price_all_time=summary.get("min_price_all_time"),
            max_price_all_time=summary.get("max_price_all_time")
        )

    def get_price_history(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        symbol = self.market_repo.get_symbol_by_ticker(ticker)
        if not symbol:
            return []
        prices = self.market_repo.get_price_history(symbol.id, start_date=start_date, end_date=end_date, limit=limit)
        return [
            {
                "date": p.date.isoformat(),
                "open": float(p.open),
                "high": float(p.high),
                "low": float(p.low),
                "close": float(p.close),
                "volume": int(p.volume)
            }
            for p in prices
        ]

    def calculate_technical_indicators(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> IndicatorsResponse:
        prices_data = self.get_price_history(ticker, start_date=start_date, end_date=end_date)
        if not prices_data or len(prices_data) < 20:
            return IndicatorsResponse(symbol=ticker, timeframe="1D", indicators={})

        df = pd.DataFrame(prices_data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # 1. Simple Moving Averages (SMA 20, 50, 200)
        sma20 = close.rolling(window=20).mean()
        sma50 = close.rolling(window=50).mean()
        sma200 = close.rolling(window=200).mean()

        # 2. Exponential Moving Averages (EMA 12, 26)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()

        # 3. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # 4. MACD (12, 26, 9)
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        # 5. Bollinger Bands (20, 2)
        bb_middle = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_middle + (2 * bb_std)
        bb_lower = bb_middle - (2 * bb_std)

        # 6. ATR (Average True Range 14)
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()

        # 7. Stochastic Oscillator (%K, %D 14, 3)
        low14 = low.rolling(window=14).min()
        high14 = high.rolling(window=14).max()
        stoch_k = 100 * ((close - low14) / (high14 - low14).replace(0, np.nan))
        stoch_d = stoch_k.rolling(window=3).mean()

        # 8. VWAP (Volume Weighted Average Price)
        typical_price = (high + low + close) / 3
        cum_vp = (typical_price * volume).cumsum()
        cum_vol = volume.cumsum().replace(0, np.nan)
        vwap = cum_vp / cum_vol

        # 9. OBV (On-Balance Volume)
        obv = np.where(close > close.shift(1), volume, np.where(close < close.shift(1), -volume, 0)).cumsum()

        # Structure outputs
        indicators_map = {
            "sma": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "sma20": None if pd.isna(s20) else round(float(s20), 2),
                    "sma50": None if pd.isna(s50) else round(float(s50), 2),
                    "sma200": None if pd.isna(s200) else round(float(s200), 2)
                }
                for d, s20, s50, s200 in zip(df["date"], sma20, sma50, sma200)
            ],
            "ema": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "ema12": None if pd.isna(e12) else round(float(e12), 2),
                    "ema26": None if pd.isna(e26) else round(float(e26), 2)
                }
                for d, e12, e26 in zip(df["date"], ema12, ema26)
            ],
            "rsi": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "value": None if pd.isna(r) else round(float(r), 2)
                }
                for d, r in zip(df["date"], rsi)
            ],
            "macd": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "macd": None if pd.isna(m) else round(float(m), 2),
                    "signal": None if pd.isna(s) else round(float(s), 2),
                    "hist": None if pd.isna(h) else round(float(h), 2)
                }
                for d, m, s, h in zip(df["date"], macd_line, signal_line, macd_hist)
            ],
            "bollinger": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "upper": None if pd.isna(u) else round(float(u), 2),
                    "middle": None if pd.isna(m) else round(float(m), 2),
                    "lower": None if pd.isna(l) else round(float(l), 2)
                }
                for d, u, m, l in zip(df["date"], bb_upper, bb_middle, bb_lower)
            ],
            "atr": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "value": None if pd.isna(a) else round(float(a), 2)
                }
                for d, a in zip(df["date"], atr)
            ],
            "stochastic": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "k": None if pd.isna(k) else round(float(k), 2),
                    "d": None if pd.isna(d_val) else round(float(d_val), 2)
                }
                for d, k, d_val in zip(df["date"], stoch_k, stoch_d)
            ],
            "vwap": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "value": None if pd.isna(v) else round(float(v), 2)
                }
                for d, v in zip(df["date"], vwap)
            ],
            "obv": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "value": None if pd.isna(o) else round(float(o), 2)
                }
                for d, o in zip(df["date"], obv)
            ]
        }

        return IndicatorsResponse(
            symbol=ticker,
            timeframe="1D",
            indicators=indicators_map
        )

    def calculate_market_stats(self, ticker: str, risk_free_rate: float = 0.06) -> Optional[MarketStatsResponse]:
        symbol = self.market_repo.get_symbol_by_ticker(ticker)
        if not symbol:
            return None
        prices = self.market_repo.get_price_history(symbol.id)
        if len(prices) < 30:
            return None

        closes = pd.Series([float(p.close) for p in prices])
        daily_returns = closes.pct_change().dropna()

        mean_ret = float(daily_returns.mean())
        ann_return = float((1 + mean_ret) ** 252 - 1)
        ann_vol = float(daily_returns.std() * np.sqrt(252))

        # Max drawdown
        cum_ret = (1 + daily_returns).cumprod()
        peak = cum_ret.cummax()
        drawdown = (cum_ret - peak) / peak
        max_dd = float(drawdown.min())

        # Sharpe & Sortino
        rf_daily = risk_free_rate / 252.0
        excess_daily = daily_returns - rf_daily
        sharpe = float((excess_daily.mean() / (daily_returns.std() or 1e-6)) * np.sqrt(252))

        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 1e-6
        sortino = float((ann_return - risk_free_rate) / (downside_std or 1e-6))

        # Beta vs market benchmark (equal weight of all symbols)
        # Compute equal weighted index returns
        all_symbols = self.market_repo.list_symbols(limit=20)
        all_tickers = [s.ticker for s in all_symbols]
        all_prices = self.market_repo.get_price_history_for_tickers(all_tickers)
        
        df_all = pd.DataFrame([
            {"date": p.date, "symbol": p.symbol.ticker, "close": float(p.close)}
            for p in all_prices
        ])
        pivot = df_all.pivot(index="date", columns="symbol", values="close")
        benchmark_returns = pivot.pct_change().mean(axis=1).dropna()

        # Align series
        aligned = pd.concat([daily_returns.rename("asset"), benchmark_returns.rename("bench")], axis=1).dropna()
        if len(aligned) > 20 and aligned["bench"].var() > 0:
            cov = np.cov(aligned["asset"], aligned["bench"])[0][1]
            var_b = np.var(aligned["bench"])
            beta = float(cov / var_b)
        else:
            beta = 1.0

        skew = float(daily_returns.skew())
        kurt = float(daily_returns.kurtosis())

        # Current indicators
        sma50_val = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else None
        sma200_val = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else None

        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None

        return MarketStatsResponse(
            symbol=ticker,
            mean_daily_return=mean_ret,
            annualized_return=ann_return,
            annualized_volatility=ann_vol,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            beta_vs_benchmark=beta,
            skewness=skew,
            kurtosis=kurt,
            current_rsi_14=current_rsi,
            current_sma_50=sma50_val,
            current_sma_200=sma200_val
        )

    def get_correlation_matrix(self, tickers: Optional[List[str]] = None) -> CorrelationMatrixResponse:
        if not tickers:
            symbols = self.market_repo.list_symbols(limit=20)
            tickers = [s.ticker for s in symbols]

        prices = self.market_repo.get_price_history_for_tickers(tickers)
        if not prices:
            return CorrelationMatrixResponse(symbols=tickers, matrix=[], start_date="", end_date="")

        df = pd.DataFrame([
            {"date": p.date, "symbol": p.symbol.ticker, "close": float(p.close)}
            for p in prices
        ])
        pivot = df.pivot(index="date", columns="symbol", values="close")
        returns = pivot.pct_change().dropna()

        corr = returns.corr().fillna(0)
        ordered_symbols = [t for t in tickers if t in corr.columns]
        matrix = [[round(float(corr.loc[r, c]), 4) for c in ordered_symbols] for r in ordered_symbols]

        start_d = str(pivot.index.min()) if not pivot.empty else ""
        end_d = str(pivot.index.max()) if not pivot.empty else ""

        return CorrelationMatrixResponse(
            symbols=ordered_symbols,
            matrix=matrix,
            start_date=start_d,
            end_date=end_d
        )
