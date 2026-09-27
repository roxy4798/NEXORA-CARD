"""Functional dynamic validation tests for multi-coin rendering, calculations, and bot flow."""

import io
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from PIL import Image
import numpy as np

from app.simulation.models import Side, PositionInput, PositionResult
from app.simulation.calculator import calculate_position
from app.simulation.pnl import calculate_pnl
from app.simulation.roi import calculate_roi
from app.renderer.position_card import PositionCardRenderer
from app.binance.client import BinanceMarketDataClient
from app.bot.states import PositionState
from app.bot.conversation import (
    start_position_live,
    start_position_mock,
    handle_coin,
    handle_side,
    handle_entry_price,
    handle_leverage,
    handle_margin,
    handle_margin_ratio,
)


@pytest.mark.parametrize(
    "symbol,side,entry,mark,leverage,margin,margin_ratio,tick_size,step_size,expected_profit",
    [
        # BTCUSDT: LONG entry below mark (profit)
        ("BTCUSDT", Side.LONG, Decimal("60000.00"), Decimal("63000.00"), Decimal("20"), Decimal("176.80"), Decimal("8.29"), Decimal("0.10"), Decimal("0.001"), True),
        # BTCUSDT: LONG entry above mark (loss)
        ("BTCUSDT", Side.LONG, Decimal("65000.00"), Decimal("63000.00"), Decimal("20"), Decimal("176.80"), Decimal("8.29"), Decimal("0.10"), Decimal("0.001"), False),
        # ETHUSDT: SHORT entry above mark (profit)
        ("ETHUSDT", Side.SHORT, Decimal("3500.00"), Decimal("3300.00"), Decimal("10"), Decimal("50.00"), Decimal("12.50"), Decimal("0.01"), Decimal("0.01"), True),
        # ETHUSDT: SHORT entry below mark (loss)
        ("ETHUSDT", Side.SHORT, Decimal("3200.00"), Decimal("3400.00"), Decimal("10"), Decimal("50.00"), Decimal("12.50"), Decimal("0.01"), Decimal("0.01"), False),
        # SOLUSDT: LONG entry below mark (profit, 3x, 5.17)
        ("SOLUSDT", Side.LONG, Decimal("140.00"), Decimal("154.00"), Decimal("3"), Decimal("5.17"), Decimal("7.64"), Decimal("0.01"), Decimal("0.01"), True),
        # FARTCOINUSDT: LONG with reference-matched parameters
        ("FARTCOINUSDT", Side.LONG, Decimal("0.1912999"), Decimal("0.1980000"), Decimal("3"), Decimal("5.17"), Decimal("7.64"), Decimal("0.0000001"), Decimal("1"), True),
    ],
)
def test_dynamic_symbol_rendering(
    symbol, side, entry, mark, leverage, margin, margin_ratio, tick_size, step_size, expected_profit
):
    """Verify renderer dynamically handles different coins, sides, margins, and leverages."""
    pos_input = PositionInput(
        symbol=symbol,
        side=side,
        entry_price=entry,
        leverage=leverage,
        margin=margin,
        margin_ratio=margin_ratio,
        mode="LIVE",
    )
    result = calculate_position(pos_input, mark, tick_size, step_size)

    # 1. Calculation integrity
    expected_size = margin * leverage
    assert result.position_size == expected_size
    if expected_profit:
        assert result.pnl > Decimal("0")
        assert result.roi > Decimal("0")
        assert result.pnl_formatted.startswith("+")
        assert result.roi_formatted.startswith("+")
    else:
        assert result.pnl < Decimal("0")
        assert result.roi < Decimal("0")
        assert result.pnl_formatted.startswith("-")
        assert result.roi_formatted.startswith("-")

    # 2. Rendering verification
    renderer = PositionCardRenderer(show_watermark=True)
    png_bytes = renderer.render_to_bytes(result)

    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (1024, 732)
    assert img.format == "PNG"


@pytest.mark.asyncio
async def test_binance_mark_price_retrieval_success():
    """Verify Binance market data client fetches real-time price from endpoint."""
    client = BinanceMarketDataClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"symbol": "BTCUSDT", "markPrice": "64123.45"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        price = await client.get_mark_price("BTCUSDT")
        assert price == Decimal("64123.45")
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_binance_mark_price_failure_raises_error_in_live_mode():
    """Verify that in production mode, if mark price cannot be fetched, it raises an error."""
    client = BinanceMarketDataClient()

    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        with pytest.raises(RuntimeError) as exc_info:
            await client.get_mark_price("BTCUSDT", mock_fallback=None)
        assert "Gagal mengambil live Mark Price" in str(exc_info.value)


@pytest.mark.asyncio
async def test_telegram_conversation_flow_mock_mode():
    """Verify complete Telegram conversation flow from coin input to card delivery."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    status_mock = MagicMock()
    status_mock.delete = AsyncMock()
    update.message.reply_text.return_value = status_mock

    context = MagicMock()
    context.user_data = {}

    # Step 1: Start Mock
    state = await start_position_mock(update, context)
    assert state == PositionState.WAITING_COIN
    assert context.user_data["sim_mode"] == "MOCK"

    # Step 2: Coin Input
    update.message.text = "BTCUSDT"
    state = await handle_coin(update, context)
    assert state == PositionState.WAITING_SIDE
    assert context.user_data["sim_input"]["symbol"] == "BTCUSDT"

    # Step 3: Side Callback
    cb_update = MagicMock()
    cb_update.callback_query.data = "side_LONG"
    cb_update.callback_query.answer = AsyncMock()
    cb_update.callback_query.edit_message_text = AsyncMock()
    state = await handle_side(cb_update, context)
    assert state == PositionState.WAITING_ENTRY
    assert context.user_data["sim_input"]["side"] == Side.LONG

    # Step 4: Entry Price
    update.message.text = "60000.00"
    state = await handle_entry_price(update, context)
    assert state == PositionState.WAITING_LEVERAGE
    assert context.user_data["sim_input"]["entry_price"] == Decimal("60000.00")

    # Step 5: Leverage
    update.message.text = "20"
    state = await handle_leverage(update, context)
    assert state == PositionState.WAITING_MARGIN
    assert context.user_data["sim_input"]["leverage"] == Decimal("20")

    # Step 6: Margin
    update.message.text = "100.00"
    state = await handle_margin(update, context)
    assert state == PositionState.WAITING_MARGIN_RATIO
    assert context.user_data["sim_input"]["margin"] == Decimal("100.00")

    # Step 7: Margin Ratio & Generation
    update.message.text = "8.29"
    with patch("app.binance.client.BinanceMarketDataClient.get_mark_price_and_funding", new_callable=AsyncMock) as mock_mp:
        mock_mp.return_value = (Decimal("63000.00"), Decimal("0.00001"))
        state = await handle_margin_ratio(update, context)
        assert state == -1  # ConversationHandler.END

    # Verify photo was transmitted
    update.message.reply_photo.assert_called_once()
    kwargs = update.message.reply_photo.call_args.kwargs
    assert "photo" in kwargs
    assert "BTCUSDT" in kwargs["caption"]


@pytest.mark.asyncio
async def test_validation_invalid_symbol():
    """Verify entering an invalid coin symbol keeps state at WAITING_COIN."""
    update = MagicMock()
    update.message.text = "NOTREALCOIN"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {"sim_input": {}}

    state = await handle_coin(update, context)
    assert state == PositionState.WAITING_COIN
    update.message.reply_text.assert_called_once()
    assert "Invalid Binance Futures symbol" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_validation_invalid_entry_price():
    """Verify invalid entry price (negative or non-numeric) keeps state at WAITING_ENTRY."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {"sim_input": {}}

    for bad_input in ["-10.5", "not_a_number", "0"]:
        update.message.text = bad_input
        state = await handle_entry_price(update, context)
        assert state == PositionState.WAITING_ENTRY
        assert "Invalid entry price" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_validation_invalid_leverage():
    """Verify invalid leverage (< 1 or > max) keeps state at WAITING_LEVERAGE."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {"sim_input": {}}

    for bad_lev in ["0", "-5", "500", "invalid"]:
        update.message.text = bad_lev
        state = await handle_leverage(update, context)
        assert state == PositionState.WAITING_LEVERAGE
        assert "Invalid leverage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_validation_invalid_margin():
    """Verify invalid margin (<= 0 or non-numeric) keeps state at WAITING_MARGIN."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {"sim_input": {}}

    for bad_margin in ["0", "-100", "abc"]:
        update.message.text = bad_margin
        state = await handle_margin(update, context)
        assert state == PositionState.WAITING_MARGIN
        assert "Invalid margin" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_validation_invalid_margin_ratio():
    """Verify invalid margin ratio (< 0 or > 100) keeps state at WAITING_MARGIN_RATIO."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.user_data = {"sim_input": {}}

    for bad_mr in ["-1", "150", "text"]:
        update.message.text = bad_mr
        state = await handle_margin_ratio(update, context)
        assert state == PositionState.WAITING_MARGIN_RATIO
        assert "Invalid margin ratio" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_binance_api_timeout_raises_error():
    """Verify Binance API timeout raises RuntimeError in live mode."""
    import httpx
    client = BinanceMarketDataClient()

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Request timed out")):
        with pytest.raises(RuntimeError) as exc_info:
            await client.get_mark_price("ETHUSDT", mock_fallback=None)
        assert "Gagal mengambil live Mark Price" in str(exc_info.value)


@pytest.mark.asyncio
async def test_binance_api_http_error():
    """Verify Binance API HTTP 500 error raises RuntimeError in live mode."""
    import httpx
    client = BinanceMarketDataClient()

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_resp)

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with pytest.raises(RuntimeError) as exc_info:
            await client.get_mark_price("ETHUSDT", mock_fallback=None)
        assert "Gagal mengambil live Mark Price" in str(exc_info.value)


@pytest.mark.asyncio
async def test_binance_api_missing_mark_price():
    """Verify Binance response without markPrice field raises RuntimeError."""
    client = BinanceMarketDataClient()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"symbol": "BTCUSDT"}  # missing markPrice
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with pytest.raises(RuntimeError) as exc_info:
            await client.get_mark_price("BTCUSDT", mock_fallback=None)
        assert "Gagal mengambil live Mark Price" in str(exc_info.value)


def test_decimal_calculation_precision_and_tick_size():
    """Verify exact Decimal calculations and tick size formatting for sub-cent values."""
    pos_input = PositionInput(
        symbol="FARTCOINUSDT",
        side=Side.LONG,
        entry_price=Decimal("0.1912999"),
        leverage=Decimal("3"),
        margin=Decimal("5.17"),
        margin_ratio=Decimal("7.64"),
        mode="LIVE",
    )
    res = calculate_position(pos_input, mark_price=Decimal("0.1980000"), tick_size=Decimal("0.0000001"), step_size=Decimal("1"))

    # Size = Margin * Leverage = 5.17 * 3 = 15.51
    assert res.position_size == Decimal("15.51")
    # PNL = 15.51 * (0.1980000 - 0.1912999) / 0.1912999
    expected_pnl = Decimal("15.51") * (Decimal("0.1980000") - Decimal("0.1912999")) / Decimal("0.1912999")
    assert res.pnl == expected_pnl
    assert res.pnl_formatted == "+0.54"
    # ROI = (pnl / margin) * 100
    expected_roi = (expected_pnl / Decimal("5.17")) * Decimal("100")
    assert res.roi == expected_roi
    assert res.roi_formatted == "+10.51%"


def test_production_and_calibration_marker_difference():
    """Verify renderer produces clean card without SIMULATED badge and correct B/S side badges."""
    pos_long = PositionInput(
        symbol="FARTCOINUSDT",
        side=Side.LONG,
        entry_price=Decimal("0.1912999"),
        leverage=Decimal("3"),
        margin=Decimal("5.17"),
        margin_ratio=Decimal("7.64"),
        mode="LIVE",
    )
    res_long = calculate_position(pos_long, mark_price=Decimal("0.1980000"), tick_size=Decimal("0.0000001"), step_size=Decimal("1"))

    pos_short = PositionInput(
        symbol="BTCUSDT",
        side=Side.SHORT,
        entry_price=Decimal("81358.0"),
        leverage=Decimal("100"),
        margin=Decimal("14972.38"),
        margin_ratio=Decimal("11.14"),
        mode="LIVE",
    )
    res_short = calculate_position(pos_short, mark_price=Decimal("81208.19"), tick_size=Decimal("0.1"), step_size=Decimal("0.001"))

    renderer = PositionCardRenderer(mode="PRODUCTION")

    img_long = renderer.render(res_long)
    img_short = renderer.render(res_short)

    arr_long = np.array(img_long, dtype=float)
    arr_short = np.array(img_short, dtype=float)

    # 1. No SIMULATED badge anywhere in top right area (must be clean background)
    top_right_slice = arr_long[45:80, 850:984]
    bg_diff = np.abs(top_right_slice - np.array([35.0, 37.0, 49.0]))
    assert np.max(bg_diff) == 0.0, "Top right must be clean background without SIMULATED badge"

    # 2. LONG side badge must be Green (B)
    badge_long = arr_long[42:84, 39:81]
    assert np.mean(badge_long[:, :, 1]) > np.mean(badge_long[:, :, 0]), "LONG badge must be green"

    # 3. SHORT side badge must be Red (S)
    badge_short = arr_short[42:84, 39:81]
    assert np.mean(badge_short[:, :, 0]) > np.mean(badge_short[:, :, 1]), "SHORT badge must be red"
