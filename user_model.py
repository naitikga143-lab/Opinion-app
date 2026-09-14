import psycopg2
import os
import bcrypt


def init_db():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id TEXT UNIQUE,
            nickname TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def add_user(nickname, email, password):
    hashed = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt(rounds=12)
    )

    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM users')
        count = c.fetchone()[0] + 1

        user_id = f'{count:04d}'

        c.execute(
            'INSERT INTO users (user_id, nickname, email, password) VALUES (%s, %s, %s, %s)',
            (user_id, nickname, email, hashed.decode('utf-8'))
        )

        conn.commit()
        conn.close()
        return True
    
    except psycopg2.IntegrityError:
        return False
    
def get_user(email, password):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()

    c.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = c.fetchone()
    conn.close()

    if user is None:
        return None

    hashed = user[4]
    if isinstance(hashed, str):
        hashed = hashed.encode('utf-8')
    if bcrypt.checkpw(password.encode('utf-8'), hashed):
        return user
        
    return None

def search_user(nickname):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT nickname FROM users WHERE nickname = %s', (nickname,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_status(nickname):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT banned FROM users WHERE nickname = %s', (nickname,))
    user = c.fetchone()
    conn.close()
    return user[0] if user else 0

