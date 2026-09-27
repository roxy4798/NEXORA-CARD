"""Comprehensive audit script for all edge cases."""
from decimal import Decimal
from app.simulation.precision import format_price_by_tick, get_decimal_places, to_decimal, quantize_tick

print("=== AUDIT 6: Precision / formatting edge cases ===")
cases = [
    (Decimal("84059.0"),    Decimal("0.1"),       "84,059.0"),
    (Decimal("84506.90"),   Decimal("0.1"),       "84,506.9"),
    (Decimal("0.1912999"),  Decimal("0.0001"),    "0.1913"),
    (Decimal("1234567.1"),  Decimal("0.1"),       "1,234,567.1"),
    (Decimal("0.00012345"), Decimal("0.0000001"), "0.0001235"),
    (Decimal("100.00"),     Decimal("0.01"),      "100.00"),
    (Decimal("1000.00"),    Decimal("0.01"),      "1,000.00"),
]
for val, tick, expected in cases:
    result = format_price_by_tick(val, tick)
    status = "OK" if result == expected else f"FAIL (expected {expected})"
    print(f"  {str(val):>14} tick={str(tick):>12} -> {result:>16}  {status}")

print()
print("=== AUDIT 7: to_decimal parsing edge cases ===")
parse_cases = [
    ("100",      Decimal("100")),
    ("100.5",    Decimal("100.5")),
    ("1,000.50", Decimal("1000.50")),
    ("1.5e2",    Decimal("150")),
]
for raw, expected in parse_cases:
    try:
        result = to_decimal(raw)
        ok = abs(result - expected) < Decimal("0.0001")
        print(f"  to_decimal({raw!r:>12}) = {result}  {'OK' if ok else 'FAIL'}")
    except Exception as e:
        print(f"  to_decimal({raw!r:>12}) EXCEPTION: {e}")

print()
print("=== AUDIT 8: liq_price_formatted edge cases ===")
from app.simulation.models import Side, PositionResult
from datetime import datetime, timezone

def make_r(**kw):
    defaults = dict(
        symbol="BTCUSDT", side=Side.LONG,
        entry_price=Decimal("100"), leverage=Decimal("10"),
        margin=Decimal("100"), margin_ratio=Decimal("5"),
        mark_price=Decimal("100"), position_size=Decimal("1000"),
        pnl=Decimal("0"), roi=Decimal("0"),
        liquidation_price=Decimal("50"),
        realized_pnl=Decimal("-0.05"),
        tick_size=Decimal("0.01"), step_size=Decimal("0.001"),
        mode="MOCK",
    )
    defaults.update(kw)
    return PositionResult(**defaults)

liq_cases = [
    (make_r(liquidation_price=Decimal("0"),    tick_size=Decimal("0.01")),  "--"),
    (make_r(liquidation_price=Decimal("0.009"),tick_size=Decimal("0.01")),  "--"),  # below tick
    (make_r(liquidation_price=Decimal("81386.9"),  tick_size=Decimal("0.1")),  "81,386.9"),
    (make_r(liquidation_price=Decimal("1000.00"), tick_size=Decimal("0.01")),  "1,000.00"),
    (make_r(liquidation_price=Decimal("0.5258"), tick_size=Decimal("0.0001")), "0.5258"),
    (make_r(liquidation_price=Decimal("86731.1"), tick_size=Decimal("0.1")),   "86,731.1"),
]
for r, expected in liq_cases:
    result = r.liq_price_formatted
    status = "OK" if result == expected else f"FAIL (expected {expected!r})"
    print(f"  liq={r.liquidation_price} tick={r.tick_size} -> {result!r:>14}  {status}")

print()
print("=== AUDIT 9: keyboards.py parse_ef_callback ===")
from app.bot.keyboards import parse_ef_callback, get_edit_fields_keyboard

tests = [
    ("ef_sim_A|symbol",      ("sim_A", "symbol")),
    ("ef_sim_A|side",        ("sim_A", "side")),
    ("ef_sim_A|marginratio", ("sim_A", "marginratio")),
    ("ef_ab12cd34|leverage", ("ab12cd34", "leverage")),
    ("ef_my_sim_1|entry",    ("my_sim_1", "entry")),  # sim_id with underscores
]
for cb_data, expected in tests:
    result = parse_ef_callback(cb_data)
    status = "OK" if result == expected else f"FAIL (expected {expected})"
    print(f"  parse({cb_data!r:>30}) -> {result}  {status}")

print()
print("=== AUDIT 10: Side badge colors ===")
from app.renderer.theme import THEME
print(f"  LONG badge color (should be green-ish): {THEME.badge_long_bg}")
print(f"  SHORT badge color (should be red-ish):  {THEME.badge_short_bg}")
assert THEME.badge_long_bg[1] > THEME.badge_long_bg[0], "LONG badge should be green dominant"
assert THEME.badge_short_bg[0] > THEME.badge_short_bg[1], "SHORT badge should be red dominant"
print("  Badge color assertions: OK")
