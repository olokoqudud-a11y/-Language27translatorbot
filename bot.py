import os
import sys
import logging
from typing import Dict, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from deep_translator import GoogleTranslator

# ============================
# CONFIGURATION & LOGGING
# ============================

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================
# ENVIRONMENT VARIABLE CHECK
# ============================

def get_token():
    """Get bot token from environment variables with better error handling"""
    # Try different ways to get the token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        # Try to read from .env file if it exists (for local development)
        try:
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.split("=")[1].strip()
                        break
        except FileNotFoundError:
            pass
    
    if not token:
        logger.error("=" * 60)
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
        logger.error("=" * 60)
        logger.error("Please set your bot token using one of these methods:")
        logger.error("")
        logger.error("1. Railway Dashboard:")
        logger.error("   - Go to your Railway project")
        logger.error("   - Click on your service")
        logger.error("   - Go to 'Variables' tab")
        logger.error("   - Add: TELEGRAM_BOT_TOKEN = your_token_here")
        logger.error("")
        logger.error("2. Railway CLI:")
        logger.error("   railway variables set TELEGRAM_BOT_TOKEN='your_token_here'")
        logger.error("")
        logger.error("3. Local .env file:")
        logger.error("   Create a .env file with: TELEGRAM_BOT_TOKEN=your_token_here")
        logger.error("=" * 60)
        sys.exit(1)
    
    return token

# Get token with error handling
TOKEN = get_token()
logger.info("✅ Bot token loaded successfully!")

# ============================
# DATA STORAGE
# ============================

# Dictionary to store user preferences (in-memory)
user_preferences: Dict[int, Dict[str, str]] = {}

# Language data
LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl",
    "Greek": "el",
    "Turkish": "tr",
    "Vietnamese": "vi",
    "Thai": "th",
    "Indonesian": "id",
    "Polish": "pl",
    "Ukrainian": "uk",
    "Romanian": "ro",
    "Czech": "cs",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Hungarian": "hu",
    "Hebrew": "he",
}

# Language emojis
LANGUAGE_EMOJIS = {
    "en": "🇬🇧", "es": "🇪🇸", "fr": "🇫🇷", "de": "🇩🇪",
    "it": "🇮🇹", "pt": "🇵🇹", "ru": "🇷🇺", "ja": "🇯🇵",
    "zh-CN": "🇨🇳", "zh-TW": "🇹🇼", "ko": "🇰🇷", "ar": "🇸🇦",
    "hi": "🇮🇳", "nl": "🇳🇱", "el": "🇬🇷", "tr": "🇹🇷",
    "vi": "🇻🇳", "th": "🇹🇭", "id": "🇮🇩", "pl": "🇵🇱",
    "uk": "🇺🇦", "ro": "🇷🇴", "cs": "🇨🇿", "sv": "🇸🇪",
    "no": "🇳🇴", "da": "🇩🇰", "fi": "🇫🇮", "hu": "🇭🇺",
    "he": "🇮🇱",
}

# ============================
# HELPER FUNCTIONS
# ============================

def get_user_language(user_id: int) -> str:
    """Get user's preferred language, default to English"""
    if user_id in user_preferences:
        return user_preferences[user_id].get("language", "English")
    return "English"

def update_user_preference(user_id: int, key: str, value: str) -> None:
    """Update user preference"""
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id][key] = value

def get_user_stats(user_id: int) -> Dict:
    """Get user statistics"""
    if user_id not in user_preferences:
        return {"translations": 0, "last_activity": None}
    return user_preferences[user_id].get("stats", {"translations": 0, "last_activity": None})

def increment_translation_count(user_id: int) -> None:
    """Increment user's translation count"""
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    if "stats" not in user_preferences[user_id]:
        user_preferences[user_id]["stats"] = {"translations": 0, "last_activity": None}
    user_preferences[user_id]["stats"]["translations"] += 1
    user_preferences[user_id]["stats"]["last_activity"] = datetime.now().isoformat()

def create_language_keyboard(exclude_lang: Optional[str] = None) -> InlineKeyboardMarkup:
    """Create a keyboard with language buttons"""
    keyboard = []
    row = []
    
    for lang_name, lang_code in LANGUAGES.items():
        if exclude_lang and lang_name == exclude_lang:
            continue
        emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
        button_text = f"{emoji} {lang_name}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"setlang_{lang_code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("📊 My Stats", callback_data="stats"),
        InlineKeyboardButton("ℹ️ Help", callback_data="help")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def create_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Create the main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🌍 Change Language", callback_data="change_lang")],
        [InlineKeyboardButton("📊 My Statistics", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Help & Commands", callback_data="help")],
        [InlineKeyboardButton("📋 Available Languages", callback_data="list_langs")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================
# COMMAND HANDLERS
# ============================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    # Initialize user preferences
    if user_id not in user_preferences:
        update_user_preference(user_id, "language", "English")
        update_user_preference(user_id, "stats", {"translations": 0, "last_activity": None})
        logger.info(f"New user: {username} (ID: {user_id})")
    
    current_lang = get_user_language(user_id)
    stats = get_user_stats(user_id)
    
    welcome_text = (
        f"🌟 **Welcome to Language27 Translator Bot!**\n\n"
        f"👋 Hello {user.first_name}!\n"
        f"📝 Your current target language: **{current_lang}**\n"
        f"📊 Total translations: **{stats['translations']}**\n\n"
        f"**How to use:**\n"
        f"• Send any text message to translate it\n"
        f"• Use the buttons below to navigate\n"
        f"• Type /help for more commands\n\n"
        f"**Powered by:** Google Translate API"
    )
    
    reply_markup = create_main_menu(user_id)
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = (
        "📖 **Language27 Translator Bot - Help**\n\n"
        "**Commands:**\n"
        "• /start - Show welcome message\n"
        "• /help - Show this help\n"
        "• /language - Change translation language\n"
        "• /languages - List all available languages\n"
        "• /stats - View your statistics\n"
        "• /about - About this bot\n\n"
        "**Translation:**\n"
        "Just send any text message and I'll translate it!\n"
        "The source language is detected automatically."
    )
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ])
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language command"""
    user_id = update.effective_user.id
    current_lang = get_user_language(user_id)
    
    await update.message.reply_text(
        f"🌍 **Current Language:** {current_lang}\n\n"
        f"Select your target translation language:",
        reply_markup=create_language_keyboard(),
        parse_mode="Markdown"
    )

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /languages command"""
    lang_list = []
    for lang_name, lang_code in LANGUAGES.items():
        emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
        lang_list.append(f"{emoji} **{lang_name}** (`{lang_code}`)")
    
    text = (
        "🌍 **Available Languages:**\n\n"
        + "\n".join(lang_list)
        + "\n\nUse /language to change your target language."
    )
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command"""
    user_id = update.effective_user.id
    current_lang = get_user_language(user_id)
    stats = get_user_stats(user_id)
    translations = stats["translations"]
    last_active = stats["last_activity"]
    
    if last_active:
        last_active = datetime.fromisoformat(last_active).strftime("%Y-%m-%d %H:%M")
    else:
        last_active = "Never"
    
    text = (
        f"📊 **Your Statistics**\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"🌍 Target Language: **{current_lang}**\n"
        f"📝 Total Translations: **{translations}**\n"
        f"⏰ Last Activity: {last_active}\n\n"
        f"Keep translating to improve your language skills! 💪"
    )
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ])
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command"""
    text = (
        "🤖 **About Language27 Translator Bot**\n\n"
        "Version: 1.0.0\n"
        "Created for the Language27 project\n\n"
        "**Features:**\n"
        "• 30+ languages supported\n"
        "• Automatic language detection\n"
        "• User preferences saved\n"
        "• Translation statistics\n"
        "• Clean, intuitive interface\n\n"
        "**Technologies:**\n"
        "• Python 3.9+\n"
        "• python-telegram-bot\n"
        "• deep-translator\n"
        "• Deployed on Railway"
    )
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ])
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ============================
# CALLBACK QUERY HANDLERS
# ============================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all button callbacks"""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    await query.answer()
    
    # Handle language selection
    if data.startswith("setlang_"):
        lang_code = data.replace("setlang_", "")
        lang_name = None
        for name, code in LANGUAGES.items():
            if code == lang_code:
                lang_name = name
                break
        
        if lang_name:
            update_user_preference(user_id, "language", lang_name)
            emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
            
            await query.edit_message_text(
                f"✅ **Language Updated!**\n\n"
                f"{emoji} Target language changed to: **{lang_name}**\n\n"
                f"Now send me any text to translate it to {lang_name}.",
                parse_mode="Markdown"
            )
            
            reply_markup = create_main_menu(user_id)
            await query.message.reply_text(
                "🔙 **Main Menu**",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Language not found. Please try again.")
    
    # Handle change language
    elif data == "change_lang":
        current_lang = get_user_language(user_id)
        await query.edit_message_text(
            f"🌍 **Change Language**\n\n"
            f"Current: **{current_lang}**\n"
            f"Select a new target language:",
            reply_markup=create_language_keyboard(),
            parse_mode="Markdown"
        )
    
    # Handle statistics
    elif data == "stats":
        stats = get_user_stats(user_id)
        translations = stats["translations"]
        last_active = stats["last_activity"]
        current_lang = get_user_language(user_id)
        
        if last_active:
            last_active = datetime.fromisoformat(last_active).strftime("%Y-%m-%d %H:%M")
        else:
            last_active = "Never"
        
        text = (
            f"📊 **Your Statistics**\n\n"
            f"🌍 Target Language: **{current_lang}**\n"
            f"📝 Total Translations: **{translations}**\n"
            f"⏰ Last Activity: {last_active}\n\n"
            f"Keep up the great work! 🎉"
        )
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="change_lang")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    # Handle help
    elif data == "help":
        help_text = (
            "📖 **Quick Help**\n\n"
            "• Send any text → Translate it\n"
            "• Use /language → Change language\n"
            "• Use /languages → See all options\n"
            "• Use /stats → View statistics\n\n"
            "Need more help? Type /help for detailed instructions."
        )
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="change_lang")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    # Handle main menu
    elif data == "main_menu":
        current_lang = get_user_language(user_id)
        stats = get_user_stats(user_id)
        
        menu_text = (
            f"🏠 **Main Menu**\n\n"
            f"📍 Current language: **{current_lang}**\n"
            f"📊 Translations: **{stats['translations']}**\n\n"
            f"Send any text to translate it!"
        )
        
        reply_markup = create_main_menu(user_id)
        await query.edit_message_text(
            menu_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    # Handle list languages
    elif data == "list_langs":
        lang_list = []
        for lang_name, lang_code in LANGUAGES.items():
            emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
            lang_list.append(f"{emoji} {lang_name}")
        
        text = (
            "🌍 **Available Languages:**\n\n"
            + "\n".join(sorted(lang_list))
            + "\n\nUse /language to change your target language."
        )
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="change_lang")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# ============================
# MESSAGE HANDLERS
# ============================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages (translate them)"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Skip if it's a command
    if text.startswith('/'):
        return
    
    # Get user's target language
    target_lang_name = get_user_language(user_id)
    target_lang_code = LANGUAGES.get(target_lang_name, "en")
    
    try:
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Translate the text
        translator = GoogleTranslator(source="auto", target=target_lang_code)
        translated = translator.translate(text)
        
        # Get source language
        try:
            source_lang = translator.detect(text)
            source_emoji = LANGUAGE_EMOJIS.get(source_lang, "🌍")
            source_name = ""
            for name, code in LANGUAGES.items():
                if code == source_lang:
                    source_name = name
                    break
            if not source_name:
                source_name = source_lang
        except:
            source_name = "Unknown"
            source_emoji = "🌍"
        
        target_emoji = LANGUAGE_EMOJIS.get(target_lang_code, "🌍")
        
        # Increment translation count
        increment_translation_count(user_id)
        
        # Prepare response
        response = (
            f"🔁 **Translation**\n\n"
            f"📝 **Original ({source_name})**\n"
            f"{text}\n\n"
            f"{target_emoji} **Translated ({target_lang_name})**\n"
            f"{translated}\n\n"
            f"💡 Tip: Use /language to change target language"
        )
        
        await update.message.reply_text(
            response,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Translation error for user {user_id}: {e}")
        await update.message.reply_text(
            f"❌ Sorry, I couldn't translate that message.\n\n"
            f"Error: {str(e)[:100]}\n\n"
            f"Please try again with a different text."
        )

# ============================
# ERROR HANDLER
# ============================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ An error occurred. Please try again later."
            )
        except:
            pass

# ============================
# MAIN FUNCTION
# ============================

def main() -> None:
    """Start the bot"""
    logger.info("🚀 Starting Language27 Translator Bot...")
    logger.info(f"📝 Bot Username: @Language27translatorbot")
    logger.info(f"🌍 Supporting {len(LANGUAGES)} languages")
    
    try:
        # Create application
        application = Application.builder().token(TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("language", language_command))
        application.add_handler(CommandHandler("languages", languages_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("about", about_command))
        
        # Message handlers
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        # Start polling
        logger.info("✅ Bot is ready and polling for updates...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
