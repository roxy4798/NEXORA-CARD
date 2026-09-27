"""Decimal arithmetic, rounding, and tick-size quantization utilities."""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union


def to_decimal(value: Union[str, int, float, Decimal]) -> Decimal:
    """Safely converts value to Decimal without binary floating-point inaccuracy.

    Accepts comma-formatted numbers (e.g. '1,000.50') by stripping commas first.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    try:
        # Strip commas (thousands separator) before parsing
        clean = str(value).strip().replace(",", "")
        return Decimal(clean)
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError(f"Cannot convert '{value}' to Decimal: {e}") from e


def get_decimal_places(step: Decimal) -> int:
    """Calculates number of decimal places for a tick or step size."""
    # Normalize step, e.g. 0.000100 -> 0.0001
    normalized = step.normalize()
    sign, digits, exponent = normalized.as_tuple()
    if exponent >= 0:
        return 0
    return -exponent


def quantize_tick(value: Decimal, tick_size: Decimal) -> Decimal:
    """Quantizes a Decimal value to the exact multiple of tick_size using ROUND_HALF_UP."""
    if tick_size <= Decimal("0"):
        raise ValueError("tick_size must be positive")
    
    # Calculate remainder to round to nearest step
    quotient = (value / tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return quotient * tick_size


def format_price_by_tick(price: Decimal, tick_size: Decimal) -> str:
    """Formats a price string matching the decimal precision of its tick size with thousands comma separator."""
    places = get_decimal_places(tick_size)
    quantized = quantize_tick(price, tick_size)
    if places == 0:
        return f"{int(quantized):,}"
    # Format with exact places and commas for thousands/millions
    fmt = f"{{:,.{places}f}}"
    return fmt.format(quantized)


def safe_divide(numerator: Decimal, denominator: Decimal, default: Decimal = Decimal("0")) -> Decimal:
    """Safely divides two Decimals, returning default if denominator is zero."""
    if denominator == Decimal("0"):
        return default
    return numerator / denominator
