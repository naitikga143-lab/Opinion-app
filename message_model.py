import sqlite3
from datetime import datetime

DB = 'opinion.db'

def init_message_tables():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        )
    ''')

    try:
        c.execute('ALTER TABLE notifications ADD COLUMN link TEXT')
    except sqlite3.OperationalError:
        conn.rollback()

    try:
        c.execute('ALTER TABLE notifications ADD COLUMN read_at TIMESTAMP')
    except sqlite3.OperationalError:
        conn.rollback()

    c.execute('''
        CREATE TABLE IF NOT EXISTS notif_checkpoints (
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            notification_id INTEGER,
            checkpoint_time TIMESTAMP,
            PRIMARY KEY (entity_type, entity_id)
        )
    ''')

    conn.commit()
    conn.close()

def add_notification(nickname, message, link=None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = datetime.now()
    c.execute('INSERT INTO notifications (nickname, message, link, created_at) VALUES (?, ?, ?, ?)', (nickname, message, link, now))
    conn.commit()
    conn.close()

def get_all_notifications(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, message, created_at, is_read, link FROM notifications WHERE nickname=? ORDER BY created_at DESC', (nickname,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_unread_count(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM notifications WHERE nickname=? AND is_read=0', (nickname,))
    count = c.fetchone()[0]
    conn.close()
    return count

def mark_all_read(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:?')
    c.execute('UPDATE notifications SET is_read=1, read_at=? WHERE nickname=? AND is_read=0', (now,nickname))
    conn.commit()
    conn.close()

def notify_with_checkpoint(nickname, entity_type, entity_id, message, link=None, window_days=3):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = datetime.now()

    c.execute(
        'SELECT notification_id, checkpoint_time FROM notif_checkpoints WHERE entity_type=? AND entity_id=?',
        (entity_type, entity_id)
    )
    tracker = c.fetchone()

    if tracker:
        notif_id, checkpoint_str = tracker
        try:
            checkpoint_time = datetime.strptime(checkpoint_str, "%Y-%m-%d %H:%M:?.%f")
        except ValueError:
            checkpoint_time = datetime.strptime(checkpoint_str, "%Y-%m-%d %H:%M:?")

        if (now - checkpoint_time).days >= window_days:
            c.execute('INSERT INTO notifications (nickname, message, link, created_at) VALUES (?, ?, ?, ?)', (nickname, message, link, now))
            new_id = c.lastrowid
            c.execute(
                'UPDATE notif_checkpoints SET notification_id=?, checkpoint_time=? WHERE entity_type=? AND entity_id=?',
                (new_id, now, entity_type, entity_id)
            )
        else:
            c.execute('UPDATE notifications SET message=?, link=?, is_read=0, created_at=? WHERE id=?', (message, link, now, notif_id))

            c.execute('UPDATE notif_checkpoints SET checkpoint_time=? WHERE entity_type=? AND entity_id=?', (now, entity_type, entity_id))
    else:
        c.execute('INSERT INTO notifications (nickname, message, link, created_at) VALUES (?, ?, ?, ?)', (nickname, message, link, now))
        new_id = c.lastrowid
        c.execute(
            'INSERT INTO notif_checkpoints (entity_type, entity_id, notification_id, checkpoint_time) VALUES (?, ?, ?, ?)',
            (entity_type, entity_id, new_id, now)
        )

    conn.commit()
    conn.close()

def delete_notification(notif_id, nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('DELETE FROM notifications WHERE id=? AND nickname=?', (notif_id, nickname))
    conn.commit()
    conn.close()

def delete_all_notifications(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('DELETE FROM notifications WHERE nickname=?', (nickname,))
    conn.commit()
    conn.close()