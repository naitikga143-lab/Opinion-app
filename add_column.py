import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM topics")
print("Total topics:", c.fetchone())
c.execute("SELECT COUNT(DISTINCT topic_id) FROM user_interactions WHERE nickname='narayan' AND action IN ('comment', 'conclusion_support')")
print("Seen deep:", c.fetchone())
conn.close()