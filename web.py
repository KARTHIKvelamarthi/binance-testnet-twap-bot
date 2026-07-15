import os
import re
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bot.client import get_client, BinanceClientError
from bot.validators import validate_order, ValidationError
from bot.orders import execute_order
from bot.twap import execute_twap
from bot.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger("trading_bot")

app = FastAPI(title="Binance Futures TWAP Bot Web API")

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")


class OrderPayload(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    duration: Optional[int] = None
    slices: Optional[int] = None


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.post("/api/order")
def place_order(payload: OrderPayload):
    api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="Binance Testnet API keys not configured in server environment."
        )

    # Run through existing validators
    try:
        req = validate_order(
            symbol=payload.symbol,
            side=payload.side,
            order_type=payload.order_type,
            quantity=payload.quantity,
            price=payload.price,
            duration=payload.duration,
            slices=payload.slices,
        )
    except ValidationError as e:
        error_msg = str(e)
        logger.error(f"Input validation failed: {error_msg}")
        logger.info("=" * 80)
        raise HTTPException(status_code=400, detail=error_msg)

    # Initialize client
    try:
        client = get_client()
    except Exception as e:
        logger.error(f"Failed to initialize Binance client: {e}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Client initialization failed: {e}")

    try:
        if req.order_type == "TWAP":
            res = execute_twap(client, req)
            if res.success:
                status = "FILLED" if res.slices_failed == 0 else "PARTIALLY_FILLED"
                return {
                    "success": True,
                    "order_id": "TWAP_MULTIPLE",
                    "status": status,
                    "executed_qty": f"{res.total_executed_qty:.4f}",
                    "avg_price": f"{res.avg_price:.2f}" if res.avg_price > 0 else "N/A"
                }
            else:
                return {
                    "success": False,
                    "error_message": f"TWAP execution failed completely. Slices: {res.slices_succeeded}/{req.slices} succeeded."
                }
        else:
            res = execute_order(client, req)
            if res.success:
                return {
                    "success": True,
                    "order_id": res.order_id,
                    "status": res.status,
                    "executed_qty": res.executed_qty,
                    "avg_price": res.avg_price
                }
            else:
                return {
                    "success": False,
                    "error_message": res.error_message
                }
    finally:
        logger.info("=" * 80)


@app.get("/api/recent-orders")
def get_recent_orders():
    log_path = "logs/trading_bot.log"
    if not os.path.exists(log_path):
        return []

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")

    runs = []
    current_run = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if "================================================================================" in line_str:
            if current_run:
                runs.append(current_run)
                current_run = []
        else:
            current_run.append(line_str)
    if current_run:
        runs.append(current_run)

    recent_orders = []
    for run in reversed(runs):
        timestamp = "N/A"
        symbol = "N/A"
        side = "N/A"
        order_type = "N/A"
        status = "N/A"
        details = ""

        # Find submission context first
        for line in run:
            parts = line.split(" | ", 3)
            if len(parts) >= 4:
                ts, level, logger_name, msg = parts[0], parts[1], parts[2], parts[3]
                if ts and timestamp == "N/A":
                    timestamp = ts

                sub_match = re.search(
                    r"Submitting order:\s+([A-Z]+)\s+([\d\.]+)\s+([A-Z0-9]+)\s+([A-Z]+)(?:\s+@\s+([\d\.]+))?",
                    msg
                )
                if sub_match:
                    side = sub_match.group(1)
                    symbol = sub_match.group(3)
                    order_type = sub_match.group(4)

        # Find execution outcome (from end of run to beginning)
        outcome_found = False
        for line in reversed(run):
            parts = line.split(" | ", 3)
            if len(parts) >= 4:
                ts, level, logger_name, msg = parts[0], parts[1], parts[2], parts[3]

                # Match Order confirmed filled
                fill_match = re.search(r"Order confirmed filled:\s+id=(\d+)\s+executedQty=([\d\.]+)\s+avgPrice=([\d\.]+)", msg)
                if fill_match:
                    status = "FILLED"
                    details = f"Filled {fill_match.group(2)} @ {float(fill_match.group(3)):.2f}"
                    outcome_found = True
                    break

                # Match Order status
                status_match = re.search(r"Order status:\s+id=(\d+)\s+status=([A-Z]+)\s+executedQty=([\d\.]+)\s+avgPrice=([\d\.]+)", msg)
                if status_match:
                    status = status_match.group(2)
                    details = f"Executed {status_match.group(3)} @ {float(status_match.group(4)):.2f}"
                    outcome_found = True
                    break

                # Match Order rejected
                reject_match = re.search(r"Order rejected:\s+reason=(.*)", msg)
                if reject_match:
                    status = "REJECTED"
                    details = reject_match.group(1)
                    outcome_found = True
                    break

                # Match TWAP summary
                twap_match = re.search(r"TWAP summary:\s+(\d+)/(\d+)\s+slices filled,\s+total executed\s+([\d\.]+)\s+([A-Z0-9]+)", msg)
                if twap_match:
                    status = "FILLED" if twap_match.group(1) == twap_match.group(2) else "PARTIALLY_FILLED"
                    details = f"{twap_match.group(1)}/{twap_match.group(2)} slices, total exec {twap_match.group(3)}"
                    outcome_found = True
                    break

                # Match Input validation failed
                val_match = re.search(r"Input validation failed:\s+(.*)", msg)
                if val_match:
                    status = "REJECTED"
                    details = val_match.group(1)
                    outcome_found = True
                    break

        if outcome_found or symbol != "N/A":
            recent_orders.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "status": status,
                "details": details
            })
            if len(recent_orders) >= 10:
                break

    return recent_orders
