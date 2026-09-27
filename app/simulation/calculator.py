"""Main calculation engine orchestrator."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from app.simulation.models import PositionInput, PositionResult
from app.simulation.pnl import calculate_pnl
from app.simulation.roi import calculate_roi
from app.simulation.liquidation import calculate_simulated_liquidation
from app.simulation.precision import quantize_tick
from app.simulation.fees import calculate_realized_pnl


def calculate_position(
    input_data: PositionInput,
    mark_price: Decimal,
    tick_size: Decimal,
    step_size: Decimal,
    funding_rate: Optional[Decimal] = None,
) -> PositionResult:
    """Calculates all position metrics deterministically using Decimal arithmetic.

    1. Position Size = margin * leverage
    2. PNL = calculate_pnl(side, size, entry, mark)
    3. ROI = calculate_roi(pnl, margin)
    4. Liq Price = calculate_simulated_liquidation(side, entry, leverage, margin_ratio, tick_size)
    5. Realized PNL = -(opening commission) + funding_fees
       If funding_rate is provided, auto-calculated from Binance fee model.
       Otherwise uses input_data.realized_pnl as-is.
    """
    # 1. Position Size in USDT
    position_size = input_data.margin * input_data.leverage

    # 2. Unrealized PNL in USDT
    pnl = calculate_pnl(
        side=input_data.side,
        position_size=position_size,
        entry_price=input_data.entry_price,
        mark_price=mark_price,
    )

    # 3. ROI (%)
    roi = calculate_roi(pnl=pnl, margin=input_data.margin)

    # 4. Simulated Liquidation Price
    liq_price = calculate_simulated_liquidation(
        side=input_data.side,
        entry_price=input_data.entry_price,
        leverage=input_data.leverage,
        margin_ratio=input_data.margin_ratio,
        tick_size=tick_size,
    )

    # 5. Realized PNL: auto-calculated from Binance fee model when funding_rate provided
    if funding_rate is not None:
        realized_pnl = calculate_realized_pnl(
            position_size=position_size,
            side=input_data.side,
            funding_rate=funding_rate,
        )
    else:
        realized_pnl = input_data.realized_pnl

    now = datetime.now(timezone.utc)
    return PositionResult(
        symbol=input_data.symbol,
        side=input_data.side,
        entry_price=input_data.entry_price,
        leverage=input_data.leverage,
        margin=input_data.margin,
        margin_ratio=input_data.margin_ratio,
        mark_price=mark_price,
        position_size=position_size,
        pnl=pnl,
        roi=roi,
        liquidation_price=liq_price,
        realized_pnl=realized_pnl,
        tick_size=tick_size,
        step_size=step_size,
        created_at=now,
        updated_at=now,
        mode=input_data.mode,
    )
