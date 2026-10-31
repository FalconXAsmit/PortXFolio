import io
import csv
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.services.portfolio_service import PortfolioService
from backend.app.models.order import Trade
from backend.app.models.portfolio import Portfolio, Transaction

class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)

    def export_portfolio_csv(self, user_id: int, portfolio_id: int) -> StreamingResponse:
        details = self.portfolio_service.get_portfolio_details(user_id, portfolio_id)
        
        output = io.StringIO()
        writer = csv.writer(output)

        # Portfolio Summary Header
        writer.writerow(["PORTFOLIX PORTFOLIO REPORT"])
        writer.writerow(["Portfolio Name", details.name])
        writer.writerow(["Currency", details.currency])
        writer.writerow(["Total Equity", f"{details.total_equity:,.2f}"])
        writer.writerow(["Cash Balance", f"{details.cash_balance:,.2f}"])
        writer.writerow(["Holdings Value", f"{details.holdings_value:,.2f}"])
        writer.writerow(["Total P&L", f"{details.total_pnl:,.2f} ({details.total_pnl_pct:.2f}%)"])
        writer.writerow(["Realized P&L", f"{details.realized_pnl:,.2f}"])
        writer.writerow(["Unrealized P&L", f"{details.unrealized_pnl:,.2f}"])
        writer.writerow([])

        # Holdings Table
        writer.writerow(["HOLDINGS BREAKDOWN"])
        writer.writerow(["Ticker", "Name", "Sector", "Quantity", "Avg Buy Price", "Current Price", "Market Value", "Total Invested", "Unrealized PnL", "Unrealized PnL %", "Weight %"])
        for h in details.holdings:
            writer.writerow([
                h.ticker,
                h.name,
                h.sector or "N/A",
                f"{h.quantity:.2f}",
                f"{h.average_buy_price:.2f}",
                f"{h.current_price:.2f}",
                f"{h.market_value:.2f}",
                f"{h.total_invested:.2f}",
                f"{h.unrealized_pnl:.2f}",
                f"{h.unrealized_pnl_pct:.2f}%",
                f"{h.weight_pct:.2f}%"
            ])
        writer.writerow([])

        # Trade History Table
        writer.writerow(["TRADE HISTORY"])
        trades = self.db.query(Trade).filter(Trade.portfolio_id == portfolio_id).order_by(Trade.executed_at.desc()).all()
        writer.writerow(["Date", "Ticker", "Side", "Quantity", "Price", "Commission", "Slippage", "Realized PnL"])
        for t in trades:
            writer.writerow([
                t.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                t.symbol.ticker,
                t.side,
                f"{t.quantity:.2f}",
                f"{t.execution_price:.2f}",
                f"{t.commission:.2f}",
                f"{t.slippage:.2f}",
                f"{t.realized_pnl:.2f}"
            ])

        output.seek(0)
        filename = f"portfolix_report_{details.name.lower().replace(' ', '_')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    def export_trades_csv(self, user_id: int) -> StreamingResponse:
        trades = self.db.query(Trade)\
            .join(Portfolio)\
            .filter(Portfolio.user_id == user_id)\
            .order_by(Trade.executed_at.desc())\
            .all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Trade ID", "Date", "Portfolio", "Ticker", "Side", "Quantity", "Execution Price", "Commission", "Slippage", "Realized PnL"])

        for t in trades:
            writer.writerow([
                t.id,
                t.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                t.portfolio.name,
                t.symbol.ticker,
                t.side,
                f"{t.quantity:.2f}",
                f"{t.execution_price:.2f}",
                f"{t.commission:.2f}",
                f"{t.slippage:.2f}",
                f"{t.realized_pnl:.2f}"
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=portfolix_trades_ledger.csv"}
        )
