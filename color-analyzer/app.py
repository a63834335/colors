# -*- coding: utf-8 -*-
import os
import uuid
import sqlite3
import hashlib
import secrets
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory)
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'database.sqlite3')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif'}
MIN_COLORS, MAX_COLORS = 1, 16

app = Flask(__name__)
app.secret_key = 'uchebny-proekt-den-3'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 МБ
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- База данных ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL)''')

# ---------- Пароли ----------
def make_hash(password):
    salt = secrets.token_hex(16)
    return salt + '$' + hashlib.sha256((salt + password).encode()).hexdigest()

def check_hash(password, stored):
    salt, h = stored.split('$', 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == h

# ---------- Названия цветов  ----------
COLOR_NAMES = [
    ((0, 0, 0), 'чёрный'), ((255, 255, 255), 'белый'), ((128, 128, 128), 'серый'),
    ((211, 211, 211), 'светло-серый'), ((64, 64, 64), 'тёмно-серый'),
    ((255, 0, 0), 'красный'), ((139, 0, 0), 'тёмно-красный'), ((255, 165, 0), 'оранжевый'),
    ((255, 255, 0), 'жёлтый'), ((255, 215, 0), 'золотой'), ((0, 128, 0), 'зелёный'),
    ((144, 238, 144), 'светло-зелёный'), ((0, 100, 0), 'тёмно-зелёный'),
    ((128, 128, 0), 'оливковый'), ((0, 0, 255), 'синий'), ((173, 216, 230), 'голубой'),
    ((0, 0, 139), 'тёмно-синий'), ((0, 255, 255), 'бирюзово-голубой'),
    ((64, 224, 208), 'бирюзовый'), ((128, 0, 128), 'фиолетовый'),
    ((238, 130, 238), 'светло-фиолетовый'), ((255, 192, 203), 'розовый'),
    ((139, 69, 19), 'коричневый'), ((245, 245, 220), 'бежевый'), ((128, 0, 0), 'бордовый'),
]

def color_name(rgb):
    best = min(COLOR_NAMES, key=lambda c: sum((a - b) ** 2 for a, b in zip(c[0], rgb)))
    return best[1]

# ---------- Анализ изображения ----------
def extract_palette(img, n):
    # прозрачный фон заменяем на белый
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGBA')
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert('RGB')
    img.thumbnail((120, 120))           # уменьшаем для скорости
    quantized = img.quantize(colors=n)  # квантование до n цветов
    flat = quantized.convert('RGB')
    total = flat.width * flat.height
    counts = flat.getcolors(maxcolors=total + 1) or []
    counts.sort(key=lambda c: c[0], reverse=True)  # по убыванию доли
    return [
        {'hex': '#%02x%02x%02x' % rgb, 'name': color_name(rgb),
         'percent': round(count * 100 / total, 1)}
        for count, rgb in counts[:n]
    ]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Сначала войдите в систему.', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper

# ---------- Регистрация / вход / выход ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if len(username) < 3 or len(username) > 20:
            flash('Имя пользователя: от 3 до 20 символов.', 'error')
        elif len(password) < 4:
            flash('Пароль должен быть не короче 4 символов.', 'error')
        else:
            db = get_db()
            exists = db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone()
            if exists:
                flash('Такое имя пользователя уже занято.', 'error')
            else:
                db.execute('INSERT INTO users(username, password_hash) VALUES (?,?)',
                           (username, make_hash(password)))
                db.commit()
                flash('Регистрация успешна! Теперь войдите.', 'success')
                db.close()
                return redirect(url_for('login'))
            db.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        db.close()
        if user and check_hash(password, user['password_hash']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль.', 'error')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    pending = session.get('pending')
    if pending:  # удаляем несохранённый загруженный файл
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, pending['file']))
        except OSError:
            pass
    session.clear()
    return redirect(url_for('login'))

# ---------- Главная: загрузка и анализ ----------
@app.route('/')
@login_required
def index():
    return render_template('index.html', pending=session.get('pending'))

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    # проверка количества цветов
    raw = request.form.get('colors_count', '').strip()
    if not raw.isdigit():
        flash('Введите количество цветов целым числом.', 'error')
        return redirect(url_for('index'))
    count = int(raw)
    if not (MIN_COLORS <= count <= MAX_COLORS):
        flash(f'Количество цветов должно быть от {MIN_COLORS} до {MAX_COLORS}.', 'error')
        return redirect(url_for('index'))
    # проверка файла
    file = request.files.get('photo')
    if file is None or file.filename == '':
        flash('Выберите фото для загрузки.', 'error')
        return redirect(url_for('index'))
    if not allowed_file(file.filename):
        flash('Неподдерживаемый формат. Разрешено: ' + ', '.join(sorted(ALLOWED_EXTENSIONS)), 'error')
        return redirect(url_for('index'))
    ext = file.filename.rsplit('.', 1)[1].lower()
    name = f'{uuid.uuid4().hex}.{ext}'
    path = os.path.join(UPLOAD_FOLDER, name)
    file.save(path)
    # пробуем открыть как картинку (защита от «фальшивых» изображений)
    try:
        with Image.open(path) as img:
            img.load()
            palette = extract_palette(img, count)
    except Exception:
        os.remove(path)
        flash('Не удалось открыть файл: похоже, это не изображение.', 'error')
        return redirect(url_for('index'))
    if not palette:
        os.remove(path)
        flash('Не удалось выделить цвета из этого изображения.', 'error')
        return redirect(url_for('index'))
    old = session.get('pending')  # удаляем прошлый несохранённый файл
    if old:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, old['file']))
        except OSError:
            pass
    session['pending'] = {'file': name, 'colors': palette}
    return redirect(url_for('index'))

@app.route('/uploads/<path:name>')
@login_required
def uploads(name):
    return send_from_directory(UPLOAD_FOLDER, name)

@app.route('/palettes')
@login_required
def palettes():
    return render_template('palettes.html')


@app.errorhandler(413)
def too_large(e):
    flash('Файл слишком большой. Ограничение — 10 МБ.', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)