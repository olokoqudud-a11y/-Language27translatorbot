import os
import sys
import logging
import threading
from typing import Dict, Optional
from datetime import datetime
from flask import Flask

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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================
# FLASK WEB SERVER FOR HEALTHCHECK
# ============================

app = Flask(__name__)

@app.route('/')
def healthcheck():
    return "✅ Bot is running!", 200

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "@Language27translatorbot"}, 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ============================
# ENVIRONMENT VARIABLE CHECK
# ============================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN or TOKEN == "your_actual_token_here":
    logger.error("=" * 70)
    logger.error("❌ INVALID TELEGRAM_BOT_TOKEN!")
    logger.error("=" * 70)
    logger.error("You must set a valid bot token from @BotFather")
    logger.error("")
    logger.error("How to get your token:")
    logger.error("1. Open Telegram")
    logger.error("2. Search for @BotFather")
    logger.error("3. Send: /token")
    logger.error("4. Select your bot: @Language27translatorbot")
    logger.error("5. Copy the token (looks like: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)")
    logger.error("")
    logger.error("How to set it on Railway:")
    logger.error("1. Go to your Railway project")
    logger.error("2. Click on your service")
    logger.error("3. Click 'Variables' tab")
    logger.error("4. Add: TELEGRAM_BOT_TOKEN = [your_real_token]")
    logger.error("5. Click 'Save' and redeploy")
    logger.error("=" * 70)
    sys.exit(1)

logger.info("✅ Bot token loaded successfully!")

# ============================
# DATA STORAGE
# ============================

user_preferences: Dict[int, Dict[str, str]] = {}

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

LANGUAGE_EMOJIS = {
    "en": "🇬🇧", "es": "🇪🇸", "fr": "🇫🇷", "de": "🇩🇪",
    "it": "🇮🇹", "pt": "🇵🇹", "ru": "🇷🇺", "ja": "🇯🇵",
    "zh-CN": "🇨🇳", "ko": "🇰🇷", "ar": "🇸🇦", "hi": "🇮🇳",
    "nl": "🇳🇱", "el": "🇬🇷", "tr": "🇹🇷", "vi": "🇻🇳",
    "th": "🇹🇭", "id": "🇮🇩", "pl": "🇵🇱", "uk": "🇺🇦",
    "ro": "🇷🇴", "cs": "🇨🇿", "sv": "🇸🇪", "no": "🇳🇴",
    "da": "🇩🇰", "fi": "🇫🇮", "hu": "🇭🇺", "he": "🇮🇱",
}

# ============================
# HELPER FUNCTIONS
# ============================

def get_user_language(user_id: int) -> str:
    if user_id in user_preferences:
        return user_preferences[user_id].get("language", "English")
    return "English"

def update_user_preference(user_id: int, key: str, value: str) -> None:
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id][key] = value

def get_user_stats(user_id: int) -> Dict:
    if user_id not in user_preferences:
        return {"translations": 0, "last_activity": None}
    return user_preferences[user_id].get("stats", {"translations": 0, "last_activity": None})

def increment_translation_count(user_id: int) -> None:
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    if "stats" not in user_preferences[user_id]:
        user_preferences[user_id]["stats"] = {"translations": 0, "last_activity": None}
    user_preferences[user_id]["stats"]["translations"] += 1
    user_preferences[user_id]["stats"]["last_activity"] = datetime.now().isoformat()

def create_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for lang_name, lang_code in LANGUAGES.items():
        emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
        row.append(InlineKeyboardButton(f"{emoji} {lang_name}", callback_data=f"setlang_{lang_code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("📊 My Stats", callback_data="stats")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def create_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🌍 Change Language", callback_data="change_lang")],
        [InlineKeyboardButton("📊 My Statistics", callback_data="stats")],
        [InlineKeyboardButton("📋 Available Languages", callback_data="list_langs")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================
# COMMAND HANDLERS
# ============================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_preferences:
        update_user_preference(user_id, "language", "English")
        update_user_preference(user_id, "stats", {"translations": 0, "last_activity": None})
        logger.info(f"New user: {user.username or user.first_name} (ID: {user_id})")
    
    current_lang = get_user_language(user_id)
    stats = get_user_stats(user_id)
    
    welcome_text = (
        f"🌟 **Welcome to Language27 Translator Bot!**\n\n"
        f"👋 Hello {user.first_name}!\n"
        f"📝 Target language: **{current_lang}**\n"
        f"📊 Translations: **{stats['translations']}**\n\n"
        f"Send any text to translate it!"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_menu(),
        parse_mode="Markdown"
    )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_lang = get_user_language(user_id)
    
    await update.message.reply_text(
        f"🌍 **Current Language:** {current_lang}\n\nSelect your target language:",
        reply_markup=create_language_keyboard(),
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_lang = get_user_language(user_id)
    stats = get_user_stats(user_id)
    last_active = stats["last_activity"]
    
    if last_active:
        last_active = datetime.fromisoformat(last_active).strftime("%Y-%m-%d %H:%M")
    else:
        last_active = "Never"
    
    text = (
        f"📊 **Your Statistics**\n\n"
        f"🌍 Target Language: **{current_lang}**\n"
        f"📝 Total Translations: **{stats['translations']}**\n"
        f"⏰ Last Activity: {last_active}"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang_list = []
    for lang_name, lang_code in LANGUAGES.items():
        emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
        lang_list.append(f"{emoji} **{lang_name}**")
    
    await update.message.reply_text(
        "🌍 **Available Languages:**\n\n" + "\n".join(lang_list),
        parse_mode="Markdown"
    )

# ============================
# CALLBACK HANDLERS
# ============================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    await query.answer()
    
    if data.startswith("setlang_"):
        lang_code = data.replace("setlang_", "")
        lang_name = None
        for name, code in LANGUAGES.items():
            if code == lang_code:
                lang_name = name
                break
        
        if lang_name:
            update_user_preference(user_id, "language", lang_name)
            await query.edit_message_text(
                f"✅ Language changed to: **{lang_name}**\n\nSend any text to translate!",
                parse_mode="Markdown"
            )
    
    elif data == "change_lang":
        current_lang = get_user_language(user_id)
        await query.edit_message_text(
            f"🌍 **Current:** {current_lang}\n\nSelect new language:",
            reply_markup=create_language_keyboard(),
            parse_mode="Markdown"
        )
    
    elif data == "stats":
        stats = get_user_stats(user_id)
        current_lang = get_user_language(user_id)
        last_active = stats["last_activity"]
        
        if last_active:
            last_active = datetime.fromisoformat(last_active).strftime("%Y-%m-%d %H:%M")
        else:
            last_active = "Never"
        
        text = (
            f"📊 **Your Statistics**\n\n"
            f"🌍 Target Language: **{current_lang}**\n"
            f"📝 Translations: **{stats['translations']}**\n"
            f"⏰ Last Active: {last_active}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="change_lang")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]),
            parse_mode="Markdown"
        )
    
    elif data == "list_langs":
        lang_list = []
        for lang_name, lang_code in LANGUAGES.items():
            emoji = LANGUAGE_EMOJIS.get(lang_code, "🌍")
            lang_list.append(f"{emoji} {lang_name}")
        
        await query.edit_message_text(
            "🌍 **All Languages:**\n\n" + "\n".join(lang_list),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="change_lang")]
            ]),
            parse_mode="Markdown"
        )
    
    elif data == "main_menu":
        current_lang = get_user_language(user_id)
        stats = get_user_stats(user_id)
        
        await query.edit_message_text(
            f"🏠 **Main Menu**\n\n📍 Language: **{current_lang}**\n📊 Translations: **{stats['translations']}**\n\nSend any text to translate!",
            reply_markup=create_main_menu(),
            parse_mode="Markdown"
        )

# ============================
# MESSAGE HANDLER
# ============================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.startswith('/'):
        return
    
    target_lang_name = get_user_language(user_id)
    target_lang_code = LANGUAGES.get(target_lang_name, "en")
    
    try:
        await update.message.chat.send_action(action="typing")
        
        translator = GoogleTranslator(source="auto", target=target_lang_code)
        translated = translator.translate(text)
        
        # Detect source language
        try:
            source_lang = translator.detect(text)
            source_name = ""
            for name, code in LANGUAGES.items():
                if code == source_lang:
                    source_name = name
                    break
            if not source_name:
                source_name = source_lang
        except:
            source_name = "Unknown"
        
        increment_translation_count(user_id)
        
        response = (
            f"🔁 **Translation**\n\n"
            f"📝 **Original ({source_name})**\n{text}\n\n"
            f"🌍 **Translated ({target_lang_name})**\n{translated}"
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text("❌ Sorry, couldn't translate that. Please try again.")

# ============================
# ERROR HANDLER
# ============================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error}")
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ An error occurred. Please try again."
        )

# ============================
# MAIN
# ============================

def main() -> None:
    logger.info("🚀 Starting Language27 Translator Bot...")
    logger.info(f"📝 Bot: @Language27translatorbot")
    logger.info(f"🌍 Supporting {len(LANGUAGES)} languages")
    
    # Start web server for healthchecks
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Start bot
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("language", language_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("languages", languages_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot is ready!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
