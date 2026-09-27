"""Binance Futures fee and funding fee calculation matching real exchange behavior.

Binance Futures Realized PNL for an open position consists of:
  1. Opening commission  : position_size × taker_fee (0.05%)
  2. Funding fees        : position_size × lastFundingRate (per 8h period)
     - LONG, rate > 0   → LONG pays SHORT  → negative for LONG
     - LONG, rate < 0   → LONG receives    → positive for LONG
     - SHORT, rate > 0  → SHORT receives   → positive for SHORT
     - SHORT, rate < 0  → SHORT pays       → negative for SHORT

Realized PNL = -(opening_commission) + funding_pnl
"""

from decimal import Decimal
from app.simulation.models import Side

# Binance standard taker fee for USD(S)-M Futures (market orders)
BINANCE_TAKER_FEE = Decimal("0.0005")   # 0.05%
BINANCE_MAKER_FEE = Decimal("0.0002")   # 0.02%


def calculate_opening_commission(
    position_size: Decimal,
    fee_rate: Decimal = BINANCE_TAKER_FEE,
) -> Decimal:
    """Returns the opening commission as a positive amount (cost to the trader).

    Commission = position_size × fee_rate
    Always positive — caller decides the sign when applying to realized PNL.
    """
    return (position_size * fee_rate).quantize(Decimal("0.01"))


def calculate_funding_fee(
    position_size: Decimal,
    funding_rate: Decimal,
    side: Side,
) -> Decimal:
    """Returns the net funding fee impact on realized PNL for the given side.

    Positive result  → trader RECEIVES funding (adds to realized PNL)
    Negative result  → trader PAYS funding (reduces realized PNL)

    Binance convention:
      - fundingRate > 0: LONG pays SHORT
      - fundingRate < 0: SHORT pays LONG
    """
    funding_amount = position_size * funding_rate
    if side == Side.LONG:
        # LONG pays when rate > 0, receives when rate < 0
        return -(funding_amount).quantize(Decimal("0.000001"))
    else:
        # SHORT receives when rate > 0, pays when rate < 0
        return funding_amount.quantize(Decimal("0.000001"))


def calculate_realized_pnl(
    position_size: Decimal,
    side: Side,
    funding_rate: Decimal,
    fee_rate: Decimal = BINANCE_TAKER_FEE,
    funding_periods: int = 1,
) -> Decimal:
    """Calculates Realized PNL for an open position, matching Binance Futures display.

    Args:
        position_size:   Notional size in USDT (margin × leverage)
        side:            LONG or SHORT
        funding_rate:    lastFundingRate from Binance /fapi/v1/premiumIndex
        fee_rate:        Commission rate (default: taker 0.05%)
        funding_periods: Number of 8h funding periods elapsed (default 1 = just opened)

    Returns:
        Realized PNL in USDT (negative = cost, positive = income)
    """
    commission = calculate_opening_commission(position_size, fee_rate)
    funding_pnl = calculate_funding_fee(position_size, funding_rate, side) * funding_periods

    realized = -commission + funding_pnl
    return realized.quantize(Decimal("0.01"))
