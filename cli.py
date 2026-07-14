"""
CLI entry point for the Binance Futures Testnet trading bot.

Usage:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
"""

import argparse
import sys

from bot.client import BinanceClientError, get_client
from bot.logging_config import setup_logging
from bot.orders import execute_order
from bot.validators import ValidationError, validate_order
from bot.twap import execute_twap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place MARKET or LIMIT orders on Binance Futures Testnet (USDT-M)."
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "TWAP", "market", "limit", "twap"],
    )
    parser.add_argument("--quantity", required=True, type=float, help="Order quantity")
    parser.add_argument(
        "--price", type=float, default=None,
        help="Required for LIMIT orders; ignored for MARKET orders",
    )
    parser.add_argument(
        "--duration", type=int, default=None,
        help="Duration in seconds to spread TWAP execution over (required for TWAP)",
    )
    parser.add_argument(
        "--slices", type=int, default=None,
        help="Number of slices to split the TWAP quantity into (required for TWAP)",
    )
    return parser


def print_summary(request) -> None:
    print("\n--- Order Request Summary ---")
    print(f"  Symbol:     {request.symbol}")
    print(f"  Side:       {request.side}")
    print(f"  Type:       {request.order_type}")
    print(f"  Quantity:   {request.quantity}")
    if request.price is not None:
        print(f"  Price:      {request.price}")
    if request.duration is not None:
        print(f"  Duration:   {request.duration} seconds")
    if request.slices is not None:
        print(f"  Slices:     {request.slices}")
    print("------------------------------\n")


def print_result(result) -> None:
    if result.success:
        print("✅ Order placed successfully.")
        print(f"  Order ID:      {result.order_id}")
        print(f"  Status:        {result.status}")
        print(f"  Executed Qty:  {result.executed_qty}")
        print(f"  Avg Price:     {result.avg_price}")
    else:
        print("❌ Order failed.")
        print(f"  Reason: {result.error_message}")


def main() -> int:
    logger = setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        request = validate_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            duration=args.duration,
            slices=args.slices,
        )
    except ValidationError as exc:
        logger.error("Input validation failed: %s", exc)
        print(f"❌ Invalid input: {exc}")
        return 1

    print_summary(request)

    try:
        client = get_client()
    except BinanceClientError as exc:
        logger.error("Client initialization failed: %s", exc)
        print(f"❌ {exc}")
        return 1

    if request.order_type == "TWAP":
        result = execute_twap(client, request)
        print("\n--- TWAP Execution Summary ---")
        print(f"  Slices Succeeded: {result.slices_succeeded}/{request.slices}")
        print(f"  Slices Failed:    {result.slices_failed}/{request.slices}")
        print(f"  Total Executed:   {result.total_executed_qty}")
        print("------------------------------\n")
        if result.success:
            print("✅ TWAP completed successfully.")
        else:
            print("❌ TWAP failed (all slices failed).")
        return 0 if result.success else 1
    else:
        result = execute_order(client, request)
        print_result(result)
        return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
