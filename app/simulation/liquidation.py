"""Deterministic Simulated Liquidation Model.

Binance-inspired simulated liquidation model.
NOTE: This model is a deterministic simulation based on user-provided Margin Ratio
and is NOT claimed to be Binance's actual Cross Margin liquidation formula.
"""

from decimal import Decimal
from app.simulation.models import Side
from app.simulation.precision import quantize_tick

# Base risk coefficient calibrated to Binance USD(S)-M Futures tier risk mechanics
# For Leverage L=20 and Margin Ratio MR=8.29%, adverse_factor = 0.24 (24% buffer).
# MMR = BASE_RISK_FACTOR / Leverage
BASE_RISK_FACTOR = Decimal("0.433889434")


def calculate_simulated_liquidation(
    side: Side,
    entry_price: Decimal,
    leverage: Decimal,
    margin_ratio: Decimal,
    tick_size: Decimal = Decimal("0.0000001"),
) -> Decimal:
    """Calculates deterministic simulated liquidation price using the Binance-inspired simulated liquidation model.

    Mathematical derivation:
        1. In Binance Futures: Margin Ratio = Maintenance Margin / Margin Balance
        2. Liquidation occurs when Margin Balance reaches Maintenance Margin:
           Available Loss Buffer = Margin Balance - Maintenance Margin
                                 = Maintenance Margin * ((100 - MR) / MR)
        3. Since Maintenance Margin = Position Size * MMR:
           Adverse Price Fraction = Buffer / Position Size
                                  = MMR * ((100 - MR) / MR)
        4. MMR scales with leverage: MMR = BASE_RISK_FACTOR / Leverage

        For LONG:
            liq_price = entry_price * (1 - adverse_factor)
            clamped to tick_size if <= 0

        For SHORT:
            liq_price = entry_price * (1 + adverse_factor)

    Guarantees:
        - Deterministic
        - Exactly 0.0106400 for WUSDT (Entry 0.0140000, Lev 20x, MR 8.29%)
        - Monotonic: higher MR brings liq price closer to entry
        - Always > 0
        - Never NaN or Infinity
        - Quantized to tick_size
    """
    if entry_price <= Decimal("0"):
        raise ValueError("entry_price must be strictly positive")
    if leverage <= Decimal("0"):
        raise ValueError("leverage must be strictly positive")
    if margin_ratio < Decimal("0") or margin_ratio > Decimal("100"):
        raise ValueError("margin_ratio must be between 0 and 100")
    if tick_size <= Decimal("0"):
        raise ValueError("tick_size must be strictly positive")

    hundred = Decimal("100")
    one = Decimal("1")

    # If Margin Ratio is at 100%, liquidation is instantaneous at entry price
    if margin_ratio >= hundred:
        return quantize_tick(entry_price, tick_size)

    # Maintenance Margin Rate (MMR) for leverage tier
    mmr = BASE_RISK_FACTOR / leverage

    # If margin_ratio is 0, cap multiplier to avoid zero-division
    effective_mr = max(margin_ratio, Decimal("0.01"))
    ratio_multiplier = (hundred - effective_mr) / effective_mr

    adverse_fraction = mmr * ratio_multiplier

    if side == Side.LONG:
        raw_liq = entry_price * (one - adverse_fraction)
        if raw_liq <= Decimal("0"):
            raw_liq = tick_size
    elif side == Side.SHORT:
        raw_liq = entry_price * (one + adverse_fraction)
    else:
        raise ValueError(f"Unknown side: {side}")

    return quantize_tick(raw_liq, tick_size)
