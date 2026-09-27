"""Data models for paper trading simulation."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional
import uuid
from pydantic import BaseModel, Field, field_validator
from app.simulation.precision import format_price_by_tick


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class PositionInput(BaseModel):
    """Input parameters provided by user for paper trading position."""

    model_config = {"validate_assignment": True}

    symbol: str = Field(..., description="Binance Futures symbol, e.g., FARTCOINUSDT")
    side: Side = Field(..., description="Position side LONG or SHORT")
    entry_price: Decimal = Field(..., gt=0, description="Entry price in USDT")
    leverage: Decimal = Field(..., gt=0, description="Leverage multiplier, e.g., 3")
    margin: Decimal = Field(..., gt=0, description="Margin collateral in USDT")
    margin_ratio: Decimal = Field(..., ge=0, le=100, description="Simulated margin ratio in %")
    realized_pnl: Decimal = Field(default=Decimal("-0.04"), description="Simulated realized PNL in USDT")
    mode: Literal["MOCK", "LIVE"] = Field(default="MOCK", description="Operation mode")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Symbol cannot be empty")
        return clean


class PositionResult(BaseModel):
    """Complete computed position state ready for display and rendering."""

    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str
    side: Side
    entry_price: Decimal
    leverage: Decimal
    margin: Decimal
    margin_ratio: Decimal
    mark_price: Decimal
    position_size: Decimal
    pnl: Decimal
    roi: Decimal
    liquidation_price: Decimal
    realized_pnl: Decimal = Decimal("-0.04")
    tick_size: Decimal = Decimal("0.0000001")
    step_size: Decimal = Decimal("0.001")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: Literal["MOCK", "LIVE"] = "MOCK"

    @property
    def is_profit(self) -> bool:
        return self.pnl >= 0

    @property
    def pnl_formatted(self) -> str:
        """Formats PNL with + or - prefix and 2 decimal places with thousands comma."""
        if self.pnl >= 0:
            return f"+{abs(self.pnl):,.2f}"
        return f"{self.pnl:,.2f}"

    @property
    def roi_formatted(self) -> str:
        """Formats ROI with + or - prefix and 2 decimal places with thousands comma and %."""
        if self.roi >= 0:
            return f"+{abs(self.roi):,.2f}%"
        return f"{self.roi:,.2f}%"

    @property
    def size_formatted(self) -> str:
        """Formats position size in USDT with thousands comma."""
        return f"{self.position_size:,.2f}"

    @property
    def margin_formatted(self) -> str:
        """Formats margin in USDT with thousands comma."""
        return f"{self.margin:,.2f}"

    @property
    def margin_ratio_formatted(self) -> str:
        """Formats margin ratio percentage with thousands comma."""
        return f"{self.margin_ratio:,.2f}%"

    @property
    def realized_pnl_formatted(self) -> str:
        """Formats realized PNL with sign and thousands comma."""
        if self.realized_pnl >= 0:
            return f"+{abs(self.realized_pnl):,.2f}"
        return f"{self.realized_pnl:,.2f}"

    @property
    def liq_price_formatted(self) -> str:
        """Formats liquidation price or '--' if unreachable with thousands comma.

        Always uses tick_size precision via format_price_by_tick.
        """
        if self.liquidation_price <= self.tick_size or self.liquidation_price <= Decimal("0"):
            return "--"
        return format_price_by_tick(self.liquidation_price, self.tick_size)
