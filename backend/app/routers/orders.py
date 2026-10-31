from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.order import Order, Trade
from backend.app.schemas.order import (
    OrderCreate, OrderResponse, TradeResponse,
    OrderPreviewRequest, OrderPreviewResponse
)
from backend.app.services.trading_engine import TradingEngine
from backend.app.repositories.order_repo import OrderRepository

router = APIRouter(prefix="/orders", tags=["Paper Trading & Orders"])

@router.post("/preview", response_model=OrderPreviewResponse)
def preview_order(
    request: OrderPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    engine = TradingEngine(db)
    return engine.preview_order(current_user.id, request)

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    engine = TradingEngine(db)
    order = engine.place_order(current_user.id, order_in)
    return OrderResponse(
        id=order.id,
        portfolio_id=order.portfolio_id,
        symbol_id=order.symbol_id,
        ticker=order.symbol.ticker,
        symbol_name=order.symbol.name,
        order_type=order.order_type,
        side=order.side,
        status=order.status,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        price=order.price,
        stop_price=order.stop_price,
        time_in_force=order.time_in_force,
        reject_reason=order.reject_reason,
        created_at=order.created_at,
        updated_at=order.updated_at
    )

@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    engine = TradingEngine(db)
    order = engine.cancel_order(current_user.id, order_id)
    return OrderResponse(
        id=order.id,
        portfolio_id=order.portfolio_id,
        symbol_id=order.symbol_id,
        ticker=order.symbol.ticker,
        symbol_name=order.symbol.name,
        order_type=order.order_type,
        side=order.side,
        status=order.status,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        price=order.price,
        stop_price=order.stop_price,
        time_in_force=order.time_in_force,
        reject_reason=order.reject_reason,
        created_at=order.created_at,
        updated_at=order.updated_at
    )

@router.get("/portfolio/{portfolio_id}", response_model=List[OrderResponse])
def list_portfolio_orders(
    portfolio_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = OrderRepository(db)
    orders = repo.list_by_portfolio_id(portfolio_id, status=status_filter, skip=skip, limit=limit)
    return [
        OrderResponse(
            id=o.id,
            portfolio_id=o.portfolio_id,
            symbol_id=o.symbol_id,
            ticker=o.symbol.ticker,
            symbol_name=o.symbol.name,
            order_type=o.order_type,
            side=o.side,
            status=o.status,
            quantity=o.quantity,
            filled_quantity=o.filled_quantity,
            price=o.price,
            stop_price=o.stop_price,
            time_in_force=o.time_in_force,
            reject_reason=o.reject_reason,
            created_at=o.created_at,
            updated_at=o.updated_at
        )
        for o in orders
    ]

@router.get("/trades", response_model=List[TradeResponse])
def list_user_trades(
    portfolio_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = OrderRepository(db)
    if portfolio_id:
        trades = repo.list_trades_by_portfolio_id(portfolio_id, limit=limit)
    else:
        trades = repo.list_trades_by_user_id(current_user.id, limit=limit)

    return [
        TradeResponse(
            id=t.id,
            order_id=t.order_id,
            portfolio_id=t.portfolio_id,
            symbol_id=t.symbol_id,
            ticker=t.symbol.ticker,
            symbol_name=t.symbol.name,
            side=t.side,
            quantity=t.quantity,
            execution_price=t.execution_price,
            commission=t.commission,
            slippage=t.slippage,
            realized_pnl=t.realized_pnl,
            executed_at=t.executed_at
        )
        for t in trades
    ]
