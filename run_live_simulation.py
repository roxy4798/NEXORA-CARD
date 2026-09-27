import asyncio
from decimal import Decimal
from PIL import Image
from pathlib import Path

from app.binance.client import BinanceMarketDataClient
from app.simulation.models import Side, PositionInput
from app.simulation.calculator import calculate_position
from app.renderer.position_card import PositionCardRenderer


async def main():
    print("=" * 60)
    print("NEXORA POSITION — LIVE END-TO-END SIMULATION")
    print("=" * 60)

    symbol = "FARTCOINUSDT"
    side = Side.LONG
    entry_price = Decimal("0.1912999")
    leverage = Decimal("3")
    margin = Decimal("5.17")
    margin_ratio = Decimal("7.64")

    # 1. Binance Market Data Client
    client = BinanceMarketDataClient()
    print("Initializing Binance Futures exchange info from /fapi/v1/exchangeInfo...")
    await client.init_exchange_info(use_fallback_on_error=True)

    info = client.exchange_info.get_symbol_info(symbol)
    tick_size = info.tick_size if info else Decimal("0.0000001")
    step_size = info.step_size if info else Decimal("1")
    print(f"Symbol info loaded: tick_size={tick_size}, step_size={step_size}")

    # 2. Fetch live Mark Price
    mark_endpoint = f"{client.base_url}/fapi/v1/premiumIndex?symbol={symbol}"
    print(f"Fetching live Mark Price from endpoint: {mark_endpoint} ...")
    mark_price = await client.get_mark_price(symbol)
    print(f"Retrieved real-time Mark Price: {mark_price}")

    # 3. Calculate position metrics
    pos_input = PositionInput(
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        leverage=leverage,
        margin=margin,
        margin_ratio=margin_ratio,
        mode="LIVE",
    )
    result = calculate_position(pos_input, mark_price=mark_price, tick_size=tick_size, step_size=step_size)

    # 4. Render production PNG
    renderer = PositionCardRenderer(mode="PRODUCTION")
    assert renderer.is_production, "Renderer must be in PRODUCTION mode"

    card_img = renderer.render(result)
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "fartcoin_production_live.png"
    card_img.save(out_path)

    print("\n" + "=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)
    print(f"Symbol:                   {result.symbol}")
    print(f"Side:                     {result.side.value}")
    print(f"Leverage:                 {result.leverage}x")
    print(f"Margin:                   {result.margin_formatted} USDT")
    print(f"Margin Ratio:             {result.margin_ratio_formatted}")
    print(f"Entry Price:              {result.entry_price}")
    print(f"Mark Price:               {result.mark_price}")
    print(f"Position Size:            {result.size_formatted} USDT")
    print(f"Unrealized PNL:           {result.pnl_formatted} USDT")
    print(f"ROI:                      {result.roi_formatted}")
    print(f"Simulated Liq. Price:     {result.liq_price_formatted}")
    print(f"Realized PNL:             {result.realized_pnl_formatted} USDT")
    print(f"Output PNG Canvas:        {card_img.size}")
    print(f"Output PNG Saved To:      {out_path.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
