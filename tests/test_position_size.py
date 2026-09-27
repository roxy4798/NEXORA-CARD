"""Unit tests for position size calculations."""

from decimal import Decimal
import pytest
from app.simulation.models import Side, PositionInput
from app.simulation.calculator import calculate_position


def test_position_size_standard():
    """Verify position size = margin * leverage using Decimal."""
    margin = Decimal("176.80")
    leverage = Decimal("20")
    expected = Decimal("3536.00")

    pos_size = margin * leverage
    assert pos_size == expected


def test_position_size_fractional_leverage():
    """Verify fractional margin and high leverage."""
    margin = Decimal("50.25")
    leverage = Decimal("50")
    expected = Decimal("2512.50")

    assert margin * leverage == expected


def test_position_size_validation_zero():
    """Verify margin or leverage <= 0 fails validation."""
    with pytest.raises(ValueError):
        PositionInput(
            symbol="BTCUSDT",
            side=Side.LONG,
            entry_price=Decimal("50000"),
            leverage=Decimal("0"),
            margin=Decimal("100"),
            margin_ratio=Decimal("5.0"),
        )
