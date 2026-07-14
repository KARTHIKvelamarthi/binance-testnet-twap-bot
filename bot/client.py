"""
Thin wrapper around python-binance's Futures Testnet client.

Isolating all direct API interaction here means orders.py and cli.py never
touch the python-binance library directly — if the underlying library or
even the exchange changes, only this file needs to change.
"""

import logging
import os
from typing import Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

logger = logging.getLogger("trading_bot")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceClientError(Exception):
    """Raised when the Binance client cannot be created or a call fails unrecoverably."""


def get_client(api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Client:
    """Create a python-binance Client configured for Futures Testnet.

    Falls back to BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET
    environment variables if not passed explicitly, so credentials never
    need to be hardcoded or typed on the command line (where they'd end
    up in shell history).
    """
    api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET")

    if not api_key or not api_secret:
        raise BinanceClientError(
            "Missing API credentials. Set BINANCE_TESTNET_API_KEY and "
            "BINANCE_TESTNET_API_SECRET environment variables."
        )

    client = Client(api_key, api_secret)
    client.FUTURES_URL = TESTNET_BASE_URL + "/fapi"
    logger.debug("Binance Futures Testnet client initialized (base_url=%s)", TESTNET_BASE_URL)
    return client


def place_futures_order(
    client: Client,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
) -> dict:
    """Place a MARKET or LIMIT order on Binance Futures Testnet and return the raw response.

    Any Binance-side error (bad symbol, insufficient testnet balance, etc.)
    or network failure is logged with full detail and re-raised as a
    BinanceClientError so the CLI layer can show a clean message without
    needing to know python-binance's internal exception types.
    """
    order_kwargs = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
    }
    if order_type == "LIMIT":
        order_kwargs["price"] = price
        order_kwargs["timeInForce"] = "GTC"  # Good-Til-Canceled — standard default for limit orders

    logger.info("Submitting order request: %s", order_kwargs)

    try:
        response = client.futures_create_order(**order_kwargs)
        logger.info("Order response: %s", response)
        return response
    except (BinanceAPIException, BinanceRequestException) as exc:
        logger.error("Binance API error while placing order %s: %s", order_kwargs, exc)
        raise BinanceClientError(f"Binance API error: {exc}") from exc
    except Exception as exc:  # network failures, timeouts, etc.
        logger.error("Unexpected/network error while placing order %s: %s", order_kwargs, exc)
        raise BinanceClientError(f"Network or unexpected error: {exc}") from exc
