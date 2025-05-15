from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_babel import Babel, gettext
import requests
import random
import sqlite3
from datetime import datetime
import json
import os
from models import init_db, save_quote, get_history, vote_quote
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'
app.config['LANGUAGES'] = {
    'en': 'English',
    'ru': 'Русский'
}

babel = Babel(app)
init_db()

# API источники с поддержкой языков
QUOTE_APIS = {
    'en': [
        "https://api.quotable.io/random",
        "https://favqs.com/api/qotd",
        "https://zenquotes.io/api/random"
    ],
    'ru': [
        "https://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=ru",
        "https://programming-quotes-api.herokuapp.com/quotes/random",
        "https://geek-jokes.sameerkumar.website/api?format=json"
    ]
}

# Запасные цитаты для каждого языка
BACKUP_QUOTES = {
    'en': [
        "Stay hungry, stay foolish. — Steve Jobs",
        "The only way to do great work is to love what you do. — Steve Jobs",
        "Life is what happens when you're busy making other plans. — John Lennon"
    ],
    'ru': [
        "Мысли позитивно — и мир станет лучше. — Неизвестный автор",
        "Код — это поэзия, а программист — поэт. — Анонимный разработчик",
        "Ошибки — это ступени к мастерству. — Мудрый программист"
    ]
}

@babel.localeselector
def get_locale():
    # Проверяем язык в сессии
    if 'language' in session:
        return session['language']
    # Возвращаем язык из заголовков запроса или дефолтный
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys())

def load_translations():
    translations = {}
    for lang in app.config['LANGUAGES']:
        try:
            with open(f'translations/{lang}.json', 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
        except FileNotFoundError:
            print(f"Translation file for {lang} not found")
            translations[lang] = {}
    return translations

TRANSLATIONS = load_translations()

def translate(key, lang=None):
    lang = lang or get_locale()
    return TRANSLATIONS.get(lang, {}).get(key, key)

def get_random_quote(lang=None):
    lang = lang or get_locale()
    try:
        api_url = random.choice(QUOTE_APIS[lang])
        response = requests.get(api_url, timeout=3)
        response.raise_for_status()
        
        data = response.json()
        
        # Обработка разных форматов API
        if "quotable.io" in api_url:
            quote = f"{data['content']} — {data['author']}"
        elif "favqs.com" in api_url:
            quote = f"{data['quote']['body']} — {data['quote']['author']}"
        elif "zenquotes.io" in api_url:
            quote = f"{data[0]['q']} — {data[0]['a']}"
        elif "forismatic.com" in api_url:
            quote = f"{data['quoteText'].strip()} — {data['quoteAuthor'] or 'Неизвестный автор'}"
        else:
            quote = random.choice(BACKUP_QUOTES[lang])
        
        return quote.strip()
    except Exception as e:
        print(f"Ошибка при получении цитаты: {e}")
        return random.choice(BACKUP_QUOTES[lang])
    
@app.context_processor
def inject_locale():
    return {'get_locale': get_locale}

@app.route('/')
def index():
    if 'quote' not in session:
        session['quote'] = get_random_quote()
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html', 
                         quote=session['quote'],
                         translate=translate)

@app.route('/new-quote', methods=['POST'])
def new_quote():
    lang = request.json.get('language', get_locale())
    quote = get_random_quote(lang)
    session['quote'] = quote
    
    # Сохраняем в историю
    if 'history' not in session:
        session['history'] = []
    session['history'].insert(0, {
        'text': quote,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Сохраняем в БД
    if 'user_id' in session:
        save_quote(session['user_id'], quote)
    
    return jsonify({
        'quote': quote,
        'message': translate('quote_updated')
    })

@app.route('/vote', methods=['POST'])
def vote():
    if 'user_id' not in session:
        return jsonify({'error': translate('login_required')}), 401
    
    quote = request.json.get('quote')
    vote_type = request.json.get('vote')  # 'like' or 'dislike'
    
    if not quote or vote_type not in ['like', 'dislike']:
        return jsonify({'error': translate('invalid_request')}), 400
    
    vote_quote(session['user_id'], quote, vote_type)
    return jsonify({'message': translate('vote_recorded')})

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    quotes = get_history(session['user_id'])
    return render_template('history.html', 
                         quotes=quotes,
                         translate=translate)

@app.route('/change-language/<language>')
def change_language(language):
    if language in app.config['LANGUAGES']:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))

DATABASE = 'users.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        db.commit()

init_db()

# Декоратор для проверки аутентификации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите для доступа к этой странице', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Валидация email
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# Валидация пароля
def is_valid_password(password):
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        errors = []

        # Валидация данных
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')
        
        if not is_valid_email(email):
            errors.append('Введите корректный email')
        
        if not is_valid_password(password):
            errors.append('Пароль должен содержать минимум 8 символов, включая цифры и заглавные буквы')
        
        if password != confirm_password:
            errors.append('Пароли не совпадают')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        try:
            with get_db() as db:
                # Проверка на существующего пользователя
                existing_user = db.execute(
                    'SELECT id FROM users WHERE username = ? OR email = ?',
                    (username, email)
                ).fetchone()

                if existing_user:
                    flash('Пользователь с таким именем или email уже существует', 'danger')
                    return render_template('register.html')

                # Создание нового пользователя
                db.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                    (username, email, generate_password_hash(password))
                )
                db.commit()

                flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
                return redirect(url_for('login'))

        except sqlite3.Error as e:
            flash(f'Ошибка базы данных: {str(e)}', 'danger')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db() as db:
            user = db.execute(
                'SELECT * FROM users WHERE username = ?',
                (username,)
            ).fetchone()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Вы успешно вошли в систему!', 'success')
                return redirect(url_for('index'))
            
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)