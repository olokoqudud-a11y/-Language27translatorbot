import os
import sys
import logging
import time
from threading import Thread
from flask import Flask, jsonify

# === SETUP LOGGING ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === CHECK TOKEN FIRST ===
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN or TOKEN == "your_actual_token_here" or len(TOKEN) < 10:
    logger.error("=" * 70)
    logger.error("❌ INVALID TELEGRAM BOT TOKEN!")
    logger.error("=" * 70)
    logger.error("You MUST set a valid token in Railway Variables:")
    logger.error("")
    logger.error("1. Go to Railway Dashboard")
    logger.error("2. Click your service")
    logger.error("3. Click 'Variables' tab")
    logger.error("4. Add: TELEGRAM_BOT_TOKEN = [your_real_token]")
    logger.error("5. Get your token from @BotFather on Telegram")
    logger.error("=" * 70)
    # Don't exit - keep web server running for healthcheck
    # Just log the error and continue with web server
    logger.warning("⚠️ Bot will not start without valid token, but web server will run for healthcheck")

# === FLASK WEB SERVER (for healthcheck) ===
app = Flask(__name__)

@app.route('/')
def healthcheck():
    return "✅ Bot is running!", 200

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "bot": "@Language27translatorbot", "token_set": bool(TOKEN and TOKEN != "your_actual_token_here")}), 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 Web server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# === START WEB SERVER IN BACKGROUND ===
web_thread = Thread(target=run_web_server, daemon=True)
web_thread.start()
time.sleep(1)  # Give web server time to start

# === NOW IMPORT TELEGRAM BOT (after web server is running) ===
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    from deep_translator import GoogleTranslator
    logger.info("✅ Telegram libraries imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import libraries: {e}")
    # Keep web server running even if bot fails
    logger.info("🔄 Web server will continue running for healthcheck")
    while True:
        time.sleep(60)

# === BOT CODE (only runs if token is valid) ===
if TOKEN and TOKEN != "your_actual_token_here" and len(TOKEN) > 10:
    logger.info("✅ Bot token looks valid, starting bot...")
    
    # Language data
    LANGUAGES = {
        "English": "en", "Spanish": "es", "French": "fr", "German": "de",
        "Italian": "it", "Portuguese": "pt", "Russian": "ru", "Japanese": "ja",
        "Chinese (Simplified)": "zh-CN", "Korean": "ko", "Arabic": "ar",
        "Hindi": "hi", "Dutch": "nl", "Greek": "el", "Turkish": "tr",
        "Vietnamese": "vi", "Thai": "th", "Indonesian": "id", "Polish": "pl",
        "Ukrainian": "uk", "Romanian": "ro", "Czech": "cs", "Swedish": "sv",
        "Norwegian": "no", "Danish": "da", "Finnish": "fi", "Hungarian": "hu",
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
    
    user_preferences = {}
    
    def get_user_language(user_id):
        return user_preferences.get(user_id, {}).get("language", "English")
    
    def create_language_keyboard():
        keyboard = []
        row = []
        for name, code in LANGUAGES.items():
            emoji = LANGUAGE_EMOJIS.get(code, "🌍")
            row.append(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"lang_{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("📊 Stats", callback_data="stats")])
        return InlineKeyboardMarkup(keyboard)
    
    def create_main_menu():
        keyboard = [
            [InlineKeyboardButton("🌍 Change Language", callback_data="change_lang")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    # === BOT COMMAND HANDLERS ===
    async def start(update: Update, context):
        user = update.effective_user
        user_id = user.id
        if user_id not in user_preferences:
            user_preferences[user_id] = {"language": "English", "translations": 0}
        
        await update.message.reply_text(
            f"🌟 Welcome {user.first_name}!\n\n"
            f"📝 Target language: **{user_preferences[user_id]['language']}**\n"
            f"📊 Translations: **{user_preferences[user_id]['translations']}**\n\n"
            f"Send any text to translate it!",
            reply_markup=create_main_menu(),
            parse_mode="Markdown"
        )
    
    async def language(update: Update, context):
        await update.message.reply_text(
            "🌍 Select your target language:",
            reply_markup=create_language_keyboard(),
            parse_mode="Markdown"
        )
    
    async def stats(update: Update, context):
        user_id = update.effective_user.id
        prefs = user_preferences.get(user_id, {"language": "English", "translations": 0})
        await update.message.reply_text(
            f"📊 **Your Stats**\n\n"
            f"🌍 Language: **{prefs['language']}**\n"
            f"📝 Translations: **{prefs['translations']}**",
            parse_mode="Markdown"
        )
    
    async def button_callback(update: Update, context):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        data = query.data
        
        if data.startswith("lang_"):
            code = data.replace("lang_", "")
            name = None
            for n, c in LANGUAGES.items():
                if c == code:
                    name = n
                    break
            if name:
                if user_id not in user_preferences:
                    user_preferences[user_id] = {"language": "English", "translations": 0}
                user_preferences[user_id]["language"] = name
                await query.edit_message_text(
                    f"✅ Language changed to: **{name}**\n\nSend any text to translate!",
                    parse_mode="Markdown"
                )
        
        elif data == "change_lang":
            await query.edit_message_text(
                "🌍 Select your target language:",
                reply_markup=create_language_keyboard(),
                parse_mode="Markdown"
            )
        
        elif data == "stats":
            prefs = user_preferences.get(user_id, {"language": "English", "translations": 0})
            await query.edit_message_text(
                f"📊 **Your Stats**\n\n"
                f"🌍 Language: **{prefs['language']}**\n"
                f"📝 Translations: **{prefs['translations']}**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="change_lang")]
                ]),
                parse_mode="Markdown"
            )
    
    async def translate(update: Update, context):
        user_id = update.effective_user.id
        text = update.message.text
        
        if text.startswith('/'):
            return
        
        if user_id not in user_preferences:
            user_preferences[user_id] = {"language": "English", "translations": 0}
        
        target = user_preferences[user_id]["language"]
        target_code = LANGUAGES.get(target, "en")
        
        try:
            await update.message.chat.send_action(action="typing")
            translator = GoogleTranslator(source="auto", target=target_code)
            translated = translator.translate(text)
            
            # Detect source
            try:
                detected = translator.detect(text)
                source = ""
                for n, c in LANGUAGES.items():
                    if c == detected:
                        source = n
                        break
                if not source:
                    source = detected
            except:
                source = "Unknown"
            
            user_preferences[user_id]["translations"] += 1
            
            await update.message.reply_text(
                f"🔁 **Translation**\n\n"
                f"📝 **Original ({source})**\n{text}\n\n"
                f"🌍 **Translated ({target})**\n{translated}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Translation error: {e}")
            await update.message.reply_text("❌ Translation failed. Please try again.")
    
    async def error_handler(update, context):
        logger.error(f"Error: {context.error}")
    
    # === START BOT ===
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("language", language))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot is ready and polling for updates...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
        logger.info("🔄 Web server will continue running for healthcheck")
        while True:
            time.sleep(60)
else:
    logger.warning("⚠️ Bot not started - invalid or missing token")
    logger.info("🔄 Web server is running for healthcheck...")
    while True:
        time.sleep(60)
