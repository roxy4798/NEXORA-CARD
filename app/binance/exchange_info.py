"""Binance Futures Exchange Information and Symbol Metadata."""

from decimal import Decimal
import logging
import time
from typing import Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SymbolInfo(BaseModel):
    """Metadata describing symbol filters and precisions."""

    symbol: str
    status: str
    base_asset: str = ""
    quote_asset: str = ""
    tick_size: Decimal
    step_size: Decimal
    price_precision: int = 8
    quantity_precision: int = 0
    min_qty: Decimal = Decimal("0.001")
    min_notional: Decimal = Decimal("5")


class ExchangeInfoManager:
    """Manages cached symbol metadata fetched from Binance USD(S)-M Futures."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        self._symbols: Dict[str, SymbolInfo] = {}
        self._last_updated: float = 0
        self._cache_ttl_seconds = cache_ttl_seconds

    @property
    def is_loaded(self) -> bool:
        return len(self._symbols) > 0 and (time.time() - self._last_updated < self._cache_ttl_seconds)

    def parse_exchange_info(self, data: dict) -> None:
        """Parses Binance GET /fapi/v1/exchangeInfo response."""
        symbols_list = data.get("symbols", [])
        parsed: Dict[str, SymbolInfo] = {}

        for sym in symbols_list:
            symbol_name = sym.get("symbol", "").upper()
            status = sym.get("status", "")
            base_asset = sym.get("baseAsset", "")
            quote_asset = sym.get("quoteAsset", "")
            price_prec = int(sym.get("pricePrecision", 2))
            qty_prec = int(sym.get("quantityPrecision", 2))

            tick_size = Decimal("0.01")
            step_size = Decimal("0.001")

            for f in sym.get("filters", []):
                filter_type = f.get("filterType")
                if filter_type == "PRICE_FILTER":
                    raw_tick = f.get("tickSize")
                    if raw_tick:
                        tick_size = Decimal(str(raw_tick))
                elif filter_type == "LOT_SIZE":
                    raw_step = f.get("stepSize")
                    if raw_step:
                        step_size = Decimal(str(raw_step))

            parsed[symbol_name] = SymbolInfo(
                symbol=symbol_name,
                status=status,
                base_asset=base_asset,
                quote_asset=quote_asset,
                tick_size=tick_size,
                step_size=step_size,
                price_precision=price_prec,
                quantity_precision=qty_prec,
            )

        self._symbols = parsed
        self._last_updated = time.time()
        logger.info(f"Loaded and cached {len(self._symbols)} symbols from Binance ExchangeInfo.")

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Returns SymbolInfo for a given symbol name (case-insensitive)."""
        clean = symbol.strip().upper()
        return self._symbols.get(clean)

    def is_valid_symbol(self, symbol: str) -> bool:
        """Checks if symbol exists and is trading."""
        info = self.get_symbol_info(symbol)
        if not info:
            return False
        return info.status == "TRADING"

    def populate_fallback_defaults(self) -> None:
        """Populates common fallback pairs for offline/mock development."""
        fallbacks = {
            "FARTCOINUSDT": SymbolInfo(
                symbol="FARTCOINUSDT",
                status="TRADING",
                base_asset="FARTCOIN",
                quote_asset="USDT",
                tick_size=Decimal("0.0000001"),
                step_size=Decimal("1"),
                price_precision=7,
                quantity_precision=0,
            ),
            "WUSDT": SymbolInfo(
                symbol="WUSDT",
                status="TRADING",
                base_asset="W",
                quote_asset="USDT",
                tick_size=Decimal("0.0000001"),
                step_size=Decimal("1"),
                price_precision=7,
                quantity_precision=0,
            ),
            "BTCUSDT": SymbolInfo(
                symbol="BTCUSDT",
                status="TRADING",
                base_asset="BTC",
                quote_asset="USDT",
                tick_size=Decimal("0.10"),
                step_size=Decimal("0.001"),
                price_precision=2,
                quantity_precision=3,
            ),
            "ETHUSDT": SymbolInfo(
                symbol="ETHUSDT",
                status="TRADING",
                base_asset="ETH",
                quote_asset="USDT",
                tick_size=Decimal("0.01"),
                step_size=Decimal("0.001"),
                price_precision=2,
                quantity_precision=3,
            ),
            "SOLUSDT": SymbolInfo(
                symbol="SOLUSDT",
                status="TRADING",
                base_asset="SOL",
                quote_asset="USDT",
                tick_size=Decimal("0.01"),
                step_size=Decimal("0.01"),
                price_precision=2,
                quantity_precision=2,
            ),
        }
        self._symbols.update(fallbacks)
        self._last_updated = time.time()
        logger.info("Populated fallback symbols for offline/mock development.")
