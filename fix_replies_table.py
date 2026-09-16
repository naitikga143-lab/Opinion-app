import sqlite3

DB = 'opinion.db'

conn = sqlite3.connect(DB)

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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER NOT NULL,
        parent_reply_id INTEGER,
        nickname TEXT NOT NULL,
        created_at TEXT,
        edited INTEGER DEFAULT 0
    )
''')

if old_data:
    c.executemany(
        "INSERT INTO replies (id, comment_id, parent_reply_id, nickname, reply_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        old_data
    )

conn.commit()
conn.close()
print("replies table fully fixed - parent_reply_id nullable + edited column added")