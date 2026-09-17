
import sqlite3
from helper import get_db

DB = 'opinion.db'
conn = get_db()
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='replies'")
exists = c.fetchone() is not None

desired_cols = ['id', 'comment_id', 'parent_reply_id', 'nickname', 'created_at', 'edited', 'reply_text', 'likes', 'dislikes']
old_data = []

if exists:
    existing_cols = [row[1] for row in c.execute("PRAGMA table_info(replies)").fetchall()]

    select_parts = []
    for col in desired_cols:
        if col in existing_cols:
            select_parts.append(col)
        elif col == 'reply_text':
            select_parts.append("'' AS reply_text")
        elif col in ('likes', 'dislikes', 'edited'):
            select_parts.append(f"0 AS {col}")
        else:
            select_parts.append(f"NULL AS {col}")

    c.execute(f"SELECT {', '.join(select_parts)} FROM replies")
    old_data = c.fetchall()
    c.execute("DROP TABLE replies")

c.execute('''
    CREATE TABLE replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER NOT NULL,
        parent_reply_id INTEGER,
        nickname TEXT NOT NULL,
        created_at TEXT,
        edited INTEGER DEFAULT 0,
        reply_text TEXT,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0
    )
''')

if old_data:
    c.executemany(
        "INSERT INTO replies (id, comment_id, parent_reply_id, nickname, created_at, edited, reply_text, likes, dislikes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        old_data
    )

conn.commit()
conn.close()
print("replies table fully fixed - reply_text, likes, dislikes now included")