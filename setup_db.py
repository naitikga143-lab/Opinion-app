import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB = 'opinion.db'

def run_migration_step(conn, c, sql, params=None):
    try:
        if params:
            c.execute(sql, params)
        else:
            c.execute(sql)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Migration step skipped/failed: {e}")

def run_migrations():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    
    run_migration_step(conn, c, 'ALTER TABLE comments ADD COLUMN replies_enabled INTEGER DEFAULT 0')

    run_migration_step(conn, c, 'ALTER TABLE topics ADD COLUMN retain_count INTEGER DEFAULT 0')

    run_migration_step(conn, c, 'ALTER TABLE issues ADD COLUMN retain_count INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE issues ADD COLUMN edited INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE comments ADD COLUMN retain_count INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE comments ADD COLUMN edited INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE replies ADD COLUMN reply_text INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE court_entries ADD COLUMN category TEXT')
    
    run_migration_step(conn, c, 'ALTER TABLE court_entries ADD COLUMN delete_votes INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE topics ADD COLUMN heat_count INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, '''
            CREATE TABLE IF NOT EXISTS topic_heats (
                topic_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                UNIQUE(topic_id, nickname)
            )
        ''')
    
    run_migration_step(conn, c, 'ALTER TABLE notifications ADD COLUMN read_at TIMESTAMP')
    
    run_migration_step(conn, c, 'ALTER TABLE replies ADD COLUMN likes INTEGER DEFAULT 0')
    
    run_migration_step(conn, c, 'ALTER TABLE replies ADD COLUMN dislikes INTEGER DEFAULT 0')

    run_migration_step(conn, c, "ALTER TABLE court_delete_votes ADD COLUMN vote_type TEXT DEFAULT 'delete'")
    
    run_migration_step(conn, c, "ALTER TABLE court_entries ADD COLUMN keep_votes INTEGER DEFAULT 0")
    
    run_migration_step(conn, c, '''
            CREATE TABLE IF NOT EXISTS reply_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reply_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                vote TEXT NOT NULL,
                UNIQUE(reply_id, nickname)
            )
        ''')

    conn.close()
    print("Setup complete")

def init_issue_votes_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS issue_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            vote TEXT NOT NULL,
            UNIQUE(issue_id, nickname)
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_migrations()