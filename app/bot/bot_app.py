"""Telegram Bot application builder and setup."""

import logging
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram import Update

from app.config import settings
from app.bot.conversation import get_position_conversation_handler
from app.bot.handlers import (
    handle_refresh_callback,
    handle_edit_callback,
    handle_delete_callback,
    handle_edit_field_selection,
    handle_edit_value_input,
    handle_cancel_edit,
    global_error_handler,
)

logger = logging.getLogger(__name__)


async def start_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends greeting and usage help."""
    text = (
        "🤖 *Binance Futures Paper Position Generator*\n\n"
        "Generate photorealistic simulated position cards using real Binance Futures market data.\n\n"
        "✨ *Commands:*\n"
        "• `/position` - Start interactive wizard (LIVE Binance Mark Price)\n"
        "• `/mock_position` - Start interactive wizard (MOCK offline mode)\n"
        "• `/help` - Show this help menu\n\n"
        "⚠️ *Safety Notice:* This simulator is strictly for learning & testing. "
        "It NEVER places real orders or touches real funds."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def create_telegram_application() -> Application:
    """Builds and returns configured python-telegram-bot Application."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured in environment.")

    builder = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token or "123456789:dummy_token_for_init_only")
        .connect_timeout(settings.telegram_connect_timeout)
        .read_timeout(settings.telegram_read_timeout)
        .write_timeout(settings.telegram_write_timeout)
    )

    # Optional HTTP proxy (e.g. TELEGRAM_PROXY_URL=http://127.0.0.1:8080 in .env)
    if settings.telegram_proxy_url:
        logger.info(f"Using proxy for Telegram: {settings.telegram_proxy_url}")
        builder = builder.proxy(settings.telegram_proxy_url)

    app = builder.build()

    # Commands
    app.add_handler(CommandHandler("start", start_help_command))
    app.add_handler(CommandHandler("help", start_help_command))

    # Position Conversation Handler
    app.add_handler(get_position_conversation_handler())

    # Post-generation button callbacks
    app.add_handler(CallbackQueryHandler(handle_refresh_callback,     pattern=r"^refresh_"))
    app.add_handler(CallbackQueryHandler(handle_edit_callback,        pattern=r"^edit_"))
    app.add_handler(CallbackQueryHandler(handle_delete_callback,      pattern=r"^delete_"))
    app.add_handler(CallbackQueryHandler(handle_edit_field_selection, pattern=r"^ef_.+\|"))  # ef_{sim_id}|{field}
    app.add_handler(CallbackQueryHandler(handle_cancel_edit,          pattern=r"^cancel_edit_"))

    # Direct text input handler for active field edits
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_value_input), group=1)

    # Global Error Handler
    app.add_error_handler(global_error_handler)

    return app
