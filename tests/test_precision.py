"""Unit tests for precision, Decimal parsing, tick-size quantization, and input boundaries."""

from decimal import Decimal
import pytest
from app.simulation.precision import (
    to_decimal,
    quantize_tick,
    format_price_by_tick,
    get_decimal_places,
    safe_divide,
)
from app.simulation.models import PositionInput, Side


def test_decimal_precision():
    """TEST 8: Decimal precision arithmetic avoids floating point errors."""
    d1 = to_decimal("0.1")
    d2 = to_decimal("0.2")
    assert d1 + d2 == Decimal("0.3")

    # High precision crypto tick
    p1 = to_decimal("0.00001234")
    p2 = to_decimal("0.00000006")
    assert p1 + p2 == Decimal("0.00001240")


def test_tick_size_rounding():
    """TEST 9: Tick-size rounding with ROUND_HALF_UP."""
    tick_size = Decimal("0.000001")
    raw_price = Decimal("0.01575394")
    quantized = quantize_tick(raw_price, tick_size)
    assert quantized == Decimal("0.015754")

    # Coarse tick size
    tick_coarse = Decimal("0.5")
    assert quantize_tick(Decimal("10.2"), tick_coarse) == Decimal("10.0")
    assert quantize_tick(Decimal("10.3"), tick_coarse) == Decimal("10.5")


def test_format_price_by_tick():
    """Verify price string formatting respects tick decimals and thousands comma separator."""
    assert format_price_by_tick(Decimal("0.0140000"), Decimal("0.0000001")) == "0.0140000"
    assert format_price_by_tick(Decimal("54321.1234"), Decimal("0.01")) == "54,321.12"
    assert format_price_by_tick(Decimal("123.45"), Decimal("1")) == "123"
    assert format_price_by_tick(Decimal("1507178.02"), Decimal("0.01")) == "1,507,178.02"


def test_invalid_leverage():
    """TEST 11: Invalid leverage boundary checks."""
    with pytest.raises(ValueError):
        PositionInput(
            symbol="BTCUSDT",
            side=Side.LONG,
            entry_price=Decimal("50000"),
            leverage=Decimal("-5"),
            margin=Decimal("100"),
            margin_ratio=Decimal("10"),
        )


def test_invalid_margin():
    """TEST 12: Invalid margin boundary checks."""
    with pytest.raises(ValueError):
        PositionInput(
            symbol="BTCUSDT",
            side=Side.LONG,
            entry_price=Decimal("50000"),
            leverage=Decimal("10"),
            margin=Decimal("-100"),
            margin_ratio=Decimal("10"),
        )


def test_invalid_margin_ratio():
    """TEST 13: Invalid margin ratio boundary checks."""
    with pytest.raises(ValueError):
        PositionInput(
            symbol="BTCUSDT",
            side=Side.LONG,
            entry_price=Decimal("50000"),
            leverage=Decimal("10"),
            margin=Decimal("100"),
            margin_ratio=Decimal("150"),  # > 100%
        )

    with pytest.raises(ValueError):
        PositionInput(
            symbol="BTCUSDT",
            side=Side.LONG,
            entry_price=Decimal("50000"),
            leverage=Decimal("10"),
            margin=Decimal("100"),
            margin_ratio=Decimal("-1"),  # < 0%
        )


def test_thousands_and_millions_comma_formatting():
    """Verify that numbers in thousands and millions include commas matching Binance UI."""
    from app.simulation.models import PositionResult

    pos = PositionResult(
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_price=Decimal("84059.0"),
        leverage=Decimal("100"),
        margin=Decimal("15079.93"),
        margin_ratio=Decimal("12.01"),
        mark_price=Decimal("84506.90"),
        position_size=Decimal("1507178.02"),
        pnl=Decimal("8035.19"),
        roi=Decimal("53.28"),
        liquidation_price=Decimal("24657.16"),
        realized_pnl=Decimal("-814.58"),
        tick_size=Decimal("0.1"),
        step_size=Decimal("0.001"),
    )

    # Check commas in thousands and millions
    assert pos.pnl_formatted == "+8,035.19"
    assert pos.roi_formatted == "+53.28%"
    assert pos.size_formatted == "1,507,178.02"
    assert pos.margin_formatted == "15,079.93"
    assert pos.margin_ratio_formatted == "12.01%"
    assert pos.realized_pnl_formatted == "-814.58"
    assert pos.liq_price_formatted == "24,657.2"   # tick=0.1 -> 1dp, rounded from 24657.16

    # Price formatting
    assert format_price_by_tick(pos.entry_price, pos.tick_size) == "84,059.0"
