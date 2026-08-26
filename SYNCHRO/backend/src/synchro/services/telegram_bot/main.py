"""Telegram Bot runnable entrypoint."""

from synchro.services.telegram_bot.bot import start_polling, stop_polling
import asyncio


if __name__ == "__main__":
    try:
        asyncio.run(start_polling())
    except KeyboardInterrupt:
        asyncio.run(stop_polling())