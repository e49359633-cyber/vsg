import telebot
import duckdb
import re
import os

# Конфигурация
TOKEN = '8732991094:AAEy2WRb3BuAB1qqvhD0GtC6VxepdjZiJAs'
DB_FILE = "kundelik_search.duckdb"

bot = telebot.TeleBot(TOKEN)

def normalize_text(text):
    if not text: return ""
    text = text.lower().strip()
    mapping = {'қ': 'к', 'ң': 'н', 'ғ': 'г', 'ү': 'у', 'ұ': 'у', 'ө': 'о', 'ә': 'а', 'і': 'и'}
    for src, dst in mapping.items():
        text = text.replace(src, dst)
    return re.sub(r'[^\w\s]+', ' ', text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🔍 Бот готов к поиску по базе Kundelik. Введите ФИО или ИИН.")

@bot.message_handler(func=lambda message: True)
def search_handler(message):
    query = message.text.strip()
    
    if len(query) < 3:
        bot.reply_to(message, "⚠️ Слишком короткий запрос (минимум 3 символа).")
        return

    if not os.path.exists(DB_FILE):
        bot.reply_to(message, "🛑 База данных еще не создана на хостинге. Запустите сначала процесс индексации.")
        return

    try:
        # Подключаемся к базе (только чтение)
        conn = duckdb.connect(DB_FILE, read_only=True)
        
        norm_query = normalize_text(query)
        like_val = f"%{norm_query}%"
        
        # Твой SQL запрос
        sql = """
            SELECT fio, birthdate, phone, iin, school, parent 
            FROM clean_students 
            WHERE search_index LIKE ? 
            OR normalized_fio LIKE ? 
            LIMIT 5
        """
        
        results = conn.execute(sql, [like_val, like_val]).fetchall()
        conn.close()

        if not results:
            bot.send_message(message.chat.id, "❌ Ничего не найдено.")
            return

        for r in results:
            response = (
                f"👤 *ФИО:* {r[0]}\n"
                f"📅 *ДР:* {r[1] or '---'}\n"
                f"📞 *Тел:* {r[2] or '---'}\n"
                f"🆔 *ИИН:* {r[3] or '---'}\n"
                f"🏫 *Школа:* {r[4] or '---'}\n"
                f"👪 *Родитель:* {r[5] or '---'}"
            )
            bot.send_message(message.chat.id, response, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, f"🛑 Ошибка поиска: {str(e)}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
