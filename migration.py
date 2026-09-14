import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
c = conn.cursor()

for col in ['reason1_upvotes', 'reason2_upvotes', 'reason3_upvotes']:
    try:
        c.execute(f"ALTER TABLE court_reasons ADD COLUMN {col} INTEGER DEFAULT 0")
    except psycopg2.errors.DuplicateColumn as e:
        conn.rollback()
        print(f"{col} already exists, skipping")

c.execute('''
    CREATE TABLE IF NOT EXISTS court_reason_upvotes (
        id SERIAL PRIMARY KEY,
        entry_id INTEGER NOT NULL,
        slot_num INTEGER NOT NULL,
        nickname TEXT NOT NULL,
        UNIQUE(entry_id, slot_num, nickname)
    )
''')

try:
    c.execute("ALTER TABLE court_entries ADD COLUMN justification TEXT")
except psycopg2.errors.DuplicateColumn as e:
    conn.rollback()
    print("justification already exists, skipping")

conn.commit()
conn.close()
print("Done")