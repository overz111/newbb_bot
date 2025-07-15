from flask import Flask, jsonify, request
import sqlite3
import pyqrcode
import io
import base64
import logging

# Настройка логирования для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def get_events():
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute("SELECT * FROM events")
    events = [{'id': row[0], 'title': row[1], 'image_url': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(events)

@app.route('/profile', methods=['POST'])
def get_profile():
    data = request.json
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (data['user_id'],))
    user = c.fetchone()
    if not user:
        return jsonify({})
    c.execute("SELECT invited_week, invited_month FROM promoter_stats WHERE user_id = ?", (data['user_id'],))
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

@app.route('/save_prize', methods=['POST'])
def save_prize():
    data = request.json
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute("INSERT INTO prizes (user_id, prize, date, status) VALUES (?, ?, datetime('now'), 'active')", 
             (data['user_id'], data['prize']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/prizes', methods=['POST'])
def get_prizes():
    data = request.json
    conn = sqlite3.connect('newbb.db')
    c = conn.cursor()
    c.execute("SELECT id, prize, date FROM prizes WHERE user_id = ? AND status = 'active' AND date > datetime('now', '-7 days')", 
             (data['user_id'],))
    prizes = [{'id': row[0], 'prize': row[1], 'expiry': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(prizes)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json
    qr = pyqrcode.create(data['prize_id'])  # Исправлено: pyqrcode.create вместо py Mew QRCode
    buffer = io.BytesIO()
    qr.png(buffer, scale=10)
    qr_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')
    return jsonify({'qr_url': qr_url})

if __name__ == '__main__':
    app.run(debug=True, port=5000)