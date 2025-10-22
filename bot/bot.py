"""
Telegram bot for the TON Trivia Battle mini app.

This bot uses the python‑telegram‑bot library to provide an entry point to
your Telegram mini app. When a user sends the /start command, the bot
responds with a message containing a button that launches the web app.

To run the bot, install python‑telegram‑bot and set the BOT_TOKEN
environment variable. Optionally set WEB_APP_URL to the URL of your
deployed mini app (for example, the HTTPS URL of your Vercel or Netlify
deployment).

Example:

    pip install python-telegram-bot
    export BOT_TOKEN=123456:ABC...
    export WEB_APP_URL=https://your-host.com
    python bot.py

"""

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes


# Read the bot token and web app URL from environment variables, or use
# placeholder values. The bot token must be kept secret.
TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WEB_APP_URL = os.environ.get('WEB_APP_URL', 'https://your-host.com')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respond to /start with a greeting and a button that opens the mini app.
    """
    keyboard = [
        [InlineKeyboardButton('🎮 Oyunu Aç', web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'TON Trivia Battle’a hoş geldin! Aşağıdaki butona tıklayarak mini uygulamayı aç.',
        reply_markup=reply_markup,
    )


def main() -> None:
    """Start the bot."""
    # Create the application instance
    application = Application.builder().token(TOKEN).build()
    # Register handlers
    application.add_handler(CommandHandler('start', start))
    # Run the bot until Ctrl‑C
    application.run_polling()


if __name__ == '__main__':
    main()
