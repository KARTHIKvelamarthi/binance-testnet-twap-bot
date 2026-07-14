"""
Thin wrapper around python-binance's Futures Testnet client.

Isolating all direct API interaction here means orders.py and cli.py never
touch the python-binance library directly — if the underlying library or
even the exchange changes, only this file needs to change.
"""

import logging
import os
import time
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

    client = Client(api_key, api_secret, testnet=True)
    
    # Calculate time offset to prevent timestamp/recWindow errors
    try:
        server_time = client.get_server_time()['serverTime']
        local_time = int(time.time() * 1000)
        client.timestamp_offset = server_time - local_time
        logger.debug("Server time sync complete. Offset: %d ms", client.timestamp_offset)
    except Exception as exc:
        logger.warning("Failed to sync server time: %s", exc)

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
    is_twap: bool = False,
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

    # Clean structured single-line submission log
    if not is_twap:
        if order_type == "LIMIT":
            logger.info("Submitting order: %s %s %s LIMIT @ %s", side, quantity, symbol, price)
        else:
            logger.info("Submitting order: %s %s %s %s", side, quantity, symbol, order_type)

    try:
        response = client.futures_create_order(**order_kwargs)
        if not is_twap:
            logger.info(
                "Order accepted: id=%s status=%s",
                response.get("orderId"),
                response.get("status"),
            )
    except Exception as exc:
        clean_msg = str(exc)
        # Avoid printing duplicate or noisy traceback log
        logger.error("Order rejected: reason=%s", clean_msg)
        raise BinanceClientError(clean_msg) from exc

    # Query the order status in a loop to retrieve final fills/status
    try:
        query_response = response
        for attempt in range(5):
            time.sleep(1.0)
            query_response = client.futures_get_order(symbol=symbol, orderId=response.get("orderId"))
            status = query_response.get("status")
            if status in ["FILLED", "CANCELED", "EXPIRED"]:
                break

        if not is_twap:
            status = query_response.get("status")
            executed_qty = query_response.get("executedQty", "0.0000")
            avg_price = query_response.get("avgPrice", "0.00")
            if status == "FILLED":
                logger.info(
                    "Order confirmed filled: id=%s executedQty=%s avgPrice=%s",
                    query_response.get("orderId"),
                    executed_qty,
                    avg_price,
                )
            else:
                logger.info(
                    "Order status: id=%s status=%s executedQty=%s avgPrice=%s",
                    query_response.get("orderId"),
                    status,
                    executed_qty,
                    avg_price,
                )
        return query_response
    except Exception as exc:
        logger.warning("Follow-up query failed: reason=%s", exc)
        return response
