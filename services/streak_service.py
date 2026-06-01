"""Service for managing eco-streaks and gamification."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database.models import User, EcoAction, WeeklyStreak

logger = logging.getLogger(__name__)


class StreakService:
    """Manages user streaks and eco-action tracking."""

    @staticmethod
    def get_or_create_user(
        session: Session,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> User:
        """Get existing user or create a new one."""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(user)
            session.flush()
            logger.info("Created new user: %s (telegram_id=%d)", username, telegram_id)
        else:
            # Update username/first_name if changed
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
        return user

    @staticmethod
    def log_eco_action(
        session: Session,
        user: User,
        product_name: str,
        category: str,
        recycling_guidance: str,
        carbon_estimate_kg: float,
        greener_alternatives: str,
        raw_response: str,
    ) -> EcoAction:
        """Log a new eco-action for the user."""
        action = EcoAction(
            user_id=user.id,
            product_name=product_name,
            category=category,
            recycling_guidance=recycling_guidance,
            carbon_estimate_kg=carbon_estimate_kg,
            greener_alternatives=greener_alternatives,
            raw_response=raw_response,
        )
        session.add(action)
        session.flush()

        # Update weekly streak
        StreakService._update_streak(session, user)
        return action

    @staticmethod
    def _get_week_start(dt: datetime) -> datetime:
        """Get the Monday 00:00 UTC of the week containing dt."""
        monday = dt - timedelta(days=dt.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _update_streak(session: Session, user: User) -> None:
        """Update or create the weekly streak record for the current week."""
        now = datetime.now(timezone.utc)
        week_start = StreakService._get_week_start(now)

        streak = (
            session.query(WeeklyStreak)
            .filter(
                WeeklyStreak.user_id == user.id,
                WeeklyStreak.week_start == week_start,
            )
            .first()
        )

        if streak:
            streak.actions_count += 1
        else:
            # Check previous week for streak continuity
            prev_week_start = week_start - timedelta(weeks=1)
            prev_streak = (
                session.query(WeeklyStreak)
                .filter(
                    WeeklyStreak.user_id == user.id,
                    WeeklyStreak.week_start == prev_week_start,
                )
                .first()
            )

            streak_length = 1
            if prev_streak and prev_streak.actions_count > 0:
                streak_length = prev_streak.streak_length + 1

            streak = WeeklyStreak(
                user_id=user.id,
                week_start=week_start,
                actions_count=1,
                streak_length=streak_length,
            )
            session.add(streak)

    @staticmethod
    def get_user_stats(session: Session, user: User) -> dict:
        """Get user's eco stats for display."""
        total_actions = (
            session.query(EcoAction).filter(EcoAction.user_id == user.id).count()
        )

        total_carbon = (
            session.query(EcoAction)
            .filter(EcoAction.user_id == user.id)
            .with_entities(EcoAction.carbon_estimate_kg)
            .all()
        )
        total_carbon_saved = sum(c[0] for c in total_carbon if c[0])

        now = datetime.now(timezone.utc)
        week_start = StreakService._get_week_start(now)
        current_streak = (
            session.query(WeeklyStreak)
            .filter(
                WeeklyStreak.user_id == user.id,
                WeeklyStreak.week_start == week_start,
            )
            .first()
        )

        return {
            "total_scans": total_actions,
            "total_carbon_awareness_kg": round(total_carbon_saved, 2),
            "current_week_actions": current_streak.actions_count if current_streak else 0,
            "streak_weeks": current_streak.streak_length if current_streak else 0,
        }

    @staticmethod
    def get_leaderboard(session: Session, limit: int = 10) -> list[dict]:
        """Get top users by streak length for the current week."""
        now = datetime.now(timezone.utc)
        week_start = StreakService._get_week_start(now)

        results = (
            session.query(WeeklyStreak, User)
            .join(User, WeeklyStreak.user_id == User.id)
            .filter(WeeklyStreak.week_start == week_start)
            .order_by(WeeklyStreak.streak_length.desc(), WeeklyStreak.actions_count.desc())
            .limit(limit)
            .all()
        )

        leaderboard = []
        for streak, user in results:
            leaderboard.append({
                "username": user.username or user.first_name or f"User {user.telegram_id}",
                "streak_weeks": streak.streak_length,
                "week_actions": streak.actions_count,
            })
        return leaderboard
