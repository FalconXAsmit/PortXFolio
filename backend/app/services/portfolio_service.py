from typing import List, Dict, Any, Optional
from datetime import datetime, date, timezone
from decimal import Decimal
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from fastapi import HTTPException, status

from backend.app.models.portfolio import Portfolio, Holding, Transaction, TransactionType
from backend.app.models.order import Order, Trade, OrderSide
from backend.app.models.market import Symbol, Price
from backend.app.schemas.portfolio import (
    PortfolioCreate, PortfolioResponse, HoldingResponse, TransactionResponse,
    PortfolioPerformanceResponse, PerformancePoint, MonthlyReturnItem, RiskMetricsResponse,
    OptimizationRequest, OptimizationResponse, EfficientFrontierPoint,
    RebalanceRequest, RebalanceResponse, RebalanceAction
)
from backend.app.repositories.portfolio_repo import PortfolioRepository
from backend.app.repositories.market_repo import MarketRepository

class PortfolioService:
    def __init__(self, db: Session):
        self.db = db
        self.portfolio_repo = PortfolioRepository(db)
        self.market_repo = MarketRepository(db)

    def create_portfolio(self, user_id: int, portfolio_in: PortfolioCreate) -> PortfolioResponse:
        portfolio = self.portfolio_repo.create(user_id, portfolio_in)
        return self.get_portfolio_details(user_id, portfolio.id)

    def list_user_portfolios(self, user_id: int) -> List[PortfolioResponse]:
        portfolios = self.portfolio_repo.list_by_user_id(user_id)
        return [self.get_portfolio_details(user_id, p.id) for p in portfolios]

    def get_portfolio_details(self, user_id: int, portfolio_id: int) -> PortfolioResponse:
        portfolio = self.portfolio_repo.get_by_id(portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        holdings = self.portfolio_repo.list_holdings(portfolio.id)
        holdings_responses = []
        total_holdings_value = Decimal("0.0")
        total_unrealized_pnl = Decimal("0.0")

        # First pass to compute holding valuations
        holdings_data = []
        for h in holdings:
            latest_price_obj = self.market_repo.get_latest_price(h.symbol_id)
            current_price = latest_price_obj.close if latest_price_obj else h.average_buy_price
            market_val = h.quantity * current_price
            unrealized_pnl = market_val - h.total_invested
            unrealized_pct = float((unrealized_pnl / h.total_invested) * 100) if h.total_invested > 0 else 0.0

            total_holdings_value += market_val
            total_unrealized_pnl += unrealized_pnl

            holdings_data.append({
                "holding": h,
                "current_price": current_price,
                "market_val": market_val,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pct": unrealized_pct
            })

        total_equity = portfolio.cash_balance + total_holdings_value

        # Calculate portfolio weights
        for item in holdings_data:
            h = item["holding"]
            weight = float((item["market_val"] / total_equity) * 100) if total_equity > 0 else 0.0
            holdings_responses.append(HoldingResponse(
                id=h.id,
                symbol_id=h.symbol_id,
                ticker=h.symbol.ticker,
                name=h.symbol.name,
                sector=h.symbol.sector,
                quantity=h.quantity,
                average_buy_price=h.average_buy_price,
                current_price=item["current_price"],
                market_value=item["market_val"],
                total_invested=h.total_invested,
                unrealized_pnl=item["unrealized_pnl"],
                unrealized_pnl_pct=item["unrealized_pct"],
                weight_pct=round(weight, 2)
            ))

        # Realized P&L from trades
        trades = self.db.query(Trade).filter(Trade.portfolio_id == portfolio.id).all()
        realized_pnl = sum([t.realized_pnl for t in trades], Decimal("0.0"))

        total_pnl = (total_equity - portfolio.initial_cash)
        total_pnl_pct = float((total_pnl / portfolio.initial_cash) * 100) if portfolio.initial_cash > 0 else 0.0

        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            description=portfolio.description,
            initial_cash=portfolio.initial_cash,
            cash_balance=portfolio.cash_balance,
            holdings_value=total_holdings_value,
            total_equity=total_equity,
            total_pnl=total_pnl,
            total_pnl_pct=round(total_pnl_pct, 2),
            realized_pnl=realized_pnl,
            unrealized_pnl=total_unrealized_pnl,
            currency=portfolio.currency,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            holdings=holdings_responses
        )

    def deposit_or_withdraw(self, user_id: int, portfolio_id: int, amount: Decimal, is_deposit: bool, notes: Optional[str] = None) -> PortfolioResponse:
        portfolio = self.portfolio_repo.get_by_id(portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        if not is_deposit and portfolio.cash_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient cash for withdrawal. Available: ₹{portfolio.cash_balance:,.2f}"
            )

        delta = amount if is_deposit else -amount
        portfolio.cash_balance += delta

        tx_type = TransactionType.DEPOSIT.value if is_deposit else TransactionType.WITHDRAWAL.value
        self.portfolio_repo.add_transaction(
            portfolio_id=portfolio.id,
            tx_type=tx_type,
            amount=delta,
            balance_after=portfolio.cash_balance,
            notes=notes or ("Cash deposit" if is_deposit else "Cash withdrawal")
        )
        self.db.commit()
        return self.get_portfolio_details(user_id, portfolio.id)

    def get_portfolio_performance(self, user_id: int, portfolio_id: int, risk_free_rate: float = 0.06) -> PortfolioPerformanceResponse:
        portfolio = self.portfolio_repo.get_by_id(portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        holdings = self.portfolio_repo.list_holdings(portfolio.id)
        if not holdings:
            # If empty holdings, baseline flat curve
            today_str = date.today().isoformat()
            eq_pts = [PerformancePoint(
                date=today_str,
                portfolio_equity=float(portfolio.cash_balance),
                benchmark_equity=float(portfolio.initial_cash),
                portfolio_return_pct=0.0,
                benchmark_return_pct=0.0
            )]
            empty_risk = RiskMetricsResponse(
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0, max_drawdown=0.0,
                annualized_return=0.0, annualized_volatility=0.0, var_95_parametric=0.0,
                var_95_historical=0.0, cvar_95_historical=0.0, beta=1.0, alpha=0.0, r_squared=0.0
            )
            return PortfolioPerformanceResponse(
                portfolio_id=portfolio.id,
                start_date=today_str,
                end_date=today_str,
                equity_curve=eq_pts,
                monthly_returns=[],
                risk_metrics=empty_risk
            )

        # Build daily price history for holdings
        holding_tickers = [h.symbol.ticker for h in holdings]
        prices = self.market_repo.get_price_history_for_tickers(holding_tickers)
        df_p = pd.DataFrame([
            {"date": p.date, "symbol": p.symbol.ticker, "close": float(p.close)}
            for p in prices
        ])
        pivot = df_p.pivot(index="date", columns="symbol", values="close").ffill().dropna()

        # Build equal-weighted benchmark from universe
        all_syms = self.market_repo.list_symbols(limit=20)
        all_tickers = [s.ticker for s in all_syms]
        bench_prices = self.market_repo.get_price_history_for_tickers(all_tickers)
        df_b = pd.DataFrame([
            {"date": p.date, "symbol": p.symbol.ticker, "close": float(p.close)}
            for p in bench_prices
        ])
        pivot_bench = df_b.pivot(index="date", columns="symbol", values="close").ffill().dropna()
        bench_daily_ret = pivot_bench.pct_change().mean(axis=1).dropna()

        # Weight current holdings by quantity * price on each date + cash
        holding_qty_map = {h.symbol.ticker: float(h.quantity) for h in holdings}
        cash_val = float(portfolio.cash_balance)
        
        daily_equity_series = []
        for d, row in pivot.iterrows():
            eq = cash_val
            for ticker, qty in holding_qty_map.items():
                if ticker in row:
                    eq += qty * row[ticker]
            daily_equity_series.append({"date": d, "equity": eq})

        df_equity = pd.DataFrame(daily_equity_series).set_index("date")
        port_daily_ret = df_equity["equity"].pct_change().dropna()

        # Align with benchmark
        aligned = pd.concat([port_daily_ret.rename("port"), bench_daily_ret.rename("bench")], axis=1).dropna()
        
        # Performance curve points (sample up to 200 points for frontend rendering)
        init_port_eq = df_equity["equity"].iloc[0] if not df_equity.empty else float(portfolio.initial_cash)
        init_bench_val = 100.0
        
        bench_cum = (1 + aligned["bench"]).cumprod()
        bench_eq_series = init_port_eq * bench_cum

        step = max(1, len(df_equity) // 200)
        sampled_df = df_equity.iloc[::step]
        
        equity_points = []
        for d_idx, row in sampled_df.iterrows():
            d_str = d_idx.isoformat()
            eq_val = float(row["equity"])
            b_val = float(bench_eq_series.loc[d_idx]) if d_idx in bench_eq_series else eq_val
            port_ret = float(((eq_val - init_port_eq) / init_port_eq) * 100)
            bench_ret = float(((b_val - init_port_eq) / init_port_eq) * 100)
            equity_points.append(PerformancePoint(
                date=d_str,
                portfolio_equity=round(eq_val, 2),
                benchmark_equity=round(b_val, 2),
                portfolio_return_pct=round(port_ret, 2),
                benchmark_return_pct=round(bench_ret, 2)
            ))

        # Monthly returns matrix
        df_equity["year"] = pd.to_datetime(df_equity.index).year
        df_equity["month"] = pd.to_datetime(df_equity.index).month
        monthly_items = []
        for (yr, mo), group in df_equity.groupby(["year", "month"]):
            if len(group) > 1:
                start_eq = group["equity"].iloc[0]
                end_eq = group["equity"].iloc[-1]
                m_ret = float(((end_eq - start_eq) / start_eq) * 100)
                monthly_items.append(MonthlyReturnItem(year=yr, month=mo, return_pct=round(m_ret, 2)))

        # Risk Metrics
        returns = aligned["port"]
        bench_ret_series = aligned["bench"]
        n_days = len(returns)
        if n_days > 10:
            ann_ret = float(returns.mean() * 252)
            ann_vol = float(returns.std() * np.sqrt(252))
            rf_daily = risk_free_rate / 252.0
            excess = returns - rf_daily
            sharpe = float((excess.mean() / (returns.std() or 1e-6)) * np.sqrt(252))

            downside = returns[returns < 0]
            downside_vol = float(downside.std() * np.sqrt(252)) if len(downside) > 0 else 1e-6
            sortino = float((ann_ret - risk_free_rate) / (downside_vol or 1e-6))

            # Max drawdown
            cum = (1 + returns).cumprod()
            peak = cum.cummax()
            dd = (cum - peak) / peak
            max_dd = float(dd.min())
            calmar = float(ann_ret / abs(max_dd or 1e-6))

            # VaR & CVaR (95%)
            var_param_95 = float(1.645 * (ann_vol / np.sqrt(252)))
            var_hist_95 = float(-np.percentile(returns, 5))
            cvar_hist_95 = float(-returns[returns <= -var_hist_95].mean()) if len(returns[returns <= -var_hist_95]) > 0 else var_hist_95

            # Beta & Alpha
            cov_mat = np.cov(returns, bench_ret_series)
            cov = cov_mat[0][1]
            var_b = np.var(bench_ret_series)
            beta = float(cov / (var_b or 1e-6))
            alpha = float(ann_ret - (risk_free_rate + beta * (bench_ret_series.mean() * 252 - risk_free_rate)))

            corr = np.corrcoef(returns, bench_ret_series)[0][1]
            r_sq = float(corr ** 2) if not np.isnan(corr) else 0.0
        else:
            ann_ret, ann_vol, sharpe, sortino, calmar, max_dd = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            var_param_95, var_hist_95, cvar_hist_95, beta, alpha, r_sq = 0.0, 0.0, 0.0, 1.0, 0.0, 0.0

        risk_metrics = RiskMetricsResponse(
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            max_drawdown=round(max_dd * 100, 2),
            annualized_return=round(ann_ret * 100, 2),
            annualized_volatility=round(ann_vol * 100, 2),
            var_95_parametric=round(var_param_95 * 100, 2),
            var_95_historical=round(var_hist_95 * 100, 2),
            cvar_95_historical=round(cvar_hist_95 * 100, 2),
            beta=round(beta, 2),
            alpha=round(alpha * 100, 2),
            r_squared=round(r_sq, 2)
        )

        return PortfolioPerformanceResponse(
            portfolio_id=portfolio.id,
            start_date=str(pivot.index.min()),
            end_date=str(pivot.index.max()),
            equity_curve=equity_points,
            monthly_returns=monthly_items,
            risk_metrics=risk_metrics
        )

    def optimize_portfolio(self, req: OptimizationRequest) -> OptimizationResponse:
        symbols = [s.upper() for s in req.symbols]
        if len(symbols) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 2 symbols required for optimization")

        prices = self.market_repo.get_price_history_for_tickers(symbols)
        if not prices:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No price history found for requested symbols")

        df = pd.DataFrame([
            {"date": p.date, "symbol": p.symbol.ticker, "close": float(p.close)}
            for p in prices
        ])
        pivot = df.pivot(index="date", columns="symbol", values="close").ffill().dropna()
        daily_returns = pivot.pct_change().dropna()

        mean_returns = daily_returns.mean() * 252
        cov_matrix = daily_returns.cov() * 252
        num_assets = len(symbols)
        rf = req.risk_free_rate

        def portfolio_performance(weights):
            ret = np.sum(mean_returns * weights)
            vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return ret, vol

        def neg_sharpe(weights):
            p_ret, p_vol = portfolio_performance(weights)
            return -(p_ret - rf) / (p_vol or 1e-6)

        def port_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))

        # Constraints & bounds: weights sum to 1, long-only (0 to 1)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))
        init_weights = num_assets * [1.0 / num_assets]

        # 1. Max Sharpe Portfolio
        opt_sharpe = minimize(neg_sharpe, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        max_sharpe_weights = dict(zip(symbols, [round(float(w), 4) for w in opt_sharpe.x]))
        ms_ret, ms_vol = portfolio_performance(opt_sharpe.x)
        max_sharpe_result = {
            "weights": max_sharpe_weights,
            "expected_return": round(float(ms_ret), 4),
            "volatility": round(float(ms_vol), 4),
            "sharpe_ratio": round(float((ms_ret - rf) / (ms_vol or 1e-6)), 4)
        }

        # 2. Min Variance Portfolio
        opt_var = minimize(port_variance, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        min_var_weights = dict(zip(symbols, [round(float(w), 4) for w in opt_var.x]))
        mv_ret, mv_vol = portfolio_performance(opt_var.x)
        min_var_result = {
            "weights": min_var_weights,
            "expected_return": round(float(mv_ret), 4),
            "volatility": round(float(mv_vol), 4),
            "sharpe_ratio": round(float((mv_ret - rf) / (mv_vol or 1e-6)), 4)
        }

        # 3. Risk Parity (Equal Risk Contribution)
        def risk_parity_objective(weights):
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / (port_vol or 1e-6)
            risk_contrib = weights * marginal_contrib
            target_risk = port_vol / num_assets
            return np.sum((risk_contrib - target_risk) ** 2)

        opt_rp = minimize(risk_parity_objective, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        rp_weights = dict(zip(symbols, [round(float(w), 4) for w in opt_rp.x]))
        rp_ret, rp_vol = portfolio_performance(opt_rp.x)
        risk_parity_result = {
            "weights": rp_weights,
            "expected_return": round(float(rp_ret), 4),
            "volatility": round(float(rp_vol), 4),
            "sharpe_ratio": round(float((rp_ret - rf) / (rp_vol or 1e-6)), 4)
        }

        # 4. Generate Efficient Frontier Curve Points
        frontier_points = []
        target_returns = np.linspace(mv_ret * 0.8, max(mean_returns.max() * 0.95, ms_ret * 1.1), 30)
        for t_ret in target_returns:
            target_constraint = (
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: np.sum(mean_returns * x) - t_ret}
            )
            res = minimize(port_variance, init_weights, method='SLSQP', bounds=bounds, constraints=target_constraint)
            if res.success:
                f_ret, f_vol = portfolio_performance(res.x)
                f_sharpe = (f_ret - rf) / (f_vol or 1e-6)
                frontier_points.append(EfficientFrontierPoint(
                    volatility=round(float(f_vol), 4),
                    expected_return=round(float(f_ret), 4),
                    sharpe=round(float(f_sharpe), 4),
                    weights={s: round(float(w), 4) for s, w in zip(symbols, res.x)}
                ))

        return OptimizationResponse(
            max_sharpe=max_sharpe_result,
            min_variance=min_var_result,
            risk_parity=risk_parity_result,
            frontier_curve=frontier_points
        )

    def calculate_rebalance_plan(self, user_id: int, portfolio_id: int, req: RebalanceRequest) -> RebalanceResponse:
        portfolio = self.portfolio_repo.get_by_id(portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        # Verify weights sum to <= 100%
        total_target_pct = sum([t.target_weight_pct for t in req.targets])
        if total_target_pct > 100.001:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target weights exceed 100% (Sum: {total_target_pct:.2f}%)"
            )

        details = self.get_portfolio_details(user_id, portfolio_id)
        total_equity = details.total_equity

        # Map current holdings
        current_holdings = {h.ticker: h for h in details.holdings}
        target_map = {t.symbol.upper(): t.target_weight_pct for t in req.targets}

        # Union of current symbols and target symbols
        all_symbols = set(current_holdings.keys()).union(set(target_map.keys()))

        actions = []
        total_buys = Decimal("0.0")
        total_sells = Decimal("0.0")

        for sym in sorted(all_symbols):
            sym_obj = self.market_repo.get_symbol_by_ticker(sym)
            if not sym_obj:
                continue

            latest_price = self.market_repo.get_latest_price(sym_obj.id)
            current_price = latest_price.close if latest_price else Decimal("100.0")

            curr_h = current_holdings.get(sym)
            curr_qty = curr_h.quantity if curr_h else Decimal("0.0")
            curr_val = curr_qty * current_price
            curr_wt = float((curr_val / total_equity) * 100) if total_equity > 0 else 0.0

            target_wt = target_map.get(sym, 0.0)
            target_val = total_equity * Decimal(str(target_wt / 100.0))
            target_qty = (target_val / current_price).quantize(Decimal("1")) # Whole shares

            qty_delta = target_qty - curr_qty
            est_cost = abs(qty_delta * current_price)

            if qty_delta > 0:
                action_str = "BUY"
                total_buys += est_cost
            elif qty_delta < 0:
                action_str = "SELL"
                total_sells += est_cost
            else:
                action_str = "HOLD"

            actions.append(RebalanceAction(
                symbol=sym,
                action=action_str,
                current_quantity=curr_qty,
                target_quantity=target_qty,
                quantity_delta=qty_delta,
                current_price=current_price,
                estimated_cost=est_cost,
                current_weight_pct=round(curr_wt, 2),
                target_weight_pct=round(target_wt, 2)
            ))

        return RebalanceResponse(
            portfolio_id=portfolio.id,
            total_equity=total_equity,
            available_cash=portfolio.cash_balance,
            actions=actions,
            total_buy_value=total_buys,
            total_sell_value=total_sells
        )
