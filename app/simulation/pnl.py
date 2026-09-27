"""Unrealized PNL calculation module."""

from decimal import Decimal
from app.simulation.models import Side


def calculate_pnl(
    side: Side,
    position_size: Decimal,
    entry_price: Decimal,
    mark_price: Decimal,
) -> Decimal:
    """Calculates unrealized PNL in USDT using Decimal arithmetic.

    For LONG:
        PNL = position_size * ((mark_price - entry_price) / entry_price)

    For SHORT:
        PNL = position_size * ((entry_price - mark_price) / entry_price)
    """
    if entry_price <= Decimal("0"):
        raise ValueError("entry_price must be strictly positive")
    if position_size <= Decimal("0"):
        raise ValueError("position_size must be strictly positive")

    if side == Side.LONG:
        pnl = position_size * ((mark_price - entry_price) / entry_price)
    elif side == Side.SHORT:
        pnl = position_size * ((entry_price - mark_price) / entry_price)
    else:
        raise ValueError(f"Unknown side: {side}")

    return pnl
