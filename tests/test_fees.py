"""Tests for Binance fee and funding fee calculation in simulation/fees.py."""

from decimal import Decimal
import pytest
from app.simulation.models import Side
from app.simulation.fees import (
    BINANCE_TAKER_FEE,
    BINANCE_MAKER_FEE,
    calculate_opening_commission,
    calculate_funding_fee,
    calculate_realized_pnl,
)


class TestOpeningCommission:
    def test_taker_fee_default(self):
        """Taker fee = 0.05% of position size."""
        comm = calculate_opening_commission(Decimal("10000"))
        assert comm == Decimal("5.00")

    def test_maker_fee(self):
        """Maker fee = 0.02% of position size."""
        comm = calculate_opening_commission(Decimal("10000"), BINANCE_MAKER_FEE)
        assert comm == Decimal("2.00")

    def test_small_position_rounds_to_cent(self):
        """Very small position rounds commission to nearest cent."""
        comm = calculate_opening_commission(Decimal("15.51"))
        assert comm == Decimal("0.01")

    def test_large_btc_position(self):
        """BTC 100x: margin 15079.93 -> size 1507993 -> fee 754.00 (0.05%)."""
        size = Decimal("15079.93") * Decimal("100")
        comm = calculate_opening_commission(size)
        assert comm == Decimal("754.00")

    def test_commission_always_positive(self):
        """Opening commission is always a positive amount (cost)."""
        comm = calculate_opening_commission(Decimal("50000"))
        assert comm > 0


class TestFundingFee:
    def test_long_positive_rate_pays(self):
        """LONG pays when funding rate is positive (negative impact on PNL)."""
        fee = calculate_funding_fee(Decimal("10000"), Decimal("0.0001"), Side.LONG)
        assert fee < 0  # LONG pays => negative

    def test_long_negative_rate_receives(self):
        """LONG receives when funding rate is negative (positive impact on PNL)."""
        fee = calculate_funding_fee(Decimal("10000"), Decimal("-0.0001"), Side.LONG)
        assert fee > 0  # LONG receives => positive

    def test_short_positive_rate_receives(self):
        """SHORT receives when funding rate is positive (positive impact on PNL)."""
        fee = calculate_funding_fee(Decimal("10000"), Decimal("0.0001"), Side.SHORT)
        assert fee > 0  # SHORT receives => positive

    def test_short_negative_rate_pays(self):
        """SHORT pays when funding rate is negative (negative impact on PNL)."""
        fee = calculate_funding_fee(Decimal("10000"), Decimal("-0.0001"), Side.SHORT)
        assert fee < 0  # SHORT pays => negative

    def test_zero_funding_rate(self):
        """Zero funding rate produces zero fee for both sides."""
        for side in (Side.LONG, Side.SHORT):
            fee = calculate_funding_fee(Decimal("10000"), Decimal("0"), side)
            assert fee == Decimal("0")

    def test_long_short_opposite_sign(self):
        """LONG and SHORT funding fees are exact opposites."""
        size = Decimal("50000")
        rate = Decimal("0.0001")
        fee_long = calculate_funding_fee(size, rate, Side.LONG)
        fee_short = calculate_funding_fee(size, rate, Side.SHORT)
        assert fee_long == -fee_short

    def test_btc_actual_rate(self):
        """BTC realistic: size 1507993, rate 0.00000872."""
        size = Decimal("1507993")
        rate = Decimal("0.00000872")
        fee = calculate_funding_fee(size, rate, Side.LONG)
        # 1507993 * 0.00000872 = 13.149... => negative
        assert fee < 0
        assert abs(fee) < Decimal("15")


class TestCalculateRealizedPnl:
    def test_realized_pnl_long_positive_rate_is_negative(self):
        """LONG with positive funding rate: realized PNL = -(commission + funding)."""
        rpnl = calculate_realized_pnl(
            position_size=Decimal("10000"),
            side=Side.LONG,
            funding_rate=Decimal("0.0001"),
        )
        assert rpnl < 0

    def test_realized_pnl_short_positive_rate_less_negative(self):
        """SHORT with positive funding rate: receives funding, so realized PNL is less negative than LONG."""
        rpnl_long = calculate_realized_pnl(Decimal("10000"), Side.LONG, Decimal("0.0001"))
        rpnl_short = calculate_realized_pnl(Decimal("10000"), Side.SHORT, Decimal("0.0001"))
        # SHORT receives funding, so less negative
        assert rpnl_short > rpnl_long

    def test_realized_pnl_zero_rate_equals_minus_commission(self):
        """Zero funding rate: realized PNL equals exactly -opening_commission."""
        rpnl = calculate_realized_pnl(Decimal("10000"), Side.LONG, Decimal("0"))
        assert rpnl == Decimal("-5.00")  # -10000 * 0.0005

    def test_multiple_funding_periods(self):
        """Multiple funding periods multiply the funding fee linearly."""
        rpnl_1 = calculate_realized_pnl(Decimal("10000"), Side.LONG, Decimal("0.0001"), funding_periods=1)
        rpnl_3 = calculate_realized_pnl(Decimal("10000"), Side.LONG, Decimal("0.0001"), funding_periods=3)
        # 3 periods means more funding paid => more negative
        assert rpnl_3 < rpnl_1

    def test_fartcoin_realistic(self):
        """FARTCOIN LONG 3x 5.17 margin: size=15.51, rate=0.00005."""
        rpnl = calculate_realized_pnl(
            position_size=Decimal("15.51"),
            side=Side.LONG,
            funding_rate=Decimal("0.00005"),
        )
        # commission: 0.01, funding: ~0.00 => ~-0.01
        assert rpnl == Decimal("-0.01")

    def test_btc_realistic(self):
        """BTC LONG 100x 15079.93 margin: size=1507993, rate=0.00000872."""
        size = Decimal("15079.93") * Decimal("100")
        rpnl = calculate_realized_pnl(size, Side.LONG, Decimal("0.00000872"))
        # commission ~753.99, funding ~13.15 => total ~-767
        assert rpnl < Decimal("-760")
        assert rpnl > Decimal("-780")

    def test_result_is_decimal_with_two_places(self):
        """Result is always quantized to 2 decimal places."""
        rpnl = calculate_realized_pnl(Decimal("9999"), Side.SHORT, Decimal("0.00005"))
        # result has max 2 decimal places
        assert rpnl == rpnl.quantize(Decimal("0.01"))
