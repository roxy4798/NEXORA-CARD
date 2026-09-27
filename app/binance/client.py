"""Async client for Binance USD(S)-M Futures public market-data endpoints."""

from decimal import Decimal
import logging
from typing import Optional
import httpx

from app.config import settings
from app.binance.exchange_info import ExchangeInfoManager, SymbolInfo

logger = logging.getLogger(__name__)


class BinanceMarketDataClient:
    """Read-only client for Binance Futures public market data."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        exchange_info_mgr: Optional[ExchangeInfoManager] = None,
    ):
        self.base_url = (base_url or settings.binance_base_url).rstrip("/")
        self.timeout = timeout
        self.exchange_info = exchange_info_mgr or ExchangeInfoManager()

    async def init_exchange_info(self, use_fallback_on_error: bool = True) -> None:
        """Loads exchange info from Binance or populates fallback defaults."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/fapi/v1/exchangeInfo"
                logger.info(f"Fetching Binance exchange info from {url}...")
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                self.exchange_info.parse_exchange_info(data)
        except Exception as e:
            logger.warning(f"Failed to fetch Binance exchange info: {e}")
            if use_fallback_on_error:
                self.exchange_info.populate_fallback_defaults()
            else:
                raise

    async def get_mark_price(self, symbol: str, mock_fallback: Optional[Decimal] = None) -> Decimal:
        """Retrieves real-time Mark Price from GET /fapi/v1/premiumIndex."""
        mark, _ = await self.get_mark_price_and_funding(symbol, mock_fallback=mock_fallback)
        return mark

    async def get_mark_price_and_funding(
        self,
        symbol: str,
        mock_fallback: Optional[Decimal] = None,
        mock_funding_rate: Optional[Decimal] = None,
    ) -> tuple[Decimal, Decimal]:
        """Retrieves real-time Mark Price AND lastFundingRate from GET /fapi/v1/premiumIndex.

        Returns:
            (mark_price, funding_rate) — both as Decimal.
            funding_rate is the last settled 8h funding rate (e.g. 0.00005 = 0.005%).
        """
        clean_symbol = symbol.strip().upper()
        url = f"{self.base_url}/fapi/v1/premiumIndex"
        params = {"symbol": clean_symbol}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Fetching mark price + funding rate for {clean_symbol}...")
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                raw_mark = data.get("markPrice")
                raw_rate = data.get("lastFundingRate", "0")
                if not raw_mark:
                    raise ValueError(f"Missing markPrice in response: {data}")
                mark_decimal = Decimal(str(raw_mark))
                rate_decimal = Decimal(str(raw_rate)) if raw_rate else Decimal("0")
                logger.info(f"Retrieved mark={mark_decimal}, fundingRate={rate_decimal} for {clean_symbol}")
                return mark_decimal, rate_decimal
        except Exception as e:
            logger.warning(f"Error fetching premiumIndex for {clean_symbol}: {e}")
            if mock_fallback is not None:
                logger.info(f"Using mock fallback: mark={mock_fallback}, rate={mock_funding_rate or 0}")
                return mock_fallback, (mock_funding_rate or Decimal("0"))
            raise RuntimeError(f"Gagal mengambil live Mark Price untuk {clean_symbol} dari Binance Futures API ({e}).")

