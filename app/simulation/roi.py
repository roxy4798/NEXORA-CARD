"""Return on Investment (ROI) calculation module."""

from decimal import Decimal


def calculate_roi(pnl: Decimal, margin: Decimal) -> Decimal:
    """Calculates ROI percentage from PNL and initial margin collateral.

    ROI (%) = (PNL / margin) * 100
    """
    if margin <= Decimal("0"):
        raise ValueError("margin must be strictly positive")

    return (pnl / margin) * Decimal("100")
