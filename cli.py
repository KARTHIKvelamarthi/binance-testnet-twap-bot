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
from bot.validators import OrderRequest, ValidationError, validate_order
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


def safe_print(text: str) -> None:
    """Print text safely, replacing emojis if the system console doesn't support them."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe_text = text.replace("✅", "[SUCCESS]").replace("❌", "[ERROR]")
        try:
            print(safe_text)
        except UnicodeEncodeError:
            encoding = sys.stdout.encoding or "ascii"
            print(text.encode(encoding, errors="backslashreplace").decode(encoding))


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
        safe_print("✅ Order placed successfully.")
        print(f"  Order ID:      {result.order_id}")
        print(f"  Status:        {result.status}")
        print(f"  Executed Qty:  {result.executed_qty}")
        print(f"  Avg Price:     {result.avg_price}")
    else:
        safe_print("❌ Order failed.")
        print(f"  Reason: {result.error_message}")


def run_interactive_mode() -> OrderRequest:
    """Walk the user through interactive order entry when no CLI flags are passed."""
    print("=== Interactive Order Entry ===")
    
    # 1. Symbol
    while True:
        val = input("Enter symbol (e.g. BTCUSDT): ").strip()
        try:
            validate_order(symbol=val, side="BUY", order_type="MARKET", quantity=1.0)
            symbol = val.upper()
            break
        except ValidationError as exc:
            print(f"Invalid input: {exc} Please try again.")

    # 2. Side
    while True:
        val = input("Enter side (BUY/SELL): ").strip()
        try:
            validate_order(symbol=symbol, side=val, order_type="MARKET", quantity=1.0)
            side = val.upper()
            break
        except ValidationError as exc:
            print(f"Invalid input: {exc} Please try again.")

    # 3. Order Type
    while True:
        val = input("Enter order type (MARKET/LIMIT/TWAP): ").strip()
        try:
            # Pass dummy valid parameters for other fields to only validate the order type itself
            validate_order(symbol=symbol, side=side, order_type=val, quantity=1.0, price=10.0, duration=10, slices=2)
            order_type = val.upper()
            break
        except ValidationError as exc:
            print(f"Invalid input: {exc} Please try again.")

    # 4. Price (LIMIT only)
    price = None
    if order_type == "LIMIT":
        while True:
            val = input("Enter price: ").strip()
            try:
                validate_order(symbol=symbol, side=side, order_type="LIMIT", quantity=1.0, price=val)
                price = float(val)
                break
            except ValidationError as exc:
                print(f"Invalid input: {exc} Please try again.")

    # 5. Duration and Slices (TWAP only)
    duration = None
    slices = None
    if order_type == "TWAP":
        while True:
            d_val = input("Enter duration (seconds): ").strip()
            s_val = input("Enter slices: ").strip()
            try:
                validate_order(
                    symbol=symbol,
                    side=side,
                    order_type="TWAP",
                    quantity=1.0,
                    duration=d_val,
                    slices=s_val
                )
                duration = int(d_val)
                slices = int(s_val)
                break
            except ValidationError as exc:
                print(f"Invalid input: {exc} Please try again.")

    # 6. Quantity
    while True:
        val = input("Enter quantity: ").strip()
        try:
            request = validate_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=val,
                price=price,
                duration=duration,
                slices=slices
            )
            return request
        except ValidationError as exc:
            print(f"Invalid input: {exc} Please try again.")


def main() -> int:
    logger = setup_logging()
    
    if len(sys.argv) == 1:
        try:
            request = run_interactive_mode()
        except (KeyboardInterrupt, EOFError):
            print("\nOrder entry cancelled.")
            return 0
    else:
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
            safe_print(f"❌ Invalid input: {exc}")
            return 1

    print_summary(request)

    try:
        client = get_client()
    except BinanceClientError as exc:
        logger.error("Client initialization failed: %s", exc)
        safe_print(f"❌ {exc}")
        return 1

    if request.order_type == "TWAP":
        result = execute_twap(client, request)
        print("\n--- TWAP Execution Summary ---")
        print(f"  Slices Succeeded: {result.slices_succeeded}/{request.slices}")
        print(f"  Slices Failed:    {result.slices_failed}/{request.slices}")
        print(f"  Total Executed:   {result.total_executed_qty}")
        print("------------------------------\n")
        if result.success:
            safe_print("✅ TWAP completed successfully.")
        else:
            safe_print("❌ TWAP failed (all slices failed).")
        return 0 if result.success else 1
    else:
        result = execute_order(client, request)
        print_result(result)
        return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
