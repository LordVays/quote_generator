import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица цитат
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Таблица голосов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quote_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL,  -- 'like' or 'dislike'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (quote_id) REFERENCES quotes (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_quote(user_id, quote_text):
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO quotes (user_id, text) VALUES (?, ?)', 
                  (user_id, quote_text))
    conn.commit()
    conn.close()

def get_history(user_id):
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT text, created_at FROM quotes 
    WHERE user_id = ? 
    ORDER BY created_at DESC
    LIMIT 50
    ''', (user_id,))
    quotes = [{'text': row[0], 'timestamp': row[1]} for row in cursor.fetchall()]
    conn.close()
    return quotes

def vote_quote(user_id, quote_text, vote_type):
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    
    # Находим или создаем цитату
    cursor.execute('SELECT id FROM quotes WHERE text = ?', (quote_text,))
    quote = cursor.fetchone()
    
    if not quote:
        cursor.execute('INSERT INTO quotes (user_id, text) VALUES (?, ?)', 
                      (user_id, quote_text))
        quote_id = cursor.lastrowid
    else:
        quote_id = quote[0]
    
    # Записываем голос
    cursor.execute('''
    INSERT INTO votes (user_id, quote_id, vote_type)
    VALUES (?, ?, ?)
    ''', (user_id, quote_id, vote_type))
    
    conn.commit()
    conn.close()