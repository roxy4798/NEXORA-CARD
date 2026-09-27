"""Handlers for post-generation interactive buttons (REFRESH, EDIT, DELETE) and lifecycle updates."""

from decimal import Decimal
import io
import logging
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes

from app.config import settings
from app.simulation.calculator import calculate_position
from app.simulation.models import Side, PositionInput
from app.simulation.precision import to_decimal, quantize_tick
from app.bot.conversation import ACTIVE_POSITIONS, binance_client, renderer, position_store
from app.bot.keyboards import (
    get_position_action_keyboard,
    get_edit_fields_keyboard,
    parse_ef_callback,
    EDIT_FIELDS,
)

logger = logging.getLogger(__name__)


# ── Field metadata used for prompts and validation ──────────────────────────
_FIELD_META = {
    "symbol":      {"label": "Coin Symbol",   "example": "BTCUSDT, ETHUSDT, FARTCOINUSDT"},
    "side":        {"label": "Side",          "example": "LONG or SHORT"},
    "entry":       {"label": "Entry Price",   "example": "84059.0, 0.1912"},
    "leverage":    {"label": "Leverage",      "example": f"1 – {settings.default_max_leverage}"},
    "margin":      {"label": "Margin (USDT)", "example": "100.00"},
    "marginratio": {"label": "Margin Ratio %","example": "0 – 100  e.g. 8.29"},
}


def _fmt_current(pos_input: PositionInput, field: str) -> str:
    """Returns a human-readable current value for the given field."""
    mapping = {
        "symbol":      pos_input.symbol,
        "side":        pos_input.side.value,
        "entry":       str(pos_input.entry_price),
        "leverage":    f"{pos_input.leverage}x",
        "margin":      f"{pos_input.margin} USDT",
        "marginratio": f"{pos_input.margin_ratio}%",
    }
    return mapping.get(field, "—")


async def _render_and_reply_photo(
    target,  # update.message or query.message
    result,
    sim_id: str,
    is_edit_message: bool = False,
) -> None:
    """Renders position card PNG and sends/edits the Telegram photo message."""
    png_bytes = renderer.render_to_bytes(result)
    photo_file = io.BytesIO(png_bytes)
    photo_file.name = f"{result.symbol}_position.png"

    side_icon = "🟢" if result.side.value == "LONG" else "🔴"
    caption = (
        f"{side_icon} *{result.symbol}* · {result.side.value} {result.leverage}x\n"
        f"PNL: `{result.pnl_formatted}` USDT  |  ROI: `{result.roi_formatted}`"
    )
    markup = get_position_action_keyboard(sim_id)

    if is_edit_message:
        media = InputMediaPhoto(media=photo_file, caption=caption, parse_mode="Markdown")
        await target.edit_message_media(media=media, reply_markup=markup)
    else:
        await target.reply_photo(photo=photo_file, caption=caption, parse_mode="Markdown", reply_markup=markup)


# ── REFRESH ──────────────────────────────────────────────────────────────────

async def handle_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refreshes the position card with the latest Mark Price and funding rate."""
    query = update.callback_query
    await query.answer(text="⏳ Fetching live data…")

    sim_id = query.data.replace("refresh_", "")
    pos_data = ACTIVE_POSITIONS.get(sim_id)

    if not pos_data:
        stored = position_store.load_all_positions()
        if sim_id in stored:
            ACTIVE_POSITIONS[sim_id] = stored[sim_id]
            pos_data = stored[sim_id]
        else:
            await query.answer(text="⚠️ Position not found or already deleted.", show_alert=True)
            return

    pos_input: PositionInput = pos_data["input"]
    symbol_info = pos_data["symbol_info"]

    try:
        if pos_input.mode == "MOCK":
            mock_price = (
                Decimal("0.0157539") if pos_input.symbol == "WUSDT"
                else pos_input.entry_price * Decimal("1.08")
            )
            mark_price, funding_rate = await binance_client.get_mark_price_and_funding(
                pos_input.symbol, mock_fallback=mock_price, mock_funding_rate=Decimal("0.0001")
            )
        else:
            mark_price, funding_rate = await binance_client.get_mark_price_and_funding(pos_input.symbol)

        updated_result = calculate_position(
            input_data=pos_input,
            mark_price=mark_price,
            tick_size=symbol_info.tick_size,
            step_size=symbol_info.step_size,
            funding_rate=funding_rate,
        )
        updated_result.simulation_id = sim_id
        pos_data["result"] = updated_result
        position_store.save_position(sim_id, pos_input, updated_result, symbol_info)

        await _render_and_reply_photo(query, updated_result, sim_id, is_edit_message=True)

    except Exception as e:
        logger.error(f"Error refreshing position {sim_id}: {e}", exc_info=True)
        await query.answer(text=f"Failed to refresh: {e}", show_alert=True)


# ── EDIT (show field menu) ────────────────────────────────────────────────────

async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the edit field selection menu."""
    query = update.callback_query
    await query.answer()

    sim_id = query.data.replace("edit_", "")
    pos_data = ACTIVE_POSITIONS.get(sim_id)
    if not pos_data:
        await query.answer(text="⚠️ Position session expired.", show_alert=True)
        return

    pos = pos_data["input"]
    text = (
        f"✏️ *Edit Position · {pos.symbol}*\n\n"
        f"┌ Side: *{pos.side.value}*\n"
        f"├ Entry: `{pos.entry_price}`\n"
        f"├ Leverage: `{pos.leverage}x`\n"
        f"├ Margin: `{pos.margin} USDT`\n"
        f"└ Margin Ratio: `{pos.margin_ratio}%`\n\n"
        f"Which parameter do you want to update?"
    )
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=get_edit_fields_keyboard(sim_id))


# ── DELETE ────────────────────────────────────────────────────────────────────

async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes the position card and removes it from memory and storage."""
    query = update.callback_query
    await query.answer(text="🗑️ Position closed.")

    sim_id = query.data.replace("delete_", "")
    if sim_id in ACTIVE_POSITIONS:
        del ACTIVE_POSITIONS[sim_id]
    position_store.delete_position(sim_id)

    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Could not delete message: {e}")
        await query.edit_message_caption(caption="🗑️ *Position closed.*", parse_mode="Markdown")


# ── EDIT FIELD SELECTION ─────────────────────────────────────────────────────

async def handle_edit_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles field selection from the edit menu.

    Callback data format: ef_{sim_id}|{field_key}
    Uses pipe '|' to safely separate sim_id (may contain underscores) from field_key.
    """
    query = update.callback_query
    await query.answer()

    try:
        sim_id, field = parse_ef_callback(query.data)
    except Exception:
        await query.answer(text="⚠️ Invalid edit action.", show_alert=True)
        return

    pos_data = ACTIVE_POSITIONS.get(sim_id)
    if not pos_data:
        await query.answer(text="⚠️ Position not found.", show_alert=True)
        return

    pos_input: PositionInput = pos_data["input"]
    symbol_info = pos_data["symbol_info"]
    meta = _FIELD_META.get(field, {"label": field, "example": ""})

    if field == "side":
        # Immediate toggle: LONG ↔ SHORT
        new_side = Side.SHORT if pos_input.side == Side.LONG else Side.LONG
        pos_input.side = new_side
        pos_input.realized_pnl = pos_data["result"].realized_pnl

        updated_result = calculate_position(
            input_data=pos_input,
            mark_price=pos_data["result"].mark_price,
            tick_size=symbol_info.tick_size,
            step_size=symbol_info.step_size,
        )
        updated_result.simulation_id = sim_id
        pos_data["result"] = updated_result
        position_store.save_position(sim_id, pos_input, updated_result, symbol_info)

        await _render_and_reply_photo(query.message, updated_result, sim_id)
        side_icon = "🟢" if new_side == Side.LONG else "🔴"
        await query.message.reply_text(
            f"{side_icon} Side switched to *{new_side.value}* — position updated.",
            parse_mode="Markdown",
        )
        return

    # For all other fields: prompt the user to type a new value
    current = _fmt_current(pos_input, field)
    context.user_data["editing_sim_id"] = sim_id
    context.user_data["editing_field"] = field

    await query.message.reply_text(
        f"✏️ *Edit {meta['label']}*\n\n"
        f"Current: `{current}`\n"
        f"Format: `{meta['example']}`\n\n"
        f"Type the new value:",
        parse_mode="Markdown",
    )


# ── EDIT VALUE INPUT ──────────────────────────────────────────────────────────

async def handle_edit_value_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes user text input when editing an active position parameter."""
    sim_id = context.user_data.get("editing_sim_id")
    field = context.user_data.get("editing_field")

    if not sim_id or not field:
        return  # not in edit mode — ignore

    pos_data = ACTIVE_POSITIONS.get(sim_id)
    if not pos_data:
        await update.message.reply_text("⚠️ Position session expired or deleted.")
        context.user_data.pop("editing_sim_id", None)
        context.user_data.pop("editing_field", None)
        return

    pos_input: PositionInput = pos_data["input"]
    symbol_info = pos_data["symbol_info"]
    raw_val = update.message.text.strip()
    meta = _FIELD_META.get(field, {"label": field, "example": ""})

    try:
        if field in ("symbol", "coin"):
            new_sym = raw_val.upper()
            if not binance_client.exchange_info.is_valid_symbol(new_sym):
                raise ValueError(f"`{new_sym}` is not a recognized Binance Futures symbol.")
            new_info = binance_client.exchange_info.get_symbol_info(new_sym)
            if not new_info:
                raise ValueError(f"Could not load symbol metadata for {new_sym}.")
            new_mark = await binance_client.get_mark_price(new_sym)
            pos_input.symbol = new_sym
            symbol_info = new_info
            pos_data["symbol_info"] = new_info
            pos_data["result"].mark_price = new_mark
            pos_input.entry_price = quantize_tick(pos_input.entry_price, new_info.tick_size)

        elif field in ("entry", "entry_price"):
            new_val = to_decimal(raw_val)
            if new_val <= Decimal("0"):
                raise ValueError("Entry price must be a positive number.")
            pos_input.entry_price = quantize_tick(new_val, symbol_info.tick_size)

        elif field == "leverage":
            new_val = to_decimal(raw_val)
            if new_val <= Decimal("0") or new_val > Decimal(str(settings.default_max_leverage)):
                raise ValueError(f"Leverage must be between 1 and {settings.default_max_leverage}.")
            pos_input.leverage = new_val

        elif field == "margin":
            new_val = to_decimal(raw_val)
            if new_val <= Decimal("0"):
                raise ValueError("Margin must be a positive number (USDT).")
            pos_input.margin = new_val

        elif field == "marginratio":
            new_val = to_decimal(raw_val)
            if new_val < Decimal("0") or new_val > Decimal("100"):
                raise ValueError("Margin ratio must be between 0 and 100.")
            pos_input.margin_ratio = new_val

        else:
            raise ValueError(f"Unknown edit field: `{field}`")

        # Recalculate — preserve realized_pnl (fees already settled)
        pos_input.realized_pnl = pos_data["result"].realized_pnl
        updated_result = calculate_position(
            input_data=pos_input,
            mark_price=pos_data["result"].mark_price,
            tick_size=symbol_info.tick_size,
            step_size=symbol_info.step_size,
        )
        updated_result.simulation_id = sim_id
        pos_data["result"] = updated_result
        position_store.save_position(sim_id, pos_input, updated_result, symbol_info)

        # Clear edit state
        context.user_data.pop("editing_sim_id", None)
        context.user_data.pop("editing_field", None)

        await _render_and_reply_photo(update.message, updated_result, sim_id)
        await update.message.reply_text(
            f"✅ *{meta['label']}* updated to `{raw_val}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.warning(f"Validation error editing [{field}]: {e}")
        meta = _FIELD_META.get(field, {"label": field, "example": ""})
        await update.message.reply_text(
            f"❌ *Invalid value* — {e}\n\n"
            f"Format: `{meta['example']}`\n"
            f"Please try again:",
            parse_mode="Markdown",
        )


# ── CANCEL EDIT ──────────────────────────────────────────────────────────────

async def handle_cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancels the active edit session."""
    context.user_data.pop("editing_sim_id", None)
    context.user_data.pop("editing_field", None)
    query = update.callback_query
    await query.answer(text="Edit cancelled.")
    try:
        await query.message.delete()
    except Exception:
        await query.message.reply_text("❌ Edit cancelled.")


# ── GLOBAL ERROR HANDLER ──────────────────────────────────────────────────────

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Safely logs uncaught exceptions without leaking sensitive tokens."""
    logger.error("Exception handling update:", exc_info=context.error)
