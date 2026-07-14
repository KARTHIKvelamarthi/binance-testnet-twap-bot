"""
Input validation for order requests.

Keeping validation separate from both the CLI layer and the API client
means the same rules apply no matter how an order request is constructed
(CLI today, could be a script or web form later) and keeps client.py
focused only on talking to Binance.
"""

from dataclasses import dataclass
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


class ValidationError(Exception):
    """Raised when an order request fails validation, before any API call is made."""


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None


def validate_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
) -> OrderRequest:
    """Validate raw CLI input and return a clean OrderRequest, or raise ValidationError.

    Deliberately fails fast on the first problem with a clear message, since
    this runs before any network call — no point contacting the API with
    input we already know is invalid.
    """
    if not symbol or not symbol.strip():
        raise ValidationError("Symbol cannot be empty (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()

    side = side.strip().upper() if side else ""
    if side not in VALID_SIDES:
        raise ValidationError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")

    order_type = order_type.strip().upper() if order_type else ""
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'."
        )

    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive, got {quantity}.")

    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a number, got '{price}'.")
        if price <= 0:
            raise ValidationError(f"Price must be positive, got {price}.")
    else:
        # MARKET orders should not carry a price — ignore if one was passed,
        # rather than silently sending it to the API where it's meaningless.
        price = None

    return OrderRequest(
        symbol=symbol, side=side, order_type=order_type, quantity=quantity, price=price
    )
