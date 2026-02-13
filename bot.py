"""
Telegram-бот для звукорежиссёров и музыкантов.
Переводит BPM в длительности нот в миллисекундах.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Путь к файлу избранного
FAVORITES_FILE = Path(__file__).parent / "favorites.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MS_PER_MINUTE = 60_000


# ═══════════════════════════════════════════════════════════════════════════════
# Избранное
# ═══════════════════════════════════════════════════════════════════════════════

def load_favorites() -> dict[str, list[int]]:
    """Загружает избранное из файла."""
    if FAVORITES_FILE.exists():
        try:
            return json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_favorites(data: dict[str, list[int]]) -> None:
    """Сохраняет избранное в файл."""
    FAVORITES_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def get_user_favorites(user_id: int) -> list[int]:
    """Возвращает список избранных BPM пользователя."""
    data = load_favorites()
    return data.get(str(user_id), [])


def add_to_favorites(user_id: int, bpm: int) -> bool:
    """Добавляет BPM в избранное. Возвращает True если добавлено."""
    data = load_favorites()
    key = str(user_id)
    if key not in data:
        data[key] = []
    if bpm in data[key]:
        return False
    data[key].append(bpm)
    data[key] = sorted(data[key])[:20]  # Максимум 20 значений
    save_favorites(data)
    return True


def remove_from_favorites(user_id: int, bpm: int) -> bool:
    """Удаляет BPM из избранного. Возвращает True если удалено."""
    data = load_favorites()
    key = str(user_id)
    if key not in data or bpm not in data[key]:
        return False
    data[key].remove(bpm)
    save_favorites(data)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Расчёты
# ═══════════════════════════════════════════════════════════════════════════════

def compute_durations(bpm: float) -> dict[str, float]:
    """Вычисляет все длительности нот в миллисекундах для данного BPM."""
    quarter = MS_PER_MINUTE / bpm

    return {
        # Основные
        "whole": quarter * 4,
        "half": quarter * 2,
        "quarter": quarter,
        "eighth": quarter / 2,
        "sixteenth": quarter / 4,
        "thirty_second": quarter / 8,
        # Триоли
        "quarter_triplet": quarter * 2 / 3,
        "eighth_triplet": (quarter / 2) * 2 / 3,
        "sixteenth_triplet": (quarter / 4) * 2 / 3,
        # Пунктирные (Dotted) — для Delay
        "dotted_half": quarter * 2 * 1.5,
        "dotted_quarter": quarter * 1.5,
        "dotted_eighth": (quarter / 2) * 1.5,
        "dotted_sixteenth": (quarter / 4) * 1.5,
    }


def compute_lfo_hz(bpm: float) -> dict[str, float]:
    """Вычисляет частоты LFO в Гц для синхронизации с темпом."""
    quarter_ms = MS_PER_MINUTE / bpm
    quarter_hz = 1000 / quarter_ms  # Гц = 1000 / мс

    return {
        "whole": quarter_hz / 4,
        "half": quarter_hz / 2,
        "quarter": quarter_hz,
        "eighth": quarter_hz * 2,
        "sixteenth": quarter_hz * 4,
        "thirty_second": quarter_hz * 8,
        # Dotted
        "dotted_quarter": quarter_hz / 1.5,
        "dotted_eighth": (quarter_hz * 2) / 1.5,
    }


def ms_to_bpm(ms: float, note_type: str = "quarter") -> float:
    """Конвертирует миллисекунды в BPM."""
    multipliers = {
        "whole": 4,
        "half": 2,
        "quarter": 1,
        "eighth": 0.5,
        "sixteenth": 0.25,
    }
    mult = multipliers.get(note_type, 1)
    quarter_ms = ms / mult
    return MS_PER_MINUTE / quarter_ms


# ═══════════════════════════════════════════════════════════════════════════════
# Форматирование
# ═══════════════════════════════════════════════════════════════════════════════

def format_response(bpm: int, d: dict[str, float], lfo: dict[str, float]) -> str:
    """Форматирует ответ с эмодзи и всеми данными."""
    return (
        f"🎵 <b>BPM: {bpm}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"🎼 <b>Основные длительности:</b>\n"
        f"┌ ♩ Четверть (1/4): <b>{round(d['quarter'])}</b> мс\n"
        f"├ ♪ Восьмая (1/8): <b>{round(d['eighth'])}</b> мс\n"
        f"├ ♬ 16-я (1/16): <b>{round(d['sixteenth'])}</b> мс\n"
        f"├ ♬ 32-я (1/32): <b>{round(d['thirty_second'])}</b> мс\n"
        f"├ ◐ Половинная (1/2): <b>{round(d['half'])}</b> мс\n"
        f"└ ○ Целая (1/1): <b>{round(d['whole'])}</b> мс\n\n"
        
        f"🎹 <b>Триоли:</b>\n"
        f"┌ Четвертная: <b>{round(d['quarter_triplet'])}</b> мс\n"
        f"├ Восьмая: <b>{round(d['eighth_triplet'])}</b> мс\n"
        f"└ 16-я: <b>{round(d['sixteenth_triplet'])}</b> мс\n\n"
        
        f"⏱ <b>Delay Time (Dotted):</b>\n"
        f"┌ 1/2 D: <b>{round(d['dotted_half'])}</b> мс\n"
        f"├ 1/4 D: <b>{round(d['dotted_quarter'])}</b> мс\n"
        f"├ 1/8 D: <b>{round(d['dotted_eighth'])}</b> мс\n"
        f"└ 1/16 D: <b>{round(d['dotted_sixteenth'])}</b> мс\n\n"
        
        f"〰️ <b>LFO (Гц):</b>\n"
        f"┌ 1/1: <b>{lfo['whole']:.3f}</b> Hz\n"
        f"├ 1/2: <b>{lfo['half']:.3f}</b> Hz\n"
        f"├ 1/4: <b>{lfo['quarter']:.3f}</b> Hz\n"
        f"├ 1/8: <b>{lfo['eighth']:.3f}</b> Hz\n"
        f"├ 1/16: <b>{lfo['sixteenth']:.3f}</b> Hz\n"
        f"└ 1/32: <b>{lfo['thirty_second']:.3f}</b> Hz"
    )


def get_bpm_keyboard(bpm: int, user_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру под сообщением с BPM."""
    favorites = get_user_favorites(user_id)
    is_favorite = bpm in favorites
    
    star = "⭐️ Убрать из избранного" if is_favorite else "☆ В избранное"
    
    keyboard = [
        [InlineKeyboardButton(star, callback_data=f"fav_{bpm}")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════════════════════
# Обработчики
# ═══════════════════════════════════════════════════════════════════════════════

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки."""
    logger.exception("Ошибка при обработке: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте ещё раз."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start."""
    msg = update.effective_message
    if not msg:
        return
    
    await msg.reply_text(
        "🎵 <b>BPM Calculator</b>\n\n"
        "Привет! Я помогу перевести темп (BPM) в длительности нот.\n\n"
        "<b>Что я умею:</b>\n"
        "• Основные длительности в мс\n"
        "• Триоли\n"
        "• Delay Time (Dotted)\n"
        "• Частоты LFO в Гц\n"
        "• Обратный расчёт (мс → BPM)\n\n"
        "Просто отправь число BPM, например: <code>140</code>\n\n"
        "Или миллисекунды для обратного расчёта:\n"
        "<code>ms 500</code> — узнать BPM по четверти\n"
        "<code>ms 250 1/8</code> — по восьмой",
        parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help."""
    msg = update.effective_message
    if not msg:
        return
    
    await msg.reply_text(
        "📖 <b>Справка</b>\n\n"
        "<b>Расчёт BPM → мс:</b>\n"
        "Отправь число, например: <code>120</code>\n\n"
        "<b>Обратный расчёт (мс → BPM):</b>\n"
        "<code>ms 500</code> — по четверти (1/4)\n"
        "<code>ms 250 1/8</code> — по восьмой\n"
        "<code>ms 1000 1/2</code> — по половинной\n\n"
        "<b>Избранное:</b>\n"
        "/favorites — показать сохранённые BPM\n"
        "Кнопка ☆ под результатом — добавить/убрать\n\n"
        "<b>Команды:</b>\n"
        "/start — начало\n"
        "/help — эта справка\n"
        "/favorites — избранное",
        parse_mode="HTML"
    )


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /favorites — показать избранное."""
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return
    
    favs = get_user_favorites(user.id)
    
    if not favs:
        await msg.reply_text(
            "⭐️ <b>Избранное пусто</b>\n\n"
            "Отправь BPM и нажми кнопку ☆ под результатом, чтобы сохранить.",
            parse_mode="HTML"
        )
        return
    
    # Создаём кнопки для быстрого доступа
    buttons = []
    row = []
    for bpm in favs:
        row.append(InlineKeyboardButton(str(bpm), callback_data=f"calc_{bpm}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await msg.reply_text(
        f"⭐️ <b>Избранные BPM ({len(favs)}):</b>\n\n"
        "Нажми на значение для быстрого расчёта:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений."""
    msg = update.effective_message
    user = update.effective_user
    if not msg or not msg.text or not user:
        return
    
    text = msg.text.strip().lower()
    
    # Обратный расчёт: ms 500 или ms 500 1/8
    if text.startswith("ms "):
        await handle_ms_to_bpm(msg, text)
        return
    
    # Обычный расчёт BPM
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        await msg.reply_text(
            "🎵 Отправь число BPM (например: <code>140</code>)\n"
            "Или <code>ms 500</code> для обратного расчёта",
            parse_mode="HTML"
        )
        return
    
    if value <= 0 or value > 9999:
        await msg.reply_text("⚠️ BPM должен быть от 1 до 9999")
        return
    
    bpm = int(round(value))
    durations = compute_durations(bpm)
    lfo = compute_lfo_hz(bpm)
    response = format_response(bpm, durations, lfo)
    keyboard = get_bpm_keyboard(bpm, user.id)
    
    await msg.reply_text(response, parse_mode="HTML", reply_markup=keyboard)


async def handle_ms_to_bpm(msg, text: str) -> None:
    """Обработка обратного расчёта мс → BPM."""
    parts = text.split()
    
    # Парсим миллисекунды
    try:
        ms = float(parts[1].replace(",", "."))
    except (IndexError, ValueError):
        await msg.reply_text(
            "⚠️ Формат: <code>ms 500</code> или <code>ms 500 1/8</code>",
            parse_mode="HTML"
        )
        return
    
    if ms <= 0:
        await msg.reply_text("⚠️ Миллисекунды должны быть положительным числом")
        return
    
    # Парсим тип ноты (опционально)
    note_type = "quarter"
    note_name = "четверти (1/4)"
    
    if len(parts) >= 3:
        note_map = {
            "1/1": ("whole", "целой (1/1)"),
            "1/2": ("half", "половинной (1/2)"),
            "1/4": ("quarter", "четверти (1/4)"),
            "1/8": ("eighth", "восьмой (1/8)"),
            "1/16": ("sixteenth", "16-й (1/16)"),
        }
        note_input = parts[2]
        if note_input in note_map:
            note_type, note_name = note_map[note_input]
        else:
            await msg.reply_text(
                "⚠️ Доступные длительности: 1/1, 1/2, 1/4, 1/8, 1/16\n"
                "Пример: <code>ms 250 1/8</code>",
                parse_mode="HTML"
            )
            return
    
    bpm = ms_to_bpm(ms, note_type)
    
    await msg.reply_text(
        f"🔄 <b>Обратный расчёт</b>\n\n"
        f"Если {note_name} = <b>{round(ms)}</b> мс,\n"
        f"то темп ≈ <b>{bpm:.1f}</b> BPM\n\n"
        f"<i>Отправь <code>{round(bpm)}</code> для полного расчёта</i>",
        parse_mode="HTML"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на inline-кнопки."""
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return
    
    await query.answer()
    data = query.data
    
    # Добавить/убрать из избранного
    if data.startswith("fav_"):
        bpm = int(data.split("_")[1])
        favorites = get_user_favorites(user.id)
        
        if bpm in favorites:
            remove_from_favorites(user.id, bpm)
            await query.answer("Удалено из избранного", show_alert=False)
        else:
            add_to_favorites(user.id, bpm)
            await query.answer("Добавлено в избранное ⭐️", show_alert=False)
        
        # Обновляем клавиатуру
        keyboard = get_bpm_keyboard(bpm, user.id)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    # Быстрый расчёт из избранного
    elif data.startswith("calc_"):
        bpm = int(data.split("_")[1])
        durations = compute_durations(bpm)
        lfo = compute_lfo_hz(bpm)
        response = format_response(bpm, durations, lfo)
        keyboard = get_bpm_keyboard(bpm, user.id)
        
        await query.message.reply_text(
            response, parse_mode="HTML", reply_markup=keyboard
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Запуск
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    if not TELEGRAM_BOT_TOKEN:
        print("Задайте TELEGRAM_BOT_TOKEN в переменных окружения или в файле .env")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("favorites", favorites_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    async def post_init(app: Application) -> None:
        commands = [
            BotCommand("start", "🎵 Начать работу"),
            BotCommand("help", "📖 Справка"),
            BotCommand("favorites", "⭐️ Избранное"),
        ]
        await app.bot.set_my_commands(commands)
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
