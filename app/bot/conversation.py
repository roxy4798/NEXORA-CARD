"""Conversation wizard for paper position generation."""

from decimal import Decimal
import io
import logging
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.config import settings
from app.binance.client import BinanceMarketDataClient
from app.simulation.models import Side, PositionInput, PositionResult
from app.simulation.calculator import calculate_position
from app.simulation.precision import to_decimal, quantize_tick, format_price_by_tick
from app.renderer.position_card import PositionCardRenderer
from app.bot.states import PositionState
from app.bot.keyboards import get_side_keyboard, get_position_action_keyboard

from app.bot.storage import PositionStore

logger = logging.getLogger(__name__)

# Shared instances
binance_client = BinanceMarketDataClient()
renderer = PositionCardRenderer(mode="PRODUCTION")
position_store = PositionStore()

# In-memory store for active positions across chats: {simulation_id: (PositionInput, PositionResult)}
ACTIVE_POSITIONS: Dict[str, dict] = position_store.load_all_positions()


async def start_position_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /position (LIVE Mode)."""
    context.user_data["sim_mode"] = "LIVE"
    context.user_data["sim_input"] = {}

    # Ensure exchange info is initialized
    if not binance_client.exchange_info.is_loaded:
        await binance_client.init_exchange_info(use_fallback_on_error=True)

    await update.message.reply_text("Enter Coin (e.g. WUSDT):")
    return PositionState.WAITING_COIN


async def start_position_mock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /mock_position (MOCK Mode)."""
    context.user_data["sim_mode"] = "MOCK"
    context.user_data["sim_input"] = {}

    if not binance_client.exchange_info.is_loaded:
        await binance_client.init_exchange_info(use_fallback_on_error=True)

    await update.message.reply_text("🛠️ [MOCK MODE] Enter Coin (e.g. WUSDT):")
    return PositionState.WAITING_COIN


async def handle_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1: Validate coin symbol against Binance Futures exchange info."""
    raw_symbol = update.message.text.strip().upper()
    info = binance_client.exchange_info.get_symbol_info(raw_symbol)

    if not info or not binance_client.exchange_info.is_valid_symbol(raw_symbol):
        await update.message.reply_text(
            f"❌ Invalid Binance Futures symbol '{raw_symbol}'.\n"
            "Please enter another coin (e.g. WUSDT, BTCUSDT, ETHUSDT):"
        )
        return PositionState.WAITING_COIN

    context.user_data["sim_input"]["symbol"] = raw_symbol
    context.user_data["sim_input"]["symbol_info"] = info

    await update.message.reply_text(
        f"✅ Symbol: {raw_symbol}\nSelect Side:",
        reply_markup=get_side_keyboard(),
    )
    return PositionState.WAITING_SIDE


async def handle_side(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: Handle Side selection callback (LONG / SHORT)."""
    query = update.callback_query
    await query.answer()

    data = query.data
    side_str = data.split("_")[1]
    side = Side.LONG if side_str == "LONG" else Side.SHORT
    context.user_data["sim_input"]["side"] = side

    await query.edit_message_text(f"Selected Side: {side.value}\n\nEnter Entry Price:")
    return PositionState.WAITING_ENTRY


async def handle_entry_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: Validate Entry Price numeric, > 0, and tick compatibility."""
    raw_val = update.message.text.strip()
    try:
        entry_price = to_decimal(raw_val)
        if entry_price <= Decimal("0"):
            raise ValueError("Entry price must be strictly positive.")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid entry price: {e}\nPlease enter a valid number (e.g. 0.0140000):")
        return PositionState.WAITING_ENTRY

    info = context.user_data["sim_input"].get("symbol_info")
    if info:
        # Quantize to tick size
        entry_price = quantize_tick(entry_price, info.tick_size)

    context.user_data["sim_input"]["entry_price"] = entry_price
    await update.message.reply_text(
        f"✅ Entry Price: {format_price_by_tick(entry_price, info.tick_size) if info else entry_price}\n\n"
        f"Enter Leverage (1 - {settings.default_max_leverage}):"
    )
    return PositionState.WAITING_LEVERAGE


async def handle_leverage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: Validate leverage."""
    raw_val = update.message.text.strip()
    try:
        leverage = to_decimal(raw_val)
        if leverage <= Decimal("0") or leverage > Decimal(str(settings.default_max_leverage)):
            raise ValueError(f"Leverage must be between 1 and {settings.default_max_leverage}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid leverage: {e}\nPlease enter a valid leverage (e.g. 20):")
        return PositionState.WAITING_LEVERAGE

    context.user_data["sim_input"]["leverage"] = leverage
    await update.message.reply_text(f"✅ Leverage: {leverage}x\n\nEnter Margin in USDT (e.g. 176.80):")
    return PositionState.WAITING_MARGIN


async def handle_margin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 5: Validate margin."""
    raw_val = update.message.text.strip()
    try:
        margin = to_decimal(raw_val)
        if margin <= Decimal("0"):
            raise ValueError("Margin must be strictly positive.")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid margin: {e}\nPlease enter a positive amount in USDT (e.g. 176.80):")
        return PositionState.WAITING_MARGIN

    context.user_data["sim_input"]["margin"] = margin
    await update.message.reply_text(f"✅ Margin: {margin:.2f} USDT\n\nEnter Margin Ratio % (e.g. 8.29):")
    return PositionState.WAITING_MARGIN_RATIO


async def handle_margin_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 6: Validate margin ratio and generate position card."""
    raw_val = update.message.text.strip()
    try:
        margin_ratio = to_decimal(raw_val)
        if margin_ratio < Decimal("0") or margin_ratio > Decimal("100"):
            raise ValueError("Margin ratio must be between 0 and 100%.")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid margin ratio: {e}\nPlease enter a percentage between 0 and 100:")
        return PositionState.WAITING_MARGIN_RATIO

    context.user_data["sim_input"]["margin_ratio"] = margin_ratio
    status_msg = await update.message.reply_text("⏳ Retrieving real-time market data and rendering card...")

    try:
        # Step 7: Fetch Mark Price + Funding Rate from a single premiumIndex call
        sim_data = context.user_data["sim_input"]
        symbol = sim_data["symbol"]
        mode = context.user_data.get("sim_mode", "LIVE")

        symbol_info = sim_data["symbol_info"]
        tick_size = symbol_info.tick_size
        step_size = symbol_info.step_size

        if mode == "MOCK":
            mock_price = Decimal("0.0157539") if symbol == "WUSDT" else sim_data["entry_price"] * Decimal("1.05")
            mark_price, funding_rate = await binance_client.get_mark_price_and_funding(
                symbol, mock_fallback=mock_price, mock_funding_rate=Decimal("0.0001")
            )
        else:
            mark_price, funding_rate = await binance_client.get_mark_price_and_funding(symbol)

        pos_input = PositionInput(
            symbol=symbol,
            side=sim_data["side"],
            entry_price=sim_data["entry_price"],
            leverage=sim_data["leverage"],
            margin=sim_data["margin"],
            margin_ratio=sim_data["margin_ratio"],
            mode=mode,
        )

        pos_result = calculate_position(pos_input, mark_price, tick_size, step_size, funding_rate=funding_rate)

        # Store in global active positions and persistent store
        ACTIVE_POSITIONS[pos_result.simulation_id] = {
            "input": pos_input,
            "result": pos_result,
            "symbol_info": symbol_info,
        }
        position_store.save_position(pos_result.simulation_id, pos_input, pos_result, symbol_info)

        # Render PNG
        png_bytes = renderer.render_to_bytes(pos_result)
        photo_file = io.BytesIO(png_bytes)
        photo_file.name = f"{symbol}_position.png"

        # Delete status message
        await status_msg.delete()

        # Send Photo
        caption = f"📊 *{pos_result.symbol}* ({pos_result.side.value}) | {pos_result.pnl_formatted} USDT ({pos_result.roi_formatted})"
        await update.message.reply_photo(
            photo=photo_file,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=get_position_action_keyboard(pos_result.simulation_id),
        )
    except Exception as e:
        logger.error(f"Failed to generate position card: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Failed to generate position: {e}")

    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    await update.message.reply_text("🚫 Position generation cancelled.")
    return ConversationHandler.END


def get_position_conversation_handler() -> ConversationHandler:
    """Builds the ConversationHandler for /position and /mock_position."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("position", start_position_live),
            CommandHandler("mock_position", start_position_mock),
        ],
        states={
            PositionState.WAITING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coin)],
            PositionState.WAITING_SIDE: [CallbackQueryHandler(handle_side, pattern=r"^side_")],
            PositionState.WAITING_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_entry_price)],
            PositionState.WAITING_LEVERAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_leverage)],
            PositionState.WAITING_MARGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_margin)],
            PositionState.WAITING_MARGIN_RATIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_margin_ratio)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True,
    )
