"""Unit tests for simulated liquidation price calculations."""

from decimal import Decimal
import pytest
from app.simulation.models import Side
from app.simulation.liquidation import calculate_simulated_liquidation


def test_liquidation_wusdt_reference():
    """Verify liquidation price exactly produces 0.0106400 for the reference scenario."""
    entry_price = Decimal("0.0140000")
    leverage = Decimal("20")
    margin_ratio = Decimal("8.29")
    tick_size = Decimal("0.0000001")

    liq = calculate_simulated_liquidation(Side.LONG, entry_price, leverage, margin_ratio, tick_size)
    assert liq == Decimal("0.0106400")


def test_liquidation_short_reference():
    """Verify SHORT liquidation is symmetric and strictly above entry price."""
    entry_price = Decimal("0.0140000")
    leverage = Decimal("20")
    margin_ratio = Decimal("8.29")
    tick_size = Decimal("0.0000001")

    liq = calculate_simulated_liquidation(Side.SHORT, entry_price, leverage, margin_ratio, tick_size)
    # Expected: 0.0140000 * (1 + 0.24) = 0.0173600
    assert liq == Decimal("0.0173600")
    assert liq > entry_price


def test_liquidation_different_margin_ratios():
    """Higher Margin Ratio brings liquidation closer to Entry Price."""
    entry_price = Decimal("100.00")
    leverage = Decimal("20")
    tick_size = Decimal("0.01")

    # Low MR: large buffer
    liq_low = calculate_simulated_liquidation(Side.LONG, entry_price, leverage, Decimal("5.0"), tick_size)
    # High MR: small buffer
    liq_high = calculate_simulated_liquidation(Side.LONG, entry_price, leverage, Decimal("50.0"), tick_size)

    assert liq_low < liq_high < entry_price


def test_liquidation_different_leverages():
    """Higher leverage reduces buffer, bringing liquidation closer to Entry."""
    entry_price = Decimal("100.00")
    margin_ratio = Decimal("10.0")
    tick_size = Decimal("0.01")

    liq_10x = calculate_simulated_liquidation(Side.LONG, entry_price, Decimal("10"), margin_ratio, tick_size)
    liq_50x = calculate_simulated_liquidation(Side.LONG, entry_price, Decimal("50"), margin_ratio, tick_size)

    assert liq_10x < liq_50x < entry_price


def test_liquidation_at_100_percent():
    """At 100% Margin Ratio, liquidation price equals entry price."""
    entry_price = Decimal("50.00")
    tick_size = Decimal("0.01")

    liq_long = calculate_simulated_liquidation(Side.LONG, entry_price, Decimal("20"), Decimal("100"), tick_size)
    liq_short = calculate_simulated_liquidation(Side.SHORT, entry_price, Decimal("20"), Decimal("100"), tick_size)

    assert liq_long == entry_price
    assert liq_short == entry_price


def test_liquidation_long_non_negative_clamp():
    """LONG liquidation must never be negative or zero."""
    entry_price = Decimal("0.01")
    leverage = Decimal("1")
    margin_ratio = Decimal("0.01")
    tick_size = Decimal("0.0001")

    liq = calculate_simulated_liquidation(Side.LONG, entry_price, leverage, margin_ratio, tick_size)
    assert liq > Decimal("0")
    assert liq == tick_size


def test_liquidation_invalid_inputs():
    """Validation errors for bad inputs."""
    with pytest.raises(ValueError):
        calculate_simulated_liquidation(Side.LONG, Decimal("-10"), Decimal("10"), Decimal("5"))

    with pytest.raises(ValueError):
        calculate_simulated_liquidation(Side.LONG, Decimal("100"), Decimal("0"), Decimal("5"))

    with pytest.raises(ValueError):
        calculate_simulated_liquidation(Side.LONG, Decimal("100"), Decimal("10"), Decimal("105"))


def test_liquidation_fartcoin_unreachable_displays_dashes():
    """Verify FARTCOINUSDT Long 3x MR 7.64% mathematically produces '--' unreachable liquidation.

    Audit breakdown:
    1. MMR = 0.433889434 / 3 = 0.1446298... (14.46%)
    2. Buffer multiplier = (100 - 7.64) / 7.64 = 12.089005...
    3. Adverse price fraction = MMR * Multiplier = 1.7484305... (174.84% drop required)
    4. Raw liquidation price = 0.1912999 * (1 - 1.7484305) = -0.14317... < 0
    5. Since price cannot drop below 0 (negative price is impossible in spot/futures),
       liquidation is unreachable and clamped to tick_size, formatting deterministically as '--'.
    """
    from app.simulation.calculator import calculate_position
    from app.simulation.models import PositionInput

    entry_price = Decimal("0.1912999")
    leverage = Decimal("3")
    margin = Decimal("5.17")
    margin_ratio = Decimal("7.64")
    tick_size = Decimal("0.0001000")
    step_size = Decimal("0.1")

    # 1. Calculator level
    liq_raw = calculate_simulated_liquidation(Side.LONG, entry_price, leverage, margin_ratio, tick_size)
    assert liq_raw == tick_size  # Clamped to tick_size because raw price < 0

    # 2. PositionResult model level
    pos_input = PositionInput(
        symbol="FARTCOINUSDT",
        side=Side.LONG,
        entry_price=entry_price,
        leverage=leverage,
        margin=margin,
        margin_ratio=margin_ratio,
        mode="LIVE",
    )
    result = calculate_position(pos_input, mark_price=Decimal("0.19420349"), tick_size=tick_size, step_size=step_size)

    assert result.liquidation_price == tick_size
    assert result.liq_price_formatted == "--"
