"""Unit tests for unrealized PNL calculations."""

from decimal import Decimal
import pytest
from app.simulation.models import Side
from app.simulation.pnl import calculate_pnl


def test_long_pnl_positive():
    """TEST 1: LONG PNL positive when mark > entry."""
    position_size = Decimal("3536.00")
    entry_price = Decimal("0.0140000")
    mark_price = Decimal("0.0157539")

    # Formula: 3536.00 * ((0.0157539 - 0.0140000) / 0.0140000)
    pnl = calculate_pnl(Side.LONG, position_size, entry_price, mark_price)

    expected = position_size * ((mark_price - entry_price) / entry_price)
    assert pnl > Decimal("0")
    assert pnl == expected
    assert round(pnl, 2) == Decimal("442.99")


def test_long_pnl_negative():
    """TEST 2: LONG PNL negative when mark < entry."""
    position_size = Decimal("1000.00")
    entry_price = Decimal("100.00")
    mark_price = Decimal("90.00")

    pnl = calculate_pnl(Side.LONG, position_size, entry_price, mark_price)

    # 1000 * ((90 - 100) / 100) = 1000 * (-0.10) = -100
    assert pnl == Decimal("-100.00")
    assert pnl < Decimal("0")


def test_short_pnl_positive():
    """TEST 3: SHORT PNL positive when mark < entry."""
    position_size = Decimal("2000.00")
    entry_price = Decimal("50.00")
    mark_price = Decimal("40.00")

    pnl = calculate_pnl(Side.SHORT, position_size, entry_price, mark_price)

    # 2000 * ((50 - 40) / 50) = 2000 * 0.20 = 400
    assert pnl == Decimal("400.00")
    assert pnl > Decimal("0")


def test_short_pnl_negative():
    """TEST 4: SHORT PNL negative when mark > entry."""
    position_size = Decimal("2000.00")
    entry_price = Decimal("50.00")
    mark_price = Decimal("60.00")

    pnl = calculate_pnl(Side.SHORT, position_size, entry_price, mark_price)

    # 2000 * ((50 - 60) / 50) = 2000 * (-0.20) = -400
    assert pnl == Decimal("-400.00")
    assert pnl < Decimal("0")


def test_zero_pnl_when_mark_equals_entry():
    """TEST 5: Zero PNL when mark == entry for both sides."""
    position_size = Decimal("5000.00")
    price = Decimal("123.456")

    pnl_long = calculate_pnl(Side.LONG, position_size, price, price)
    pnl_short = calculate_pnl(Side.SHORT, position_size, price, price)

    assert pnl_long == Decimal("0")
    assert pnl_short == Decimal("0")
