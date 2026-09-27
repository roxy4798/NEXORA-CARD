"""Future extension interface for Market Scanner (pump/dump detection)."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal


class ScanResult(BaseModel):
    """Placeholder model for scanner candidate results."""
    symbol: str
    price_change_percent_24h: Decimal
    volume_24h: Decimal
    volume_spike_ratio: Optional[Decimal] = None
    momentum_score: Optional[Decimal] = None


class MarketScanner(ABC):
    """Abstract interface prepared for future pump/dump scanning extensions.

    Kept strictly separate from the position simulator core per design spec.
    """

    @abstractmethod
    async def scan_market(self, min_volume: Decimal, min_change_percent: Decimal) -> List[ScanResult]:
        """Scans Binance Futures market for volatility or momentum spikes."""
        pass
