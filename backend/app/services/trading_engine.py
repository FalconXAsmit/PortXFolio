from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status

from backend.app.models.order import Order, Trade, OrderType, OrderSide, OrderStatus, TimeInForce
from backend.app.models.portfolio import Portfolio, Holding, Transaction, TransactionType
from backend.app.models.market import Symbol, Price
from backend.app.models.audit import AuditLog
from backend.app.schemas.order import OrderCreate, OrderPreviewRequest, OrderPreviewResponse
from backend.app.core.config import settings

class TradingEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_market_price(self, symbol_id: int) -> Decimal:
        latest = self.db.query(Price)\
            .filter(Price.symbol_id == symbol_id)\
            .order_by(desc(Price.date))\
            .first()
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No market price available for symbol id {symbol_id}"
            )
        return latest.close

    def preview_order(self, user_id: int, request: OrderPreviewRequest) -> OrderPreviewResponse:
        portfolio = self.db.query(Portfolio)\
            .filter(Portfolio.id == request.portfolio_id, Portfolio.user_id == user_id)\
            .first()
        if not portfolio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        symbol = self.db.query(Symbol).filter(Symbol.ticker == request.symbol.upper()).first()
        if not symbol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {request.symbol} not found")

        current_price = self.get_latest_market_price(symbol.id)
        exec_price = request.price if (request.order_type == OrderType.LIMIT.value and request.price) else current_price
        
        commission_rate = Decimal(str(settings.DEFAULT_COMMISSION_RATE))
        slippage_rate = Decimal(str(settings.DEFAULT_SLIPPAGE_RATE))

        gross_amount = request.quantity * exec_price
        commission = gross_amount * commission_rate
        slippage = gross_amount * slippage_rate

        side = request.side.upper()
        can_execute = True
        rejection_reason = None
        cash_before = portfolio.cash_balance

        if side == OrderSide.BUY.value:
            # Slippage increases buy cost
            effective_price = exec_price * (Decimal("1.0") + slippage_rate)
            total_required = (request.quantity * effective_price) + commission
            cash_after = cash_before - total_required
            if cash_after < Decimal("0.0"):
                can_execute = False
                rejection_reason = f"Insufficient funds: Required ₹{total_required:,.2f}, Available ₹{cash_before:,.2f}"
        else: # SELL
            effective_price = exec_price * (Decimal("1.0") - slippage_rate)
            total_proceeds = (request.quantity * effective_price) - commission
            cash_after = cash_before + total_proceeds
            holding = self.db.query(Holding)\
                .filter(Holding.portfolio_id == portfolio.id, Holding.symbol_id == symbol.id)\
                .first()
            current_qty = holding.quantity if holding else Decimal("0.0")
            if current_qty < request.quantity:
                can_execute = False
                rejection_reason = f"Insufficient shares: Required {request.quantity}, Available {current_qty}"

        return OrderPreviewResponse(
            symbol=symbol.ticker,
            side=side,
            quantity=request.quantity,
            estimated_price=exec_price,
            estimated_gross=gross_amount,
            estimated_commission=commission,
            estimated_slippage=slippage,
            estimated_total=gross_amount,
            can_execute=can_execute,
            rejection_reason=rejection_reason,
            cash_balance_before=cash_before,
            cash_balance_after=cash_after if can_execute else cash_before
        )

    def place_order(
        self,
        user_id: int,
        order_in: OrderCreate,
        commission_rate: Optional[Decimal] = None,
        slippage_rate: Optional[Decimal] = None
    ) -> Order:
        if commission_rate is None:
            commission_rate = Decimal(str(settings.DEFAULT_COMMISSION_RATE))
        if slippage_rate is None:
            slippage_rate = Decimal(str(settings.DEFAULT_SLIPPAGE_RATE))

        # Begin atomic transaction
        portfolio = self.db.query(Portfolio)\
            .filter(Portfolio.id == order_in.portfolio_id, Portfolio.user_id == user_id)\
            .with_for_update()\
            .first()
        if not portfolio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        symbol = self.db.query(Symbol).filter(Symbol.ticker == order_in.symbol.upper()).first()
        if not symbol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {order_in.symbol} not found")

        side = order_in.side.upper()
        order_type = order_in.order_type.upper()
        quantity = Decimal(str(order_in.quantity))

        # Create Order record
        order = Order(
            portfolio_id=portfolio.id,
            symbol_id=symbol.id,
            order_type=order_type,
            side=side,
            status=OrderStatus.PENDING.value,
            quantity=quantity,
            filled_quantity=Decimal("0.0"),
            price=Decimal(str(order_in.price)) if order_in.price else None,
            stop_price=Decimal(str(order_in.stop_price)) if order_in.stop_price else None,
            time_in_force=order_in.time_in_force
        )
        self.db.add(order)
        self.db.flush()

        current_market_price = self.get_latest_market_price(symbol.id)

        # Execution logic based on order type
        should_fill = False
        execution_price = current_market_price

        if order_type == OrderType.MARKET.value:
            should_fill = True
            execution_price = current_market_price
        elif order_type == OrderType.LIMIT.value:
            if order.price is None:
                order.status = OrderStatus.REJECTED.value
                order.reject_reason = "Limit price is required for LIMIT order"
                self.db.commit()
                return order
            if side == OrderSide.BUY.value and current_market_price <= order.price:
                should_fill = True
                execution_price = min(current_market_price, order.price)
            elif side == OrderSide.SELL.value and current_market_price >= order.price:
                should_fill = True
                execution_price = max(current_market_price, order.price)
        elif order_type == OrderType.STOP_LOSS.value:
            if order.stop_price is None:
                order.status = OrderStatus.REJECTED.value
                order.reject_reason = "Stop price is required for STOP_LOSS order"
                self.db.commit()
                return order
            if side == OrderSide.SELL.value and current_market_price <= order.stop_price:
                should_fill = True
                execution_price = current_market_price
        elif order_type == OrderType.TAKE_PROFIT.value:
            if order.price is None:
                order.status = OrderStatus.REJECTED.value
                order.reject_reason = "Target price is required for TAKE_PROFIT order"
                self.db.commit()
                return order
            if side == OrderSide.SELL.value and current_market_price >= order.price:
                should_fill = True
                execution_price = current_market_price

        # If condition triggers or market order, execute trade ACID-compliant
        if should_fill:
            self._execute_trade(
                order=order,
                portfolio=portfolio,
                symbol=symbol,
                base_price=execution_price,
                commission_rate=commission_rate,
                slippage_rate=slippage_rate
            )

        self.db.commit()
        self.db.refresh(order)
        return order

    def _execute_trade(
        self,
        order: Order,
        portfolio: Portfolio,
        symbol: Symbol,
        base_price: Decimal,
        commission_rate: Decimal,
        slippage_rate: Decimal
    ):
        qty = order.quantity
        gross_value = qty * base_price
        commission = gross_value * commission_rate

        if order.side == OrderSide.BUY.value:
            # Slippage raises effective buy price
            slippage_cost = gross_value * slippage_rate
            effective_price = base_price * (Decimal("1.0") + slippage_rate)
            total_cash_needed = (qty * effective_price) + commission

            if portfolio.cash_balance < total_cash_needed:
                order.status = OrderStatus.REJECTED.value
                order.reject_reason = f"Insufficient cash balance. Required: ₹{total_cash_needed:,.2f}, Available: ₹{portfolio.cash_balance:,.2f}"
                return

            # Deduct cash atomically
            portfolio.cash_balance -= total_cash_needed

            # Update or create holding with Average Cost Basis
            holding = self.db.query(Holding)\
                .filter(Holding.portfolio_id == portfolio.id, Holding.symbol_id == symbol.id)\
                .first()

            if not holding:
                holding = Holding(
                    portfolio_id=portfolio.id,
                    symbol_id=symbol.id,
                    quantity=qty,
                    average_buy_price=effective_price,
                    total_invested=qty * effective_price
                )
                self.db.add(holding)
            else:
                new_qty = holding.quantity + qty
                new_total_invested = holding.total_invested + (qty * effective_price)
                new_avg_price = new_total_invested / new_qty
                holding.quantity = new_qty
                holding.average_buy_price = new_avg_price
                holding.total_invested = new_total_invested

            # Record Trade
            trade = Trade(
                order_id=order.id,
                portfolio_id=portfolio.id,
                symbol_id=symbol.id,
                side=OrderSide.BUY.value,
                quantity=qty,
                execution_price=effective_price,
                commission=commission,
                slippage=slippage_cost,
                realized_pnl=Decimal("0.0"),
                executed_at=datetime.now(timezone.utc)
            )
            self.db.add(trade)

            # Record Cash Transaction
            tx = Transaction(
                portfolio_id=portfolio.id,
                type=TransactionType.BUY.value,
                amount=-total_cash_needed,
                balance_after=portfolio.cash_balance,
                notes=f"Bought {qty} {symbol.ticker} @ ₹{effective_price:,.2f} (Comm: ₹{commission:,.2f})"
            )
            self.db.add(tx)

            order.status = OrderStatus.FILLED.value
            order.filled_quantity = qty

        elif order.side == OrderSide.SELL.value:
            holding = self.db.query(Holding)\
                .filter(Holding.portfolio_id == portfolio.id, Holding.symbol_id == symbol.id)\
                .first()

            if not holding or holding.quantity < qty:
                available_qty = holding.quantity if holding else Decimal("0.0")
                order.status = OrderStatus.REJECTED.value
                order.reject_reason = f"Insufficient holding quantity. Required: {qty}, Available: {available_qty}"
                return

            # Slippage lowers effective sell price
            slippage_cost = gross_value * slippage_rate
            effective_price = base_price * (Decimal("1.0") - slippage_rate)
            total_proceeds = (qty * effective_price) - commission

            # Calculate Realized P&L: (effective_sell_price - average_buy_price) * qty - commission
            cost_basis = holding.average_buy_price * qty
            gross_pnl = (effective_price * qty) - cost_basis
            net_realized_pnl = gross_pnl - commission

            # Credit cash balance
            portfolio.cash_balance += total_proceeds

            # Update holding
            holding.quantity -= qty
            if holding.quantity == Decimal("0.0"):
                holding.total_invested = Decimal("0.0")
                holding.average_buy_price = Decimal("0.0")
            else:
                holding.total_invested = holding.quantity * holding.average_buy_price

            # Record Trade
            trade = Trade(
                order_id=order.id,
                portfolio_id=portfolio.id,
                symbol_id=symbol.id,
                side=OrderSide.SELL.value,
                quantity=qty,
                execution_price=effective_price,
                commission=commission,
                slippage=slippage_cost,
                realized_pnl=net_realized_pnl,
                executed_at=datetime.now(timezone.utc)
            )
            self.db.add(trade)

            # Record Cash Transaction
            tx = Transaction(
                portfolio_id=portfolio.id,
                type=TransactionType.SELL.value,
                amount=total_proceeds,
                balance_after=portfolio.cash_balance,
                notes=f"Sold {qty} {symbol.ticker} @ ₹{effective_price:,.2f} (Realized PnL: ₹{net_realized_pnl:,.2f})"
            )
            self.db.add(tx)

            order.status = OrderStatus.FILLED.value
            order.filled_quantity = qty

    def cancel_order(self, user_id: int, order_id: int) -> Order:
        order = self.db.query(Order)\
            .join(Portfolio)\
            .filter(Order.id == order_id, Portfolio.user_id == user_id)\
            .first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        if order.status != OrderStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status '{order.status}'"
            )

        order.status = OrderStatus.CANCELLED.value
        self.db.commit()
        self.db.refresh(order)
        return order
