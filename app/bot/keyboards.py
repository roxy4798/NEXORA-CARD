"""Inline keyboards for Telegram bot — modern, professional design."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ── Allowed edit fields and their display labels ───────────────────────────
# Key = field ID used in callback_data, Value = emoji + display name
EDIT_FIELDS: dict[str, str] = {
    "symbol":       "🪙 Coin Symbol",
    "side":         "↕️ Side (L/S)",
    "entry":        "🎯 Entry Price",
    "leverage":     "⚡ Leverage",
    "margin":       "💰 Margin",
    "marginratio":  "📊 Margin Ratio",
}


def get_side_keyboard() -> InlineKeyboardMarkup:
    """Returns side selection inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🟢 LONG", callback_data="side_LONG"),
            InlineKeyboardButton("🔴 SHORT", callback_data="side_SHORT"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_position_action_keyboard(sim_id: str) -> InlineKeyboardMarkup:
    """Returns action buttons displayed below generated position card."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{sim_id}"),
            InlineKeyboardButton("✏️ Edit",    callback_data=f"edit_{sim_id}"),
            InlineKeyboardButton("🗑️ Close",   callback_data=f"delete_{sim_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_edit_fields_keyboard(sim_id: str) -> InlineKeyboardMarkup:
    """Returns keyboard for selecting which parameter to edit.

    Callback data format: ef_{sim_id}|{field_key}
    Uses pipe separator to avoid ambiguity with underscores in sim_id or field names.
    """
    rows = []
    field_items = list(EDIT_FIELDS.items())
    # Pair fields into rows of 2
    for i in range(0, len(field_items), 2):
        row = []
        for field_key, label in field_items[i:i + 2]:
            row.append(InlineKeyboardButton(label, callback_data=f"ef_{sim_id}|{field_key}"))
        rows.append(row)

    # Cancel row
    rows.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_edit_{sim_id}"),
    ])
    return InlineKeyboardMarkup(rows)


def parse_ef_callback(data: str) -> tuple[str, str]:
    """Parses 'ef_{sim_id}|{field}' callback data.

    Returns:
        (sim_id, field_key)
    """
    # strip 'ef_' prefix, split on pipe
    payload = data[3:]  # strip "ef_"
    sim_id, field_key = payload.split("|", 1)
    return sim_id, field_key
