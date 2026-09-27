"""Security safety test: ensures no trade execution code or order endpoints exist."""

from pathlib import Path
import pytest

FORBIDDEN_PATTERNS = [
    "/fapi/v1/order",
    "/fapi/v1/batchOrders",
    "/fapi/v1/allOpenOrders",
    "/fapi/v1/countdownCancelAll",
    "order creation",
    "create_order",
    "cancel order",
    "cancel_order",
    "place_order",
    "execute_order",
    "account trading endpoints",
    "/fapi/v2/account",
    "/fapi/v2/balance",
]


def test_no_forbidden_trading_endpoints_in_codebase():
    """Recursively scans all python files in app/ to verify zero trade execution logic exists."""
    app_dir = Path(__file__).resolve().parent.parent / "app"
    assert app_dir.exists(), "app directory must exist"

    violations = []

    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in content:
                violations.append(f"{py_file.name}: contains forbidden pattern '{pattern}'")

    assert not violations, f"Safety violations found in codebase: {violations}"
