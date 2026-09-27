"""Lightweight atomic JSON persistence store for simulated positions across bot restarts."""

from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.simulation.models import Side, PositionInput, PositionResult
from app.binance.exchange_info import SymbolInfo

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "positions.json"


class PositionStore:
    """Atomic JSON storage for active simulated positions."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or DEFAULT_STORAGE_FILE
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_position(
        self,
        sim_id: str,
        input_data: PositionInput,
        result: PositionResult,
        symbol_info: SymbolInfo,
    ) -> None:
        """Saves or updates a position atomically to the JSON store."""
        data = self.load_raw()
        data[sim_id] = {
            "input": {
                "symbol": input_data.symbol,
                "side": input_data.side.value,
                "entry_price": str(input_data.entry_price),
                "leverage": str(input_data.leverage),
                "margin": str(input_data.margin),
                "margin_ratio": str(input_data.margin_ratio),
                "realized_pnl": str(input_data.realized_pnl),
                "mode": input_data.mode,
            },
            "result": {
                "simulation_id": result.simulation_id,
                "symbol": result.symbol,
                "side": result.side.value,
                "entry_price": str(result.entry_price),
                "leverage": str(result.leverage),
                "margin": str(result.margin),
                "margin_ratio": str(result.margin_ratio),
                "mark_price": str(result.mark_price),
                "position_size": str(result.position_size),
                "pnl": str(result.pnl),
                "roi": str(result.roi),
                "liquidation_price": str(result.liquidation_price),
                "realized_pnl": str(result.realized_pnl),
                "tick_size": str(result.tick_size),
                "step_size": str(result.step_size),
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat(),
                "mode": result.mode,
            },
            "symbol_info": {
                "symbol": symbol_info.symbol,
                "status": symbol_info.status,
                "base_asset": symbol_info.base_asset,
                "quote_asset": symbol_info.quote_asset,
                "tick_size": str(symbol_info.tick_size),
                "step_size": str(symbol_info.step_size),
                "price_precision": symbol_info.price_precision,
                "quantity_precision": symbol_info.quantity_precision,
                "min_qty": str(symbol_info.min_qty),
                "min_notional": str(symbol_info.min_notional),
            },
        }
        self.write_raw(data)

    def delete_position(self, sim_id: str) -> bool:
        """Deletes a position by simulation ID from storage."""
        data = self.load_raw()
        if sim_id in data:
            del data[sim_id]
            self.write_raw(data)
            return True
        return False

    def load_all_positions(self) -> Dict[str, dict]:
        """Loads and reconstructs all positions from the JSON store."""
        raw_data = self.load_raw()
        positions: Dict[str, dict] = {}

        for sim_id, item in raw_data.items():
            try:
                inp_dict = item["input"]
                res_dict = item["result"]
                sym_dict = item["symbol_info"]

                pos_input = PositionInput(
                    symbol=inp_dict["symbol"],
                    side=Side(inp_dict["side"]),
                    entry_price=Decimal(inp_dict["entry_price"]),
                    leverage=Decimal(inp_dict["leverage"]),
                    margin=Decimal(inp_dict["margin"]),
                    margin_ratio=Decimal(inp_dict["margin_ratio"]),
                    realized_pnl=Decimal(inp_dict.get("realized_pnl", "-0.04")),
                    mode=inp_dict.get("mode", "LIVE"),
                )

                created_at = datetime.fromisoformat(res_dict["created_at"])
                updated_at = datetime.fromisoformat(res_dict["updated_at"])

                pos_result = PositionResult(
                    simulation_id=res_dict.get("simulation_id", sim_id),
                    symbol=res_dict["symbol"],
                    side=Side(res_dict["side"]),
                    entry_price=Decimal(res_dict["entry_price"]),
                    leverage=Decimal(res_dict["leverage"]),
                    margin=Decimal(res_dict["margin"]),
                    margin_ratio=Decimal(res_dict["margin_ratio"]),
                    mark_price=Decimal(res_dict["mark_price"]),
                    position_size=Decimal(res_dict["position_size"]),
                    pnl=Decimal(res_dict["pnl"]),
                    roi=Decimal(res_dict["roi"]),
                    liquidation_price=Decimal(res_dict["liquidation_price"]),
                    realized_pnl=Decimal(res_dict.get("realized_pnl", "-0.04")),
                    tick_size=Decimal(res_dict["tick_size"]),
                    step_size=Decimal(res_dict["step_size"]),
                    created_at=created_at,
                    updated_at=updated_at,
                    mode=res_dict.get("mode", "LIVE"),
                )

                symbol_info = SymbolInfo(
                    symbol=sym_dict["symbol"],
                    status=sym_dict["status"],
                    base_asset=sym_dict.get("base_asset", ""),
                    quote_asset=sym_dict.get("quote_asset", ""),
                    tick_size=Decimal(sym_dict["tick_size"]),
                    step_size=Decimal(sym_dict["step_size"]),
                    price_precision=sym_dict.get("price_precision", 8),
                    quantity_precision=sym_dict.get("quantity_precision", 0),
                    min_qty=Decimal(sym_dict.get("min_qty", "0.001")),
                    min_notional=Decimal(sym_dict.get("min_notional", "5")),
                )

                positions[sim_id] = {
                    "input": pos_input,
                    "result": pos_result,
                    "symbol_info": symbol_info,
                }
            except Exception as e:
                logger.error(f"Error restoring position {sim_id}: {e}", exc_info=True)

        return positions

    def load_raw(self) -> Dict[str, Any]:
        """Reads raw JSON file dictionary."""
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read positions file {self.file_path}: {e}")
            return {}

    def write_raw(self, data: Dict[str, Any]) -> None:
        """Writes dictionary to file atomically."""
        tmp_file = self.file_path.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(self.file_path)
        except Exception as e:
            logger.error(f"Failed to write positions file {self.file_path}: {e}", exc_info=True)
            if tmp_file.exists():
                tmp_file.unlink()
