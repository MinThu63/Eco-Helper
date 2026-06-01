"""Telegram bot command and message handlers."""

import logging
import os
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from database import get_session
from services.ollama_service import OllamaService, EcoAnalysis
from services.streak_service import StreakService

logger = logging.getLogger(__name__)

# Shared Ollama service instance
ollama = OllamaService()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_msg = (
        f"🌱 *Welcome to Eco-Helper, {user.first_name}!*\n\n"
        "I'm your sustainability concierge. Here's what I can do:\n\n"
        "📸 *Send me a photo* of any product or packaging and I'll give you:\n"
        "  • ♻️ Recycling guidance\n"
        "  • 🏭 Carbon footprint estimate\n"
        "  • 🌿 Greener alternatives\n\n"
        "📊 *Commands:*\n"
        "  /stats — Your eco-impact dashboard\n"
        "  /streak — Current week streak info\n"
        "  /leaderboard — Community top eco-warriors\n"
        "  /help — Show this message again\n\n"
        "Let's make the planet greener, one scan at a time! 🌍"
    )

    # Register user in database
    with get_session() as session:
        StreakService.get_or_create_user(
            session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    await update.message.reply_text(welcome_msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await start_command(update, context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command — show user's eco dashboard."""
    user = update.effective_user

    with get_session() as session:
        db_user = StreakService.get_or_create_user(
            session, telegram_id=user.id, username=user.username
        )
        stats = StreakService.get_user_stats(session, db_user)

    msg = (
        "📊 *Your Eco Dashboard*\n\n"
        f"🔍 Total scans: *{stats['total_scans']}*\n"
        f"🏭 Carbon awareness: *{stats['total_carbon_awareness_kg']} kg CO₂e*\n"
        f"📅 This week's scans: *{stats['current_week_actions']}*\n"
        f"🔥 Streak: *{stats['streak_weeks']} week(s)*\n\n"
        "Keep scanning to grow your streak! 🌱"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /streak command."""
    user = update.effective_user

    with get_session() as session:
        db_user = StreakService.get_or_create_user(
            session, telegram_id=user.id, username=user.username
        )
        stats = StreakService.get_user_stats(session, db_user)

    streak = stats["streak_weeks"]
    actions = stats["current_week_actions"]

    # Fun streak messages
    if streak == 0:
        emoji = "🌱"
        message = "Start your streak by scanning a product this week!"
    elif streak < 3:
        emoji = "🌿"
        message = "Nice start! Keep it going!"
    elif streak < 8:
        emoji = "🌳"
        message = "You're growing strong! Impressive commitment!"
    else:
        emoji = "🏆"
        message = "Legendary eco-warrior! You're an inspiration!"

    msg = (
        f"{emoji} *Eco-Streak Update*\n\n"
        f"🔥 Current streak: *{streak} week(s)*\n"
        f"📸 Scans this week: *{actions}*\n\n"
        f"{message}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /leaderboard command."""
    with get_session() as session:
        leaders = StreakService.get_leaderboard(session, limit=10)

    if not leaders:
        await update.message.reply_text(
            "🏆 *Leaderboard*\n\nNo eco-warriors yet this week. Be the first! 🌱",
            parse_mode="Markdown",
        )
        return

    lines = ["🏆 *Community Leaderboard*\n"]
    medals = ["🥇", "🥈", "🥉"]

    for i, entry in enumerate(leaders):
        medal = medals[i] if i < 3 else f"  {i + 1}."
        lines.append(
            f"{medal} *{entry['username']}* — "
            f"{entry['streak_weeks']}w streak, {entry['week_actions']} scans"
        )

    lines.append("\nKeep scanning to climb the ranks! 🌍")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos — analyze with Ollama vision model."""
    user = update.effective_user
    await update.message.reply_text("🔍 Analyzing your product... please wait ♻️")

    # Download the photo (get largest available size)
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    image_path = os.path.join(temp_dir, f"{photo.file_id}.jpg")

    await file.download_to_drive(image_path)
    logger.info("Downloaded photo to %s", image_path)

    try:
        # Analyze with Ollama
        analysis: EcoAnalysis = await ollama.analyze_image(image_path)

        # Format response
        response_msg = _format_analysis(analysis)

        # Log to database
        with get_session() as session:
            db_user = StreakService.get_or_create_user(
                session,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
            )
            StreakService.log_eco_action(
                session,
                user=db_user,
                product_name=analysis.product_name,
                category=analysis.category,
                recycling_guidance=analysis.recycling_guidance,
                carbon_estimate_kg=analysis.carbon_estimate_kg,
                greener_alternatives=analysis.greener_alternatives,
                raw_response=analysis.raw_response,
            )

        await update.message.reply_text(response_msg, parse_mode="Markdown")

    except Exception as e:
        logger.error("Error analyzing photo: %s", e, exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, something went wrong analyzing your image. "
            "Please make sure Ollama is running and try again."
        )
    finally:
        # Cleanup temp file
        try:
            os.remove(image_path)
            os.rmdir(temp_dir)
        except OSError:
            pass


def _format_analysis(analysis: EcoAnalysis) -> str:
    """Format the eco-analysis into a nice Telegram message."""
    # Category emoji mapping
    category_emojis = {
        "plastic": "🧴",
        "glass": "🫙",
        "paper": "📄",
        "metal": "🥫",
        "organic": "🍎",
        "electronic": "📱",
        "textile": "👕",
        "mixed": "📦",
        "unknown": "❓",
    }
    cat_emoji = category_emojis.get(analysis.category, "📦")

    msg = (
        f"🌱 *Eco-Analysis Complete!*\n\n"
        f"📦 *Product:* {analysis.product_name}\n"
        f"{cat_emoji} *Category:* {analysis.category.title()}\n\n"
        f"♻️ *Recycling Guidance:*\n{analysis.recycling_guidance}\n\n"
        f"🏭 *Carbon Footprint:* ~{analysis.carbon_estimate_kg} kg CO₂e\n\n"
        f"🌿 *Greener Alternatives:*\n{analysis.greener_alternatives}\n\n"
        f"_Scan logged! Keep building your eco-streak_ 🔥"
    )
    return msg


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages."""
    await update.message.reply_text(
        "📸 Send me a *photo* of a product or packaging and I'll analyze it for you!\n\n"
        "Or use /help to see all available commands.",
        parse_mode="Markdown",
    )
