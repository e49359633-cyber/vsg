import asyncio
import logging
import re
import os
import duckdb
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message

# Настройки
TOKEN = '8732991094:AAEy2WRb3BuAB1qqvhD0GtC6VxepdjZiJAs'
DB_FILE = "kundelik_search.duckdb"

# Включаем логирование, чтобы видеть ошибки в панели хостинга
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

def normalize_text(text: str) -> str:
    if not text: return ""
    text = text.lower().strip()
    mapping = {'қ': 'к', 'ң': 'н', 'ғ': 'г', 'ү': 'у', 'ұ': 'у', 'ө': 'о', 'ә': 'а', 'і': 'и'}
    for src, dst in mapping.items():
        text = text.replace(src, dst)
    return re.sub(r'[^\w\s]+', ' ', text)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🔍 **Kundelik OSINT Bot** на aiogram.\nВведите ФИО, ИИН или телефон для поиска.")

@dp.message()
async def search_handler(message: Message):
    query = message.text.strip()
    
    if len(query) < 3:
        await message.answer("⚠️ Запрос слишком короткий (нужно хотя бы 3 символа).")
        return

    if not os.path.exists(DB_FILE):
        await message.answer("🛑 Файл базы данных `kundelik_search.duckdb` не найден на сервере.")
        return

    # Запускаем поиск в отдельном потоке, чтобы бот не "фризил"
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, perform_search, query)

    if not results:
        await message.answer("❌ Ничего не найдено.")
        return

    for r in results:
        resp = (
            f"👤 *ФИО:* {r[0]}\n"
            f"📅 *ДР:* {r[1] or '---'}\n"
            f"📞 *Тел:* {r[2] or '---'}\n"
            f"🆔 *ИИН:* {r[3] or '---'}\n"
            f"🏫 *Школа:* {r[4] or '---'}\n"
            f"👪 *Родитель:* {r[5] or '---'}"
        )
        await message.answer(resp, parse_mode="Markdown")

def perform_search(query: str):
    """Логика поиска в DuckDB"""
    try:
        conn = duckdb.connect(DB_FILE, read_only=True)
        norm_q = normalize_text(query)
        like_val = f"%{norm_q}%"
        
        sql = """
            SELECT fio, birthdate, phone, iin, school, parent 
            FROM clean_students 
            WHERE search_index LIKE ? 
            OR normalized_fio LIKE ? 
            LIMIT 5
        """
        res = conn.execute(sql, [like_val, like_val]).fetchall()
        conn.close()
        return res
    except Exception as e:
        logging.error(f"Search error: {e}")
        return []

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
