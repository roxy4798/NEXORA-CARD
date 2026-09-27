"""Acceptance test verifying exact user specification example."""

from decimal import Decimal
from app.simulation.models import Side, PositionInput
from app.simulation.calculator import calculate_position


def test_wusdt_acceptance_scenario():
    """TEST 25: Acceptance test with WUSDT Long scenario.

    Inputs:
        Symbol: WUSDT
        Side: LONG
        Entry: 0.0140000
        Leverage: 20
        Margin: 176.80
        Margin Ratio: 8.29
        Mock Mark Price: 0.0157539
    """
    symbol = "WUSDT"
    side = Side.LONG
    entry_price = Decimal("0.0140000")
    leverage = Decimal("20")
    margin = Decimal("176.80")
    margin_ratio = Decimal("8.29")
    mock_mark_price = Decimal("0.0157539")
    tick_size = Decimal("0.0000001")
    step_size = Decimal("1")

    pos_input = PositionInput(
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        leverage=leverage,
        margin=margin,
        margin_ratio=margin_ratio,
        mode="MOCK",
    )

    res = calculate_position(
        input_data=pos_input,
        mark_price=mock_mark_price,
        tick_size=tick_size,
        step_size=step_size,
    )

    # 1. Expected Position Size: margin * leverage
    expected_size = margin * leverage
    assert expected_size == Decimal("3536.00")
    assert res.position_size == expected_size
    assert res.size_formatted in ["3,536.00", "3,536.0"]

    # 2. Independent formula calculation for PNL:
    # PNL = position_size * ((mark_price - entry_price) / entry_price)
    expected_pnl = expected_size * ((mock_mark_price - entry_price) / entry_price)
    assert res.pnl == expected_pnl
    assert round(res.pnl, 2) == Decimal("442.99")
    assert res.pnl_formatted == "+442.99"

    # 3. Independent formula calculation for ROI:
    # ROI = (PNL / margin) * 100
    expected_roi = (expected_pnl / margin) * Decimal("100")
    assert res.roi == expected_roi
    assert round(res.roi, 2) == Decimal("250.56")
    assert res.roi_formatted == "+250.56%"

    # 4. Simulated Liquidation price must equal 0.0106400
    assert res.liquidation_price == Decimal("0.0106400")
