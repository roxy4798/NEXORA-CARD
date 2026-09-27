"""Unit tests for Binance exchange info and symbol validation."""

from decimal import Decimal
import pytest
from app.binance.exchange_info import ExchangeInfoManager, SymbolInfo


def test_symbol_validation_with_fallback():
    """Verify fallback symbols validate correctly."""
    mgr = ExchangeInfoManager()
    mgr.populate_fallback_defaults()

    assert mgr.is_valid_symbol("WUSDT")
    assert mgr.is_valid_symbol("wusdt")
    assert mgr.is_valid_symbol("BTCUSDT")

    # TEST 10: Invalid symbol
    assert not mgr.is_valid_symbol("NONEXISTENT_COIN_123")


def test_parse_real_exchange_info_structure():
    """Test parsing Binance exchangeInfo response schema."""
    sample_response = {
        "symbols": [
            {
                "symbol": "WUSDT",
                "status": "TRADING",
                "baseAsset": "W",
                "quoteAsset": "USDT",
                "pricePrecision": 7,
                "quantityPrecision": 0,
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "0.0000001",
                        "maxPrice": "100.0000000",
                        "tickSize": "0.0000001",
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "1",
                        "maxQty": "1000000",
                        "stepSize": "1",
                    },
                ],
            }
        ]
    }

    mgr = ExchangeInfoManager()
    mgr.parse_exchange_info(sample_response)

    info = mgr.get_symbol_info("WUSDT")
    assert info is not None
    assert info.symbol == "WUSDT"
    assert info.status == "TRADING"
    assert info.tick_size == Decimal("0.0000001")
    assert info.step_size == Decimal("1")
    assert info.price_precision == 7
