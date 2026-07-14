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


def execute_twap(client, request: OrderRequest) -> TwapResult:
    slice_qty = request.quantity / request.slices
    interval = request.duration / request.slices

    slices_succeeded = 0
    slices_failed = 0
    total_executed_qty = 0.0

    for i in range(request.slices):
        if i > 0:
            time.sleep(interval)

        logger.info(f"Placing TWAP slice {i + 1}/{request.slices} with quantity {slice_qty}")
        try:
            response = place_futures_order(
                client=client,
                symbol=request.symbol,
                side=request.side,
                order_type="MARKET",
                quantity=slice_qty,
            )
            slices_succeeded += 1
            exec_qty_str = response.get("executedQty", "0")
            try:
                total_executed_qty += float(exec_qty_str)
            except ValueError:
                total_executed_qty += slice_qty
        except BinanceClientError as exc:
            # We don't abort on a single slice failure so that transient network glitches
            # or brief API rejects don't ruin a long-running TWAP execution completely.
            slices_failed += 1
            logger.error(f"Slice {i + 1} failed: {exc}")

    # Log execution summary
    logger.info("TWAP execution completed.")
    logger.info(f"Succeeded slices: {slices_succeeded}/{request.slices}")
    logger.info(f"Failed slices: {slices_failed}/{request.slices}")
    logger.info(f"Total quantity executed: {total_executed_qty}")

    return TwapResult(
        success=slices_succeeded > 0,
        slices_succeeded=slices_succeeded,
        slices_failed=slices_failed,
        total_executed_qty=total_executed_qty,
    )
