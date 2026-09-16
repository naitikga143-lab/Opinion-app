import sqlite3

DB = 'opinion.db'

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM topics")
print("Total topics:", c.fetchone())
c.execute("SELECT COUNT(DISTINCT topic_id) FROM user_interactions WHERE nickname='narayan' AND action IN ('comment', 'conclusion_support')")
print("Seen deep:", c.fetchone())
conn.close()