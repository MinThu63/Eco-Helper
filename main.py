"""Main entry point for Eco-Helper Sustainability Concierge."""

import logging
import sys

from config import config
from database import init_db
from bot.app import create_bot_app


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    """Start the Eco-Helper bot."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("🌱 Starting Eco-Helper Sustainability Concierge...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Create and run bot
    app = create_bot_app()
    logger.info("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
