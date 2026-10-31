from typing import List, Dict, Any, Optional
from datetime import date, datetime
import itertools
import json
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.repositories.market_repo import MarketRepository
from backend.app.schemas.backtest import (
    BacktestRequest, BacktestResponse, BacktestTradeRecord,
    EquityPoint, MonthlyReturnMatrix,
    GridOptimizationRequest, GridOptimizationResponse, GridResultItem
)
from backend.app.models.backtest import Backtest, BacktestTrade

class BacktestEngine:
    def __init__(self, db: Session):
        self.db = db
        self.market_repo = MarketRepository(db)

    def run_backtest(self, user_id: int, req: BacktestRequest) -> BacktestResponse:
        ticker = req.symbol.upper()
        symbol = self.market_repo.get_symbol_by_ticker(ticker)
        if not symbol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {ticker} not found")

        prices = self.market_repo.get_price_history(symbol.id, start_date=req.start_date, end_date=req.end_date)
        if len(prices) < 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient price history ({len(prices)} bars) for {ticker} in specified range"
            )

        df = pd.DataFrame([
            {
                "date": p.date,
                "open": float(p.open),
                "high": float(p.high),
                "low": float(p.low),
                "close": float(p.close),
                "volume": int(p.volume)
            }
            for p in prices
        ]).sort_values("date").reset_index(drop=True)

        # Generate signals without look-ahead bias (signals generated on bar i, trade executed on bar i+1 open or bar i close)
        signals = self._generate_signals(df, req.strategy_type, req.parameters)

        # Simulate Event-Driven Execution
        results = self._simulate_execution(
            df=df,
            signals=signals,
            initial_cash=req.initial_cash,
            commission_rate=req.commission_rate,
            slippage_rate=req.slippage_rate,
            symbol_ticker=ticker
        )

        # Persist to database if needed
        backtest_model = Backtest(
            user_id=user_id,
            name=req.name or f"{req.strategy_type} on {ticker}",
            strategy_type=req.strategy_type,
            symbol_or_universe=ticker,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_cash=req.initial_cash,
            final_equity=results["final_equity"],
            total_return_pct=results["total_return_pct"],
            benchmark_return_pct=results["benchmark_return_pct"],
            cagr=results["cagr"],
            sharpe_ratio=results["sharpe_ratio"],
            sortino_ratio=results["sortino_ratio"],
            calmar_ratio=results["calmar_ratio"],
            max_drawdown_pct=results["max_drawdown_pct"],
            win_rate=results["win_rate"],
            profit_factor=results["profit_factor"],
            total_trades=results["total_trades"],
            winning_trades=results["winning_trades"],
            losing_trades=results["losing_trades"],
            parameters_json=json.dumps(req.parameters),
            equity_curve_json=json.dumps([ep.model_dump() for ep in results["equity_curve"]])
        )
        self.db.add(backtest_model)
        self.db.flush()

        for t in results["trades"]:
            bt_trade = BacktestTrade(
                backtest_id=backtest_model.id,
                symbol=t.symbol,
                side=t.side,
                entry_date=t.entry_date,
                exit_date=t.exit_date,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                quantity=t.quantity,
                pnl=t.pnl,
                return_pct=t.return_pct,
                holding_period_days=t.holding_period_days
            )
            self.db.add(bt_trade)

        self.db.commit()
        self.db.refresh(backtest_model)

        return BacktestResponse(
            id=backtest_model.id,
            name=backtest_model.name,
            strategy_type=req.strategy_type,
            symbol=ticker,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_cash=req.initial_cash,
            final_equity=results["final_equity"],
            total_return_pct=results["total_return_pct"],
            benchmark_return_pct=results["benchmark_return_pct"],
            cagr=results["cagr"],
            sharpe_ratio=results["sharpe_ratio"],
            sortino_ratio=results["sortino_ratio"],
            calmar_ratio=results["calmar_ratio"],
            max_drawdown_pct=results["max_drawdown_pct"],
            win_rate=results["win_rate"],
            profit_factor=results["profit_factor"],
            total_trades=results["total_trades"],
            winning_trades=results["winning_trades"],
            losing_trades=results["losing_trades"],
            parameters=req.parameters,
            equity_curve=results["equity_curve"],
            trades=results["trades"],
            monthly_matrix=results["monthly_matrix"]
        )

    def _generate_signals(self, df: pd.DataFrame, strategy: str, params: Dict[str, Any]) -> pd.Series:
        close = df["close"]
        signals = pd.Series(0, index=df.index) # 1 = BUY, -1 = SELL, 0 = HOLD

        strat = strategy.upper()
        if strat == "SMA_CROSS":
            fast_p = int(params.get("fast_period", 20))
            slow_p = int(params.get("slow_period", 50))
            fast_sma = close.rolling(fast_p).mean()
            slow_sma = close.rolling(slow_p).mean()
            
            # Position: 1 when fast > slow, 0 otherwise
            position = (fast_sma > slow_sma).astype(int)
            signals = position.diff().fillna(0) # 1 = cross up, -1 = cross down

        elif strat == "RSI_MEAN_REVERSION":
            rsi_p = int(params.get("rsi_period", 14))
            oversold = float(params.get("oversold_threshold", 30))
            overbought = float(params.get("overbought_threshold", 70))
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(rsi_p).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(rsi_p).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))

            # Buy when dipping below oversold, sell when rising above overbought
            pos = pd.Series(0, index=df.index)
            curr_pos = 0
            for i in range(len(df)):
                r_val = rsi.iloc[i]
                if not pd.isna(r_val):
                    if r_val <= oversold:
                        curr_pos = 1
                    elif r_val >= overbought:
                        curr_pos = 0
                pos.iloc[i] = curr_pos
            signals = pos.diff().fillna(0)

        elif strat == "MACD":
            fast_span = int(params.get("fast_span", 12))
            slow_span = int(params.get("slow_span", 26))
            signal_span = int(params.get("signal_span", 9))
            
            ema_fast = close.ewm(span=fast_span, adjust=False).mean()
            ema_slow = close.ewm(span=slow_span, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            sig_line = macd_line.ewm(span=signal_span, adjust=False).mean()

            position = (macd_line > sig_line).astype(int)
            signals = position.diff().fillna(0)

        elif strat == "MOMENTUM":
            lookback = int(params.get("lookback_period", 20))
            roc = close.pct_change(lookback)
            threshold = float(params.get("roc_threshold_pct", 2.0)) / 100.0

            position = (roc > threshold).astype(int)
            signals = position.diff().fillna(0)

        elif strat == "BOLLINGER_BREAKOUT":
            bb_p = int(params.get("period", 20))
            bb_std_mult = float(params.get("std_dev", 2.0))
            middle = close.rolling(bb_p).mean()
            std = close.rolling(bb_p).std()
            upper = middle + (bb_std_mult * std)
            lower = middle - (bb_std_mult * std)

            pos = pd.Series(0, index=df.index)
            curr = 0
            for i in range(len(df)):
                if not pd.isna(upper.iloc[i]):
                    if close.iloc[i] > upper.iloc[i]:
                        curr = 1
                    elif close.iloc[i] < middle.iloc[i]:
                        curr = 0
                pos.iloc[i] = curr
            signals = pos.diff().fillna(0)

        return signals

    def _simulate_execution(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        initial_cash: float,
        commission_rate: float,
        slippage_rate: float,
        symbol_ticker: str
    ) -> Dict[str, Any]:
        cash = initial_cash
        position_shares = 0.0
        entry_price = 0.0
        entry_date = None

        trades_list: List[BacktestTradeRecord] = []
        equity_curve: List[EquityPoint] = []
        
        benchmark_init_price = df["close"].iloc[0]

        for i in range(len(df)):
            row = df.iloc[i]
            d = row["date"]
            curr_price = row["close"]
            sig = signals.iloc[i]

            # Process Entry (BUY)
            if sig == 1 and position_shares == 0:
                # Apply slippage on buy
                exec_price = curr_price * (1.0 + slippage_rate)
                # Position sizing: use 98% of available cash to account for commissions
                capital_to_use = cash * 0.98
                shares = capital_to_use / exec_price
                comm = (shares * exec_price) * commission_rate
                
                cash -= ((shares * exec_price) + comm)
                position_shares = shares
                entry_price = exec_price
                entry_date = d

            # Process Exit (SELL)
            elif sig == -1 and position_shares > 0:
                exec_price = curr_price * (1.0 - slippage_rate)
                gross_proceeds = position_shares * exec_price
                comm = gross_proceeds * commission_rate
                net_proceeds = gross_proceeds - comm
                
                cost_basis = position_shares * entry_price
                trade_pnl = net_proceeds - cost_basis
                trade_ret = (trade_pnl / cost_basis) * 100.0
                holding_days = (d - entry_date).days if entry_date else 1

                trades_list.append(BacktestTradeRecord(
                    symbol=symbol_ticker,
                    side="LONG",
                    entry_date=entry_date,
                    exit_date=d,
                    entry_price=round(entry_price, 2),
                    exit_price=round(exec_price, 2),
                    quantity=round(position_shares, 2),
                    pnl=round(trade_pnl, 2),
                    return_pct=round(trade_ret, 2),
                    holding_period_days=max(1, holding_days)
                ))

                cash += net_proceeds
                position_shares = 0.0
                entry_price = 0.0
                entry_date = None

            # Mark to Market Portfolio Equity
            holdings_val = position_shares * curr_price
            current_total_equity = cash + holdings_val
            bench_equity = initial_cash * (curr_price / benchmark_init_price)

            equity_curve.append({
                "date": d.isoformat(),
                "equity": current_total_equity,
                "benchmark_equity": bench_equity,
                "cash": cash,
                "holdings_value": holdings_val
            })

        # Convert equity curve to DataFrame for drawdown and risk metrics
        df_eq = pd.DataFrame(equity_curve)
        peak = df_eq["equity"].cummax()
        df_eq["drawdown_pct"] = ((df_eq["equity"] - peak) / peak) * 100.0

        equity_points = [
            EquityPoint(
                date=row["date"],
                equity=round(float(row["equity"]), 2),
                benchmark_equity=round(float(row["benchmark_equity"]), 2),
                drawdown_pct=round(float(row["drawdown_pct"]), 2),
                cash=round(float(row["cash"]), 2),
                holdings_value=round(float(row["holdings_value"]), 2)
            )
            for _, row in df_eq.iterrows()
        ]

        final_equity = df_eq["equity"].iloc[-1]
        total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100.0
        bench_final = df_eq["benchmark_equity"].iloc[-1]
        benchmark_return_pct = ((bench_final - initial_cash) / initial_cash) * 100.0

        # Calculate CAGR
        n_days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        years = max(n_days / 365.25, 0.1)
        cagr = ((final_equity / initial_cash) ** (1.0 / years) - 1.0) * 100.0

        # Daily returns & Sharpe
        daily_returns = df_eq["equity"].pct_change().dropna()
        rf_daily = 0.06 / 252.0
        excess = daily_returns - rf_daily
        ann_vol = daily_returns.std() * np.sqrt(252)
        sharpe = float((excess.mean() / (daily_returns.std() or 1e-6)) * np.sqrt(252))

        downside = daily_returns[daily_returns < 0]
        downside_std = downside.std() * np.sqrt(252) if len(downside) > 0 else 1e-6
        sortino = float((cagr / 100.0 - 0.06) / (downside_std or 1e-6))

        max_dd = float(df_eq["drawdown_pct"].min())
        calmar = float((cagr / 100.0) / abs(max_dd / 100.0 or 1e-6))

        # Trade metrics
        total_trades = len(trades_list)
        win_trades = [t for t in trades_list if t.pnl > 0]
        loss_trades = [t for t in trades_list if t.pnl <= 0]
        win_rate = (len(win_trades) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum([t.pnl for t in win_trades])
        gross_loss = abs(sum([t.pnl for t in loss_trades]))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        # Monthly returns matrix
        df_eq["date_dt"] = pd.to_datetime(df_eq["date"])
        df_eq["year"] = df_eq["date_dt"].dt.year
        df_eq["month"] = df_eq["date_dt"].dt.month
        
        monthly_matrix_list: List[MonthlyReturnMatrix] = []
        for yr, y_group in df_eq.groupby("year"):
            m_returns = {}
            y_start = y_group["equity"].iloc[0]
            y_end = y_group["equity"].iloc[-1]
            y_tot = ((y_end - y_start) / y_start) * 100.0
            
            for mo, m_group in y_group.groupby("month"):
                m_start = m_group["equity"].iloc[0]
                m_end = m_group["equity"].iloc[-1]
                m_returns[mo] = round(((m_end - m_start) / m_start) * 100.0, 2)
            
            monthly_matrix_list.append(MonthlyReturnMatrix(
                year=yr,
                returns=m_returns,
                total_year=round(y_tot, 2)
            ))

        return {
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return_pct, 2),
            "benchmark_return_pct": round(benchmark_return_pct, 2),
            "cagr": round(cagr, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": total_trades,
            "winning_trades": len(win_trades),
            "losing_trades": len(loss_trades),
            "equity_curve": equity_points,
            "trades": trades_list,
            "monthly_matrix": monthly_matrix_list
        }

    def run_grid_optimization(self, req: GridOptimizationRequest) -> GridOptimizationResponse:
        param_names = list(req.parameter_grid.keys())
        param_values = list(req.parameter_grid.values())
        combinations = [dict(zip(param_names, combo)) for combo in itertools.product(*param_values)]

        results: List[GridResultItem] = []
        for p_combo in combinations:
            bt_req = BacktestRequest(
                strategy_type=req.strategy_type,
                symbol=req.symbol,
                start_date=req.start_date,
                end_date=req.end_date,
                initial_cash=req.initial_cash,
                parameters=p_combo
            )
            # Lightweight simulation for grid
            ticker = req.symbol.upper()
            sym = self.market_repo.get_symbol_by_ticker(ticker)
            if not sym:
                continue
            prices = self.market_repo.get_price_history(sym.id, start_date=req.start_date, end_date=req.end_date)
            df = pd.DataFrame([{"date": p.date, "close": float(p.close), "open": float(p.open)} for p in prices]).sort_values("date").reset_index(drop=True)
            signals = self._generate_signals(df, req.strategy_type, p_combo)
            sim_res = self._simulate_execution(df, signals, req.initial_cash, 0.001, 0.0005, ticker)

            results.append(GridResultItem(
                parameters=p_combo,
                total_return_pct=sim_res["total_return_pct"],
                sharpe_ratio=sim_res["sharpe_ratio"],
                max_drawdown_pct=sim_res["max_drawdown_pct"],
                win_rate=sim_res["win_rate"],
                profit_factor=sim_res["profit_factor"],
                total_trades=sim_res["total_trades"]
            ))

        best_by_sharpe = max(results, key=lambda r: r.sharpe_ratio).parameters if results else {}
        best_by_return = max(results, key=lambda r: r.total_return_pct).parameters if results else {}

        return GridOptimizationResponse(
            strategy_type=req.strategy_type,
            symbol=req.symbol.upper(),
            total_combinations=len(combinations),
            results=results,
            best_parameters_by_sharpe=best_by_sharpe,
            best_parameters_by_return=best_by_return
        )
