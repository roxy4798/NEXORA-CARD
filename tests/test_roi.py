"""Unit tests for ROI calculations."""

from decimal import Decimal
import pytest
from app.simulation.roi import calculate_roi


def test_roi_positive():
    """TEST 6: ROI calculation positive."""
    margin = Decimal("176.80")
    pnl = Decimal("442.99")

    roi = calculate_roi(pnl, margin)
    # Expected: (442.99 / 176.80) * 100 = 250.56%
    assert round(roi, 2) == Decimal("250.56")


def test_roi_negative():
    """ROI calculation negative."""
    margin = Decimal("200.00")
    pnl = Decimal("-50.00")

    roi = calculate_roi(pnl, margin)
    # Expected: (-50 / 200) * 100 = -25.00%
    assert roi == Decimal("-25.00")


def test_roi_zero():
    """ROI calculation zero."""
    margin = Decimal("500.00")
    pnl = Decimal("0")

    roi = calculate_roi(pnl, margin)
    assert roi == Decimal("0")


def test_roi_invalid_margin():
    """ROI calculation with zero or negative margin raises ValueError."""
    with pytest.raises(ValueError):
        calculate_roi(Decimal("10"), Decimal("0"))

    with pytest.raises(ValueError):
        calculate_roi(Decimal("10"), Decimal("-100"))
