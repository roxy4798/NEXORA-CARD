"""WebSocket client for Binance Futures real-time mark price streams."""

import asyncio
from decimal import Decimal
import json
import logging
from typing import Callable, Optional
import websockets

from app.config import settings

logger = logging.getLogger(__name__)


class BinanceWebSocketManager:
    """Manages WebSocket stream for Binance Futures real-time mark price updates."""

    def __init__(self, ws_base_url: Optional[str] = None):
        self.ws_base_url = (ws_base_url or settings.binance_ws_url).rstrip("/")
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._latest_mark_prices: dict[str, Decimal] = {}

    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Returns the latest cached mark price from the live WebSocket stream."""
        return self._latest_mark_prices.get(symbol.strip().upper())

    async def listen_mark_price(
        self,
        symbol: str,
        on_price_update: Optional[Callable[[str, Decimal], None]] = None,
    ) -> None:
        """Connects to <symbol>@markPrice stream and processes live mark price events."""
        clean_symbol = symbol.strip().lower()
        stream_url = f"{self.ws_base_url}/{clean_symbol}@markPrice"
        self._running = True

        logger.info(f"Connecting to Binance Mark Price WebSocket: {stream_url}")

        while self._running:
            try:
                async with websockets.connect(stream_url) as ws:
                    logger.info(f"WebSocket connected for {clean_symbol}")
                    while self._running:
                        message = await ws.recv()
                        data = json.loads(message)
                        raw_price = data.get("p")
                        if raw_price:
                            mark_decimal = Decimal(str(raw_price))
                            sym_upper = symbol.strip().upper()
                            self._latest_mark_prices[sym_upper] = mark_decimal
                            if on_price_update:
                                on_price_update(sym_upper, mark_decimal)
            except asyncio.CancelledError:
                logger.info(f"WebSocket listener for {clean_symbol} cancelled.")
                break
            except Exception as e:
                logger.warning(f"WebSocket error for {clean_symbol}: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)

    def stop(self) -> None:
        """Stops the WebSocket stream."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
