"""Application entrypoint for Telegram Bot and local test runner."""

import argparse
from decimal import Decimal
import logging
import sys

from app.config import settings
from app.logging_config import setup_logging
from app.simulation.models import Side, PositionInput
from app.simulation.calculator import calculate_position
from app.binance.exchange_info import ExchangeInfoManager
from app.renderer.position_card import PositionCardRenderer
from app.bot.bot_app import create_telegram_application

logger = logging.getLogger(__name__)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def run_demo(
    symbol: str = "WUSDT",
    side: str = "LONG",
    entry: str = "0.0140000",
    leverage: str = "20",
    margin: str = "176.80",
    margin_ratio: str = "8.29",
    realized_pnl: str = "0.00",
) -> None:
    """Runs a local simulation demo without needing a Telegram connection."""
    print("=" * 60)
    print("[DEMO] RUNNING PAPER POSITION GENERATOR LOCAL DEMO")
    print("=" * 60)

    mgr = ExchangeInfoManager()
    mgr.populate_fallback_defaults()
    sym_info = mgr.get_symbol_info(symbol) or mgr.get_symbol_info("WUSDT")

    pos_input = PositionInput(
        symbol=symbol,
        side=Side(side.upper()),
        entry_price=Decimal(entry),
        leverage=Decimal(leverage),
        margin=Decimal(margin),
        margin_ratio=Decimal(margin_ratio),
        realized_pnl=Decimal(realized_pnl),
        mode="MOCK",
    )

    mock_mark = Decimal("0.0157539")
    result = calculate_position(
        input_data=pos_input,
        mark_price=mock_mark,
        tick_size=sym_info.tick_size,
        step_size=sym_info.step_size,
    )

    print(f"Symbol:           {result.symbol}")
    print(f"Side:             {result.side.value}")
    print(f"Entry Price:      {result.entry_price}")
    print(f"Leverage:         {result.leverage}X")
    print(f"Margin:           {result.margin_formatted} USDT")
    print(f"Margin Ratio:     {result.margin_ratio_formatted}")
    print(f"Mark Price:       {result.mark_price}")
    print(f"Position Size:    {result.size_formatted} USDT")
    print(f"Unrealized PNL:   {result.pnl_formatted} USDT")
    print(f"ROI:              {result.roi_formatted}")
    print(f"Liq. Price:       {result.liq_price_formatted}")
    print(f"Realized PNL:     {result.realized_pnl_formatted} USDT")

    renderer = PositionCardRenderer(mode="PRODUCTION")
    png_bytes = renderer.render_to_bytes(result)

    out_file = "output/demo_position_card.png"
    with open(out_file, "wb") as f:
        f.write(png_bytes)

    print(f"[SUCCESS] Generated sample position card saved to: {out_file}")
    print("=" * 60)


def main() -> None:
    """Starts the application."""
    parser = argparse.ArgumentParser(description="Binance Futures Paper Position Generator")
    parser.add_argument("--demo", action="store_true", help="Run local simulation and render demo image")
    args = parser.parse_args()

    setup_logging(settings.log_level)

    if args.demo or not settings.telegram_bot_token:
        if not settings.telegram_bot_token:
            logger.info("No TELEGRAM_BOT_TOKEN found in environment. Running local demo mode.")
        run_demo()
        return

    logger.info("Starting Telegram Bot polling...")
    app = create_telegram_application()
    app.run_polling()


if __name__ == "__main__":
    main()
