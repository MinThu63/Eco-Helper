"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for Eco-Helper."""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llava")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./eco_helper.db")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
