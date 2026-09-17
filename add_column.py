import sqlite3

DB = 'opinion.db'

conn = sqlite3.connect(DB)
c = conn.cursor()
print(conn.execute("PRAGMA table_info(replies)").fetchall())
