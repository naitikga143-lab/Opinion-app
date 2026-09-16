import sqlite3

DB = 'opinion.db'

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA table_info(comments)")
for row in c.fetchall():
    print(row)
