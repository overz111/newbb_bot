import sqlite3
from flask import Flask, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from threading import Thread

# Настройка логирования для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Инициализация Flask
app = Flask(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        first_name TEXT, 
        last_name TEXT, 
        phone TEXT, 
        username TEXT, 
        role TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        title TEXT, 
        image_url TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS prizes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        prize TEXT, 
        date TEXT, 
        status TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS promoter_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        invited_week INTEGER, 
        invited_month INTEGER, 
        qr_code TEXT, 
        activation_date TEXT
    )''')
    conn.commit()
    conn.close()

# Telegram-бот
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id, first_name, username, role) VALUES (?, ?, ?, ?)", 
                 (user.id, user.first_name, user.username, 'guest'))
        conn.commit()
    conn.close()
    
    keyboard = [[InlineKeyboardButton("Открыть приложение", web_app={"url": "http://localhost:5000"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать в NewBB!", reply_markup=reply_markup)

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE id = ?", (user.id,))
    role = c.fetchone()
    if role and role[0] == 'admin':
        args = context.args
        if len(args) >= 2:
            title, image_url = args[0], args[1]
            c.execute("INSERT INTO events (title, image_url) VALUES (?, ?)", (title, image_url))
            conn.commit()
            await update.message.reply_text("Событие добавлено!")
        else:
            await update.message.reply_text("Укажите название и URL изображения: /add_event Название URL")
    else:
        await update.message.reply_text("Доступ запрещен!")
    conn.close()

# Flask-роуты
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    init_db()
    # Запуск Flask в отдельном потоке
    Thread(target=lambda: app.run(debug=True, port=5000, use_reloader=False)).start()
    # Запуск бота
    # application = Application.builder().token("YOUR_BOT_TOKEN").build()
    # application.add_handler(CommandHandler("start", start))
    # application.add_handler(CommandHandler("add_event", add_event))
    # application.run_polling(allowed_updates=Update.ALL_TYPES)