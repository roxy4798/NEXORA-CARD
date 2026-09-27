"""Comprehensive tests for Position Lifecycle: REFRESH, EDIT, DELETE, Multi-Position Isolation, and Persistence."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.simulation.models import Side, PositionInput, PositionResult
from app.simulation.calculator import calculate_position
from app.binance.exchange_info import SymbolInfo
from app.bot.conversation import ACTIVE_POSITIONS
from app.bot.storage import PositionStore
from app.bot.handlers import (
    handle_refresh_callback,
    handle_edit_callback,
    handle_delete_callback,
    handle_edit_field_selection,
    handle_edit_value_input,
)


@pytest.fixture
def mock_storage(tmp_path):
    """Provides a fresh temporary PositionStore."""
    store_file = tmp_path / "positions_test.json"
    store = PositionStore(file_path=store_file)
    return store


@pytest.fixture
def setup_three_positions(mock_storage):
    """Creates 3 isolated simulated positions (A, B, C) in memory and storage."""
    ACTIVE_POSITIONS.clear()

    # Position A: FARTCOINUSDT LONG
    info_a = SymbolInfo(symbol="FARTCOINUSDT", status="TRADING", tick_size=Decimal("0.0001000"), step_size=Decimal("0.1"), min_qty=Decimal("0.1"), min_notional=Decimal("5"))
    inp_a = PositionInput(symbol="FARTCOINUSDT", side=Side.LONG, entry_price=Decimal("0.1912999"), leverage=Decimal("3"), margin=Decimal("5.17"), margin_ratio=Decimal("7.64"), mode="LIVE")
    res_a = calculate_position(inp_a, mark_price=Decimal("0.1942000"), tick_size=info_a.tick_size, step_size=info_a.step_size)
    res_a.simulation_id = "sim_A"

    # Position B: BTCUSDT SHORT
    info_b = SymbolInfo(symbol="BTCUSDT", status="TRADING", tick_size=Decimal("0.10"), step_size=Decimal("0.001"), min_qty=Decimal("0.001"), min_notional=Decimal("5"))
    inp_b = PositionInput(symbol="BTCUSDT", side=Side.SHORT, entry_price=Decimal("65000.00"), leverage=Decimal("20"), margin=Decimal("100.00"), margin_ratio=Decimal("10.00"), mode="LIVE")
    res_b = calculate_position(inp_b, mark_price=Decimal("63000.00"), tick_size=info_b.tick_size, step_size=info_b.step_size)
    res_b.simulation_id = "sim_B"

    # Position C: ETHUSDT LONG
    info_c = SymbolInfo(symbol="ETHUSDT", status="TRADING", tick_size=Decimal("0.01"), step_size=Decimal("0.01"), min_qty=Decimal("0.01"), min_notional=Decimal("5"))
    inp_c = PositionInput(symbol="ETHUSDT", side=Side.LONG, entry_price=Decimal("3200.00"), leverage=Decimal("10"), margin=Decimal("50.00"), margin_ratio=Decimal("12.50"), mode="LIVE")
    res_c = calculate_position(inp_c, mark_price=Decimal("3400.00"), tick_size=info_c.tick_size, step_size=info_c.step_size)
    res_c.simulation_id = "sim_C"

    for sim_id, inp, res, info in [("sim_A", inp_a, res_a, info_a), ("sim_B", inp_b, res_b, info_b), ("sim_C", inp_c, res_c, info_c)]:
        ACTIVE_POSITIONS[sim_id] = {"input": inp, "result": res, "symbol_info": info}
        mock_storage.save_position(sim_id, inp, res, info)

    return {"sim_A": inp_a, "sim_B": inp_b, "sim_C": inp_c}


@pytest.mark.asyncio
async def test_refresh_long_with_mark_price_change(setup_three_positions):
    """Verify refreshing a LONG position updates Mark Price, PNL, and ROI without changing input parameters."""
    update = MagicMock()
    update.callback_query.data = "refresh_sim_A"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_media = AsyncMock()
    context = MagicMock()

    initial_entry = ACTIVE_POSITIONS["sim_A"]["input"].entry_price
    initial_margin = ACTIVE_POSITIONS["sim_A"]["input"].margin
    initial_lev = ACTIVE_POSITIONS["sim_A"]["input"].leverage
    initial_side = ACTIVE_POSITIONS["sim_A"]["input"].side

    # Mock new mark price higher (profit increase) - returns (mark, funding_rate) tuple
    new_mark = Decimal("0.2000000")
    with patch("app.binance.client.BinanceMarketDataClient.get_mark_price_and_funding", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = (new_mark, Decimal("0.00005"))
        await handle_refresh_callback(update, context)

    # Verify input unchanged
    assert ACTIVE_POSITIONS["sim_A"]["input"].entry_price == initial_entry
    assert ACTIVE_POSITIONS["sim_A"]["input"].margin == initial_margin
    assert ACTIVE_POSITIONS["sim_A"]["input"].leverage == initial_lev
    assert ACTIVE_POSITIONS["sim_A"]["input"].side == initial_side
    assert ACTIVE_POSITIONS["sim_A"]["result"].simulation_id == "sim_A"

    # Verify metrics updated
    updated_result = ACTIVE_POSITIONS["sim_A"]["result"]
    assert updated_result.mark_price == new_mark
    assert updated_result.pnl > Decimal("0")
    update.callback_query.edit_message_media.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_short_with_mark_price_change(setup_three_positions):
    """Verify refreshing a SHORT position calculates correct updated profit on price drop."""
    update = MagicMock()
    update.callback_query.data = "refresh_sim_B"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_media = AsyncMock()
    context = MagicMock()

    # Short entry was 65000, new mark is 62000 (profit increase) - returns (mark, rate) tuple
    new_mark = Decimal("62000.00")
    with patch("app.binance.client.BinanceMarketDataClient.get_mark_price_and_funding", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = (new_mark, Decimal("0.00001"))
        await handle_refresh_callback(update, context)

    updated_result = ACTIVE_POSITIONS["sim_B"]["result"]
    assert updated_result.mark_price == new_mark
    assert updated_result.side == Side.SHORT
    # Expected PNL = 2000 * (65000 - 62000) / 65000
    assert updated_result.pnl > Decimal("0")
    assert updated_result.pnl_formatted.startswith("+")
    update.callback_query.edit_message_media.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_api_failure_does_not_corrupt_position(setup_three_positions):
    """Verify that if Binance API fails during refresh, the cached position remains intact."""
    update = MagicMock()
    update.callback_query.data = "refresh_sim_A"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_media = AsyncMock()
    context = MagicMock()

    prev_mark = ACTIVE_POSITIONS["sim_A"]["result"].mark_price
    prev_pnl = ACTIVE_POSITIONS["sim_A"]["result"].pnl

    with patch("app.binance.client.BinanceMarketDataClient.get_mark_price_and_funding", new_callable=AsyncMock,
               side_effect=RuntimeError("Gagal mengambil live Mark Price untuk FARTCOINUSDT dari Binance Futures API (Binance 503).")):
        await handle_refresh_callback(update, context)

    # Position result remains uncorrupted
    assert ACTIVE_POSITIONS["sim_A"]["result"].mark_price == prev_mark
    assert ACTIVE_POSITIONS["sim_A"]["result"].pnl == prev_pnl
    # Alert answered with failure notice
    update.callback_query.answer.assert_called_with(text="Failed to refresh: Gagal mengambil live Mark Price untuk FARTCOINUSDT dari Binance Futures API (Binance 503).", show_alert=True)


@pytest.mark.asyncio
async def test_delete_position_and_reject_further_refresh(setup_three_positions):
    """Verify deleting a position purges it from memory and rejects further refresh attempts."""
    update = MagicMock()
    update.callback_query.data = "delete_sim_C"
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.delete = AsyncMock()
    context = MagicMock()

    assert "sim_C" in ACTIVE_POSITIONS
    await handle_delete_callback(update, context)
    assert "sim_C" not in ACTIVE_POSITIONS

    # Attempting to refresh sim_C after deletion
    refresh_update = MagicMock()
    refresh_update.callback_query.data = "refresh_sim_C"
    refresh_update.callback_query.answer = AsyncMock()

    await handle_refresh_callback(refresh_update, context)
    refresh_update.callback_query.answer.assert_called_with(text="⚠️ Position not found or already deleted.", show_alert=True)


@pytest.mark.asyncio
async def test_edit_side_toggle(setup_three_positions):
    """Verify toggling side from LONG to SHORT recalculates position metrics."""
    update = MagicMock()
    update.callback_query.data = "ef_sim_A|side"
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.reply_photo = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    context = MagicMock()

    assert ACTIVE_POSITIONS["sim_A"]["input"].side == Side.LONG
    await handle_edit_field_selection(update, context)

    assert ACTIVE_POSITIONS["sim_A"]["input"].side == Side.SHORT
    assert ACTIVE_POSITIONS["sim_A"]["result"].side == Side.SHORT
    update.callback_query.message.reply_photo.assert_called_once()


@pytest.mark.asyncio
async def test_edit_entry_price(setup_three_positions):
    """Verify editing entry price updates entry and recalculates metrics."""
    update = MagicMock()
    update.message.text = "0.1950000"
    update.message.reply_photo = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"editing_sim_id": "sim_A", "editing_field": "entry"}

    await handle_edit_value_input(update, context)

    assert ACTIVE_POSITIONS["sim_A"]["input"].entry_price == Decimal("0.1950000")
    assert ACTIVE_POSITIONS["sim_A"]["result"].entry_price == Decimal("0.1950000")
    update.message.reply_photo.assert_called_once()
    assert "editing_sim_id" not in context.user_data


@pytest.mark.asyncio
async def test_edit_leverage(setup_three_positions):
    """Verify editing leverage updates leverage and recalculates position size."""
    update = MagicMock()
    update.message.text = "10"
    update.message.reply_photo = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"editing_sim_id": "sim_A", "editing_field": "leverage"}

    await handle_edit_value_input(update, context)

    assert ACTIVE_POSITIONS["sim_A"]["input"].leverage == Decimal("10")
    assert ACTIVE_POSITIONS["sim_A"]["result"].leverage == Decimal("10")
    # Position size = 5.17 * 10 = 51.70
    assert ACTIVE_POSITIONS["sim_A"]["result"].position_size == Decimal("51.70")


@pytest.mark.asyncio
async def test_edit_margin(setup_three_positions):
    """Verify editing margin updates margin and position size."""
    update = MagicMock()
    update.message.text = "20.00"
    update.message.reply_photo = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"editing_sim_id": "sim_A", "editing_field": "margin"}

    await handle_edit_value_input(update, context)

    assert ACTIVE_POSITIONS["sim_A"]["input"].margin == Decimal("20.00")
    assert ACTIVE_POSITIONS["sim_A"]["result"].margin == Decimal("20.00")
    # Position size = 20.00 * 3 = 60.00
    assert ACTIVE_POSITIONS["sim_A"]["result"].position_size == Decimal("60.00")


@pytest.mark.asyncio
async def test_edit_invalid_values(setup_three_positions):
    """Verify entering invalid values for fields prompts error and keeps edit state."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    # Invalid entry
    context.user_data = {"editing_sim_id": "sim_A", "editing_field": "entry"}
    update.message.text = "-10"
    await handle_edit_value_input(update, context)
    assert context.user_data.get("editing_sim_id") == "sim_A"
    assert "Invalid value" in update.message.reply_text.call_args[0][0]

    # Invalid leverage
    context.user_data = {"editing_sim_id": "sim_A", "editing_field": "leverage"}
    update.message.text = "200"
    await handle_edit_value_input(update, context)
    assert context.user_data.get("editing_sim_id") == "sim_A"
    assert "Invalid value" in update.message.reply_text.call_args[0][0]

    # Invalid margin
    context.user_data = {"editing_sim_id": "sim_A", "editing_field": "margin"}
    update.message.text = "0"
    await handle_edit_value_input(update, context)
    assert context.user_data.get("editing_sim_id") == "sim_A"
    assert "Invalid value" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_multi_position_isolation(setup_three_positions):
    """Verify complete isolation between 3 concurrent simulated positions (A, B, C)."""
    # 1. Refresh A does not alter B or C
    b_entry_before = ACTIVE_POSITIONS["sim_B"]["input"].entry_price
    b_size_before = ACTIVE_POSITIONS["sim_B"]["result"].position_size
    c_mark_before = ACTIVE_POSITIONS["sim_C"]["result"].mark_price

    up_a = MagicMock()
    up_a.callback_query.data = "refresh_sim_A"
    up_a.callback_query.answer = AsyncMock()
    up_a.callback_query.edit_message_media = AsyncMock()
    with patch("app.binance.client.BinanceMarketDataClient.get_mark_price_and_funding", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = (Decimal("0.2500000"), Decimal("0.00005"))
        await handle_refresh_callback(up_a, MagicMock())

    assert ACTIVE_POSITIONS["sim_B"]["input"].entry_price == b_entry_before
    assert ACTIVE_POSITIONS["sim_B"]["result"].position_size == b_size_before
    assert ACTIVE_POSITIONS["sim_C"]["result"].mark_price == c_mark_before

    # 2. Edit B does not alter A or C
    up_b = MagicMock()
    up_b.message.text = "50"  # leverage = 50
    up_b.message.reply_photo = AsyncMock()
    up_b.message.reply_text = AsyncMock()
    ctx_b = MagicMock()
    ctx_b.user_data = {"editing_sim_id": "sim_B", "editing_field": "leverage"}
    await handle_edit_value_input(up_b, ctx_b)

    assert ACTIVE_POSITIONS["sim_B"]["input"].leverage == Decimal("50")
    assert ACTIVE_POSITIONS["sim_A"]["input"].leverage == Decimal("3")
    assert ACTIVE_POSITIONS["sim_C"]["input"].leverage == Decimal("10")

    # 3. Delete C does not remove A or B
    up_c = MagicMock()
    up_c.callback_query.data = "delete_sim_C"
    up_c.callback_query.answer = AsyncMock()
    up_c.callback_query.message.delete = AsyncMock()
    await handle_delete_callback(up_c, MagicMock())

    assert "sim_C" not in ACTIVE_POSITIONS
    assert "sim_A" in ACTIVE_POSITIONS
    assert "sim_B" in ACTIVE_POSITIONS


def test_persistence_restart_reload_cycle(mock_storage):
    """Verify create -> restart -> reload -> refresh lifecycle without silent corruption."""
    # 1. Create and save position
    info = SymbolInfo(symbol="FARTCOINUSDT", status="TRADING", tick_size=Decimal("0.0001000"), step_size=Decimal("0.1"), min_qty=Decimal("0.1"), min_notional=Decimal("5"))
    inp = PositionInput(symbol="FARTCOINUSDT", side=Side.LONG, entry_price=Decimal("0.1912999"), leverage=Decimal("3"), margin=Decimal("5.17"), margin_ratio=Decimal("7.64"), mode="LIVE")
    res = calculate_position(inp, mark_price=Decimal("0.1942000"), tick_size=info.tick_size, step_size=info.step_size)
    res.simulation_id = "sim_persist_1"

    mock_storage.save_position("sim_persist_1", inp, res, info)

    # 2. Simulate bot restart (re-instantiate store and reload)
    restarted_store = PositionStore(file_path=mock_storage.file_path)
    loaded_positions = restarted_store.load_all_positions()

    assert "sim_persist_1" in loaded_positions
    loaded_item = loaded_positions["sim_persist_1"]

    assert loaded_item["input"].symbol == "FARTCOINUSDT"
    assert loaded_item["input"].side == Side.LONG
    assert loaded_item["input"].entry_price == Decimal("0.1912999")
    assert loaded_item["input"].leverage == Decimal("3")
    assert loaded_item["input"].margin == Decimal("5.17")
    assert loaded_item["result"].pnl == res.pnl
    assert loaded_item["result"].roi == res.roi
    assert loaded_item["symbol_info"].tick_size == Decimal("0.0001000")
