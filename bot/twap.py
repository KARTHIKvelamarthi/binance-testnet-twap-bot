import logging
import time
from dataclasses import dataclass
from .client import BinanceClientError, place_futures_order
from .validators import OrderRequest

logger = logging.getLogger("trading_bot")


@dataclass
class TwapResult:
    success: bool
    slices_succeeded: int
    slices_failed: int
    total_executed_qty: float
    avg_price: float = 0.0


def execute_twap(client, request: OrderRequest) -> TwapResult:
    logger.info("Submitting order: %s %s %s TWAP", request.side, request.quantity, request.symbol)
    slice_qty = request.quantity / request.slices
    interval = request.duration / request.slices

    slices_succeeded = 0
    slices_failed = 0
    total_executed_qty = 0.0
    cumulative_value = 0.0

    for i in range(request.slices):
        if i > 0:
            time.sleep(interval)

        logger.info(f"TWAP slice {i + 1}/{request.slices} submitted: {slice_qty:.4f} {request.symbol}")
        try:
            response = place_futures_order(
                client=client,
                symbol=request.symbol,
                side=request.side,
                order_type="MARKET",
                quantity=slice_qty,
                is_twap=True,
            )
            slices_succeeded += 1
            exec_qty_str = response.get("executedQty", "0")
            avg_price_str = response.get("avgPrice", "0.00")
            
            try:
                exec_qty_val = float(exec_qty_str)
                avg_price_val = float(avg_price_str)
                logger.info(f"TWAP slice {i + 1}/{request.slices} confirmed filled: {exec_qty_val:.4f} @ {avg_price_val:.2f}")
                total_executed_qty += exec_qty_val
                cumulative_value += exec_qty_val * avg_price_val
            except ValueError:
                logger.info(f"TWAP slice {i + 1}/{request.slices} confirmed filled: {exec_qty_str} @ {avg_price_str}")
                total_executed_qty += slice_qty
        except BinanceClientError as exc:
            # We don't abort on a single slice failure so that transient network glitches
            # or brief API rejects don't ruin a long-running TWAP execution completely.
            slices_failed += 1
            logger.error(f"TWAP slice {i + 1}/{request.slices} rejected: reason={exc}")

    avg_price_final = cumulative_value / total_executed_qty if total_executed_qty > 0 else 0.0

    # Log execution summary
    logger.info(f"TWAP summary: {slices_succeeded}/{request.slices} slices filled, total executed {total_executed_qty:.4f} {request.symbol}")

    return TwapResult(
        success=slices_succeeded > 0,
        slices_succeeded=slices_succeeded,
        slices_failed=slices_failed,
        total_executed_qty=total_executed_qty,
        avg_price=avg_price_final,
    )
