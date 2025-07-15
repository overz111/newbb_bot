import psycopg2
from psycopg2 import sql
from flask import Flask, render_template, jsonify, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import pyqrcode
import io
import base64
import logging
import os

# Настройка логирования для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)

# Проверка переменных окружения
def check_env_vars():
    required_vars = ['PG_DBNAME', 'PG_USER', 'PG_PASSWORD', 'PG_HOST', 'PG_PORT', 'TELEGRAM_BOT_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        raise ValueError(f"Не заданы переменные окружения: {', '.join(missing_vars)}")

# Функция для подключения к базе данных
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('PG_DBNAME'),
            user=os.getenv('PG_USER'),
            password=os.getenv('PG_PASSWORD'),
            host=os.getenv('PG_HOST'),
            port=os.getenv('PG_PORT')
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        raise

# Инициализация базы данных
def init_db():
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY, 
            first_name TEXT, 
            last_name TEXT, 
            phone TEXT, 
            username TEXT, 
            role TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY, 
            title TEXT, 
            image_url TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS prizes (
            id SERIAL PRIMARY KEY, 
            user_id BIGINT, 
            prize TEXT, 
            date TEXT, 
            status TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS promoter_stats (
            id SERIAL PRIMARY KEY, 
            user_id BIGINT, 
            invited_week INTEGER, 
            invited_month INTEGER, 
            qr_code TEXT, 
            activation_date TEXT
        )''')
        conn.commit()
        logger.info("База данных успешно инициализирована")
    except psycopg2.Error as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
    finally:
        if conn is not None:
            conn.close()

# Telegram-бот
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = %s", (user.id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, first_name, username, role) VALUES (%s, %s, %s, %s)", 
                      (user.id, user.first_name, user.username, 'guest'))
            conn.commit()
            logger.info(f"Пользователь {user.id} добавлен в базу данных")
        conn.close()
        
        keyboard = [[InlineKeyboardButton("Открыть приложение", web_app={"url": os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')})]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Добро пожаловать в NewBB!", reply_markup=reply_markup)
    except psycopg2.Error as e:
        logger.error(f"Ошибка базы данных в /start: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = %s", (user.id,))
        role = c.fetchone()
        if role and role[0] == 'admin':
            args = context.args
            if len(args) >= 2:
                title, image_url = args[0], args[1]
                c.execute("INSERT INTO events (title, image_url) VALUES (%s, %s)", (title, image_url))
                conn.commit()
                logger.info(f"Событие '{title}' добавлено пользователем {user.id}")
                await update.message.reply_text("Событие добавлено!")
            else:
                await update.message.reply_text("Укажите название и URL изображения: /add_event Название URL")
        else:
            await update.message.reply_text("Доступ запрещен!")
        conn.close()
    except psycopg2.Error as e:
        logger.error(f"Ошибка базы данных в /add_event: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Flask-роуты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def get_events():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM events")
        events = [{'id': row[0], 'title': row[1], 'image_url': row[2]} for row in c.fetchall()]
        conn.close()
        return jsonify(events)
    except psycopg2.Error as e:
        logger.error(f"Ошибка базы данных в /events: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/profile', methods=['POST'])
def get_profile():
    data = request.json
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = %s", (data['user_id'],))
        user = c.fetchone()
        if not user:
            return jsonify({})
        c.execute("SELECT invited_week, invited_month FROM promoter_stats WHERE user_id = %s", (data['user_id'],))
        stats = c.fetchone() or (0, 0)
        conn.close()
        return jsonify({
            'first_name': user[1],
            'last_name': user[2],
            'phone': user[3],
            'username': user[4],
            'role': user[5],
            'invited_week': stats[0],
            'invited_month': stats[1]
        })
    except psycopg2.Error as e:
        logger.error(f"Ошибка базы данных в /profile: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/save_prize', methods=['POST'])
def save_prize():
    data = request.json
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO prizes (user_id, prize, date, status) VALUES (%s, %s, CURRENT_TIMESTAMP, 'active')", 
                  (data['user_id'], data['prize']))
        conn.commit()
        conn.close()
        logger.info(f"Приз сохранен для пользователя {data['user_id']}")
        return jsonify({'status': 'success'})
    except psycopg2.Error as e:
        logger.error(f"Ошибка базы данных в /save_prize: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/prizes', methods=['POST'])
def get_prizes():
    data = request.json
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, prize, date FROM prizes WHERE user_id = %s AND status = 'active' AND date > CURRENT_TIMESTAMP - INTERVAL '7 days'", 
                  (data['user_id'],))
        prizes = [{'id': row[0], 'prize': row[1], 'expiry': row[2]} for row in c.fetchall()]
        conn.close()
        return jsonify(prizes)
    except psycopg2.Error as e:
        logger.error(f"Ошибка базы данных в /prizes: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json
    try:
        qr = pyqrcode.create(str(data['prize_id']))
        buffer = io.BytesIO()
        qr.png(buffer, scale=10)
        qr_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')
        return jsonify({'qr_url': qr_url})
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}")
        return jsonify({'error': 'QR generation error'}), 500

@app.route('/webhook/<token>', methods=['POST'])
async def webhook(token):
    try:
        if token == os.getenv('8180271263:AAHY3SFRqw2KeF-O9cblWA5TPPt0XhHApeY'):
            update = Update.de_json(request.get_json(), application.bot)
            await application.process_update(update)
            return jsonify({'status': 'ok'})
        return jsonify({'status': 'error'}), 403
    except Exception as e:
        logger.error(f"Ошибка в вебхуке: {e}")
        return jsonify({'error': 'Webhook error'}), 500

if __name__ == '__main__':
    try:
        check_env_vars()  # Проверка переменных окружения
        init_db()  # Инициализация базы данных
        # Инициализация Telegram-бота
        application = Application.builder().token(os.getenv('8180271263:AAHY3SFRqw2KeF-O9cblWA5TPPt0XhHApeY')).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add_event", add_event))
        
        # Настройка вебхука
        port = int(os.getenv('PORT', 5000))
        webhook_url = f"{os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')}/webhook/{os.getenv('8180271263:AAHY3SFRqw2KeF-O9cblWA5TPPt0XhHApeY')}"
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=f"/webhook/{os.getenv('8180271263:AAHY3SFRqw2KeF-O9cblWA5TPPt0XhHApeY')}",
            webhook_url=webhook_url
        )
        logger.info(f"Вебхук запущен на порту {port}")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        raise