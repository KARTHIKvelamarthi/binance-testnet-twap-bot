"""
Order placement orchestration — sits between validated input and the
Binance client, and shapes the response into a clean summary for display.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .client import BinanceClientError, place_futures_order
from .validators import OrderRequest

logger = logging.getLogger("trading_bot")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    raw_response: Optional[dict] = None
    error_message: Optional[str] = None


def execute_order(client, request: OrderRequest) -> OrderResult:
    """Place the given order and return a structured OrderResult.

    Never raises — API/network failures are caught here and returned as a
    failed OrderResult, so the CLI layer only ever deals with one
    consistent shape whether the order succeeded or failed.
    """
    try:
        response = place_futures_order(
            client=client,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
        )
        return OrderResult(
            success=True,
            order_id=str(response.get("orderId")),
            status=response.get("status"),
            executed_qty=response.get("executedQty"),
            avg_price=response.get("avgPrice"),
            raw_response=response,
        )
    except BinanceClientError as exc:
        return OrderResult(success=False, error_message=str(exc))
