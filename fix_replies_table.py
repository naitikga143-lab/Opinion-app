import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))

c = conn.cursor()

c.execute("SELECT to_regclass('public.replies')")
exists = c.fetchone() is not None

old_data =[]
if exists:
    c.execute("SELECT id, comment_id, parent_reply_id, nickname, reply_text, created_at FROM replies")
    old_data = c.fetchall()
    c.execute("DROP TABLE replies")

c.execute('''
    CREATE TABLE replies (
        id SERIAL PRIMARY KEY,
        comment_id INTEGER NOT NULL,
        parent_reply_id INTEGER,
        nickname TEXT NOT NULL,
        created_at TEXT,
        edited INTEGER DEFAULT 0
    )
''')

if old_data:
    c.executemany(
        "INSERT INTO replies (id, comment_id, parent_reply_id, nickname, reply_text, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        old_data
    )

conn.commit()
conn.close()
print("replies table fully fixed - parent_reply_id nullable + edited column added")