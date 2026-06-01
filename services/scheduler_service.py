"""Scheduled tasks for weekly eco-streak summaries."""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from database import get_session
from database.models import User, WeeklyStreak

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled tasks like weekly streak summaries."""

    def __init__(self, app: Application) -> None:
        self.app = app
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Start the scheduler with weekly summary job."""
        # Run every Sunday at 18:00 UTC
        self.scheduler.add_job(
            self._send_weekly_summaries,
            "cron",
            day_of_week="sun",
            hour=18,
            minute=0,
            id="weekly_summary",
        )
        self.scheduler.start()
        logger.info("Scheduler started — weekly summaries every Sunday at 18:00 UTC")

    def stop(self) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=False)

    async def _send_weekly_summaries(self) -> None:
        """Send weekly eco-streak summaries to all active users."""
        logger.info("Sending weekly eco-streak summaries...")

        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        with get_session() as session:
            # Get all users with activity this week
            streaks = (
                session.query(WeeklyStreak, User)
                .join(User, WeeklyStreak.user_id == User.id)
                .filter(WeeklyStreak.week_start == week_start)
                .all()
            )

            for streak, user in streaks:
                try:
                    msg = self._format_weekly_summary(user, streak)
                    await self.app.bot.send_message(
                        chat_id=user.telegram_id,
                        text=msg,
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to send summary to user %d: %s",
                        user.telegram_id,
                        e,
                    )

        logger.info("Weekly summaries sent to %d users", len(streaks))

    @staticmethod
    def _format_weekly_summary(user: User, streak: WeeklyStreak) -> str:
        """Format the weekly summary message."""
        name = user.first_name or user.username or "Eco-Warrior"

        if streak.streak_length >= 4:
            badge = "🏆 Eco-Champion"
        elif streak.streak_length >= 2:
            badge = "🌳 Growing Green"
        else:
            badge = "🌱 Getting Started"

        return (
            f"📬 *Weekly Eco-Recap for {name}*\n\n"
            f"📸 Scans this week: *{streak.actions_count}*\n"
            f"🔥 Streak: *{streak.streak_length} week(s)*\n"
            f"🎖 Badge: *{badge}*\n\n"
            f"{'Great job keeping up your streak!' if streak.streak_length > 1 else 'Scan more products next week to build your streak!'}\n\n"
            f"_Every scan helps you make greener choices_ 🌍"
        )
