import sqlite3

DB = 'opinion.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn