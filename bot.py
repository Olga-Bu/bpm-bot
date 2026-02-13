"""
Telegram-бот для звукорежиссёров и музыкантов.
Переводит BPM в длительности нот в миллисекундах.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MS_PER_MINUTE = 60_000


def compute_durations(bpm: float) -> dict[str, int]:
    """Вычисляет все длительности нот в миллисекундах для данного BPM."""
    quarter = MS_PER_MINUTE / bpm

    # Основные
    whole = round(quarter * 4)
    half = round(quarter * 2)
    quarter_ms = round(quarter)
    eighth = round(quarter / 2)
    sixteenth = round(quarter / 4)
    thirty_second = round(quarter / 8)

    # Триоли: базовая × 2/3
    quarter_triplet = round(quarter * 2 / 3)
    eighth_triplet = round((quarter / 2) * 2 / 3)
    sixteenth_triplet = round((quarter / 4) * 2 / 3)

    # Пунктирные: базовая × 1.5
    dotted_half = round(half * 1.5)
    dotted_quarter = round(quarter * 1.5)
    dotted_eighth = round((quarter / 2) * 1.5)

    return {
        "whole": whole,
        "half": half,
        "quarter": quarter_ms,
        "eighth": eighth,
        "sixteenth": sixteenth,
        "thirty_second": thirty_second,
        "quarter_triplet": quarter_triplet,
        "eighth_triplet": eighth_triplet,
        "sixteenth_triplet": sixteenth_triplet,
        "dotted_half": dotted_half,
        "dotted_quarter": dotted_quarter,
        "dotted_eighth": dotted_eighth,
    }


def format_response(bpm: int, d: dict[str, int]) -> str:
    """Форматирует ответ пользователю (HTML, жирные значения в мс)."""
    return (
        f"BPM: {bpm}\n\n"
        "Основные:\n"
        f"Четверть: <b>{d['quarter']}</b> мс\n"
        f"Восьмая: <b>{d['eighth']}</b> мс\n"
        f"16-я: <b>{d['sixteenth']}</b> мс\n"
        f"32-я: <b>{d['thirty_second']}</b> мс\n"
        f"Целая: <b>{d['whole']}</b> мс\n"
        f"Половинная: <b>{d['half']}</b> мс\n\n"
        "Триоли:\n"
        f"Четвертная триоль: <b>{d['quarter_triplet']}</b> мс\n"
        f"Восьмая триоль: <b>{d['eighth_triplet']}</b> мс\n"
        f"16-я триоль: <b>{d['sixteenth_triplet']}</b> мс\n\n"
        "Пунктирные:\n"
        f"Пунктирная половинная: <b>{d['dotted_half']}</b> мс\n"
        f"Пунктирная четвертная: <b>{d['dotted_quarter']}</b> мс\n"
        f"Пунктирная восьмая: <b>{d['dotted_eighth']}</b> мс"
    )


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Логирует ошибки и уведомляет пользователя."""
    logger.exception("Ошибка при обработке обновления: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Попробуйте ещё раз или отправьте другое число."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    logger.info("Получена команда /start")
    msg = update.effective_message
    if not msg:
        return
    await msg.reply_text(
        "Привет! Я бот для перевода темпа (BPM) в длительности нот в миллисекундах.\n\n"
        "Отправь мне число BPM (например: 140), и я пришлю таблицу длительностей "
        "для основных нот, триолей и пунктирных длительностей."
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка: бот отвечает «ок»."""
    logger.info("Получена команда /ping")
    msg = update.effective_message
    if msg:
        await msg.reply_text("ок")


async def handle_bpm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстового сообщения с BPM."""
    msg = update.effective_message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    logger.info("Получено сообщение с BPM: %r", text)

    try:
        value = float(text.replace(",", "."))
    except ValueError:
        await msg.reply_text(
            "Введите положительное число BPM (например: 120 или 140)."
        )
        return

    if value <= 0:
        await msg.reply_text("BPM должен быть положительным числом.")
        return

    bpm = int(round(value))
    durations = compute_durations(bpm)
    response = format_response(bpm, durations)
    await msg.reply_text(response, parse_mode="HTML")


def main() -> None:
    # В Python 3.14+ в главном потоке нет event loop по умолчанию — создаём
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    if not TELEGRAM_BOT_TOKEN:
        print(
            "Задайте TELEGRAM_BOT_TOKEN в переменных окружения или в файле .env"
        )
        return

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bpm))
    application.add_error_handler(error_handler)

    async def post_init(app: Application) -> None:
        bot_info = await app.bot.get_me()
        print(f"Подключено к Telegram: @{bot_info.username}")

    application.post_init = post_init

    print("Бот запущен...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
