"""Telegram bot application setup and entry point."""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import config
from bot.handlers import (
    start_command,
    help_command,
    stats_command,
    streak_command,
    leaderboard_command,
    handle_photo,
    handle_text,
    ollama,
)
from services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


def create_bot_app() -> Application:
    """Create and configure the Telegram bot application."""
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Get one from @BotFather on Telegram and add it to your .env file."
        )

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("streak", streak_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))

    # Register message handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start weekly summary scheduler
    scheduler = SchedulerService(app)
    scheduler.start()

    # Shutdown hooks for cleanup
    async def shutdown(application: Application) -> None:
        scheduler.stop()
        await ollama.close()

    app.post_shutdown = shutdown

    logger.info("Bot application created successfully")
    return app
