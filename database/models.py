"""SQLAlchemy models for Eco-Helper."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """Telegram user who interacts with the bot."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    actions = relationship("EcoAction", back_populates="user", cascade="all, delete-orphan")
    streaks = relationship("WeeklyStreak", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class EcoAction(Base):
    """A single eco-action logged when a user scans a product."""

    __tablename__ = "eco_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Product info extracted by vision model
    product_name = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)  # e.g. plastic, glass, paper

    # Analysis results
    recycling_guidance = Column(Text, nullable=True)
    carbon_estimate_kg = Column(Float, nullable=True)
    greener_alternatives = Column(Text, nullable=True)

    # Raw model response for debugging
    raw_response = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="actions")

    def __repr__(self) -> str:
        return f"<EcoAction(user_id={self.user_id}, product={self.product_name})>"


class WeeklyStreak(Base):
    """Tracks weekly eco-streaks for gamification."""

    __tablename__ = "weekly_streaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(DateTime, nullable=False)  # Monday of the week
    actions_count = Column(Integer, default=0)
    streak_length = Column(Integer, default=0)  # Consecutive weeks with >= 1 action

    # Relationships
    user = relationship("User", back_populates="streaks")

    def __repr__(self) -> str:
        return f"<WeeklyStreak(user_id={self.user_id}, week={self.week_start}, count={self.actions_count})>"
