import sqlite3

DB = 'opinion.db'

def get_all_users():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('''
        SELECT user_id, nickname, email, banned, created_at, last_active
        FROM users ORDER BY created_at DESC
    ''')
    users = c.fetchall()
    conn.close()
    return users

def ban_user(user_id, ban=1):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('UPDATE users SET banned = %s WHERE user_id = %s', (ban, user_id))
    conn.commit()
    conn.close()

def delete_court_entry(entry_id, item_type, item_id):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()

    posted_by = None
    if item_type == 'topic':
        c.execute('SELECT nickname FROM topics WHERE id=%s', (item_id,))
        row = c.fetchone()
        posted_by = row[0] if row else None

        c.execute('SELECT id FROM issues WHERE topic_id=%s', (item_id,))
        issue_ids = [row[0] for row in c.fetchall()]
        for iid in issue_ids:
            c.execute('DELETE FROM comments WHERE issue_id=%s', (iid,))
        c.execute('DELETE FROM issues WHERE topic_id=%s', (item_id,))
        c.execute('DELETE FROM topics WHERE id=%s', (item_id,))

    elif item_type == 'issue':
        c.execute('SELECT nickname FROM issues WHERE id=%s', (item_id,))
        row = c.fetchone()
        posted_by = row[0] if row else None

        c.execute('DELETE FROM comments WHERE issue_id=%s', (item_id,))
        c.execute('DELETE FROM issues WHERE id=%s', (item_id,))

    elif item_type == 'comment':
        c.execute('SELECT nickname FROM comments WHERE id=%s', (item_id,))
        row = c.fetchone()
        posted_by = row[0] if row else None

        c.execute('DELETE FROM comments WHERE id=%s', (item_id,))

    c.execute('SELECT reason1, reason1_by, reason2, reason2_by, reason3, reason3_by FROM court_reasons WHERE entry_id=%s', (entry_id,))
    reason_row = c.fetchone()

    c.execute('DELETE FROM court_entries WHERE id=%s', (entry_id,))
    c.execute('DELETE FROM court_reasons WHERE entry_id=%s', (entry_id,))

    conn.commit()
    conn.close()

    return posted_by, reason_row

def retain_court_entry(entry_id, item_type, item_id):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()

    if item_type == 'topic':
        c.execute('UPDATE topics SET retain_count = retain_count + 1 WHERE id=%s', (item_id,))
    elif item_type == 'issue':
        c.execute('UPDATE issues SET retain_count = retain_count + 1 WHERE id=%s', (item_id,))
    elif item_type == 'comment':
        c.execute('UPDATE comments SET retain_count = retain_count + 1 WHERE id=%s', (item_id,))

    c.execute('DELETE FROM court_entries WHERE id=%s', (entry_id,))
    c.execute('DELETE FROM court_reasons WHERE entry_id=%s', (entry_id,))

    conn.commit()
    conn.close()