import sqlite3
from admin_model import retain_court_entry
from datetime import datetime, timedelta
from message_model import add_notification

DB = 'opinion.db'

def init_court_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS court_entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              item_type TEXT NOT NULL,
              item_id INTEGER NOT NULL,
              content TEXT NOT NULL,
              posted_by TEXT,
              reported_by TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(item_type, item_id)
        )
    ''')
    conn.commit()
    conn.close()

def is_already_reported(item_type, item_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id FROM court_entries WHERE item_type=? AND item_id=?', (item_type, item_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_court_entry(item_type, item_id, category, content, posted_by, reported_by):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        'INSERT INTO court_entries (item_type, item_id, category, content, posted_by, reported_by) VALUES (?, ?, ?, ?, ?, ?)',
        (item_type, item_id, category, content, posted_by, reported_by)
    )
    conn.commit()
    entry_id = c.lastrowid
    conn.close()
    return entry_id

def get_court_entries(category):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM court_entries WHERE category=? ORDER BY created_at DESC', (category,))
    entries = c.fetchall()
    conn.close()
    return entries

def add_vote(entry_id, nickname, vote_type): 
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('SELECT 1 FROM court_delete_votes WHERE entry_id=? AND nickname=?', (entry_id, nickname))
    if c.fetchone():
        conn.close()
        return False

    c.execute('INSERT INTO court_delete_votes (entry_id, nickname, vote_type) VALUES (?, ?, ?)', (entry_id, nickname, vote_type))

    column = 'delete_votes' if vote_type == 'delete' else 'keep_votes'
    c.execute(f'UPDATE court_entries SET {column} = {column} + 1 WHERE id=?', (entry_id,))

    conn.commit()
    conn.close()
    return True

def has_user_voted(entry_id, nickname): 
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT 1 FROM court_delete_votes WHERE entry_id=? AND nickname=?', (entry_id, nickname))
    row = c.fetchone()
    conn.close()
    return row is not None

def init_court_reasons_table():     #
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS court_reasons (
            entry_id INTEGER PRIMARY KEY,
            reason1 TEXT, reason1_by TEXT,
            reason2 TEXT, reason2_by TEXT,
            reason3 TEXT, reason3_by TEXT
        )
    ''')
    conn.commit()
    conn.close()

def init_court_delete_votes_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS court_delete_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            UNIQUE(entry_id, nickname)
        )
    ''')
    conn.commit()
    conn.close()

def get_court_reasons(entry_id, nickname=None): 
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT reason1, reason1_by, reason1_upvotes, reason2, reason2_by, reason2_upvotes, reason3, reason3_by, reason3_upvotes FROM court_reasons WHERE entry_id=?', (entry_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        row = (None,) * 9

    result = {}
    for n in range(1, 4):
        base = (n - 1) * 3
        result[f'reason{n}'] = row[base]
        result[f'reason{n}_by'] = row[base + 1]
        result[f'reason{n}_upvotes'] = row[base + 2] or 0
        result[f'reason{n}_has)upvoted'] = has_user_upvoted_reason(entry_id, n, nickname) if nickname else False

    return result

def fill_court_reason_slot(entry_id, slot_num, text, submitted_by): #
    conn = sqlite3.connect(DB) 
    c = conn.cursor()

    c.execute('SELECT reason1, reason2, reason3 FROM court_reasons WHERE entry_id=?', (entry_id,))
    row = c.fetchone()

    if row is None:
        c.execute('INSERT INTO court_reasons (entry_id) VALUES (?)', (entry_id,))
        row = (None, None, None)

    if row[slot_num - 1] is not None:
        conn.close()
        return False

    col = f'reason{slot_num}'
    by_col = f'reason{slot_num}_by'
    c.execute(f'UPDATE court_reasons SET {col}=?, {by_col}=? WHERE entry_id=?', (text, submitted_by, entry_id))
    conn.commit()
    conn.close()
    return True

def get_court_entries_with_vote(category): #
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        SELECT id, item_type, item_id, content, posted_by, reported_by, created_at, category, delete_votes
        FROM court_entries WHERE category=? ORDER BY created_at DESC
    ''', (category,))
    entries = c.fetchall()
    conn.close()
    return entries

def init_court_setting_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS court_settings (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("""
        INSERT INTO court_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT (key) DO NOTHING
    """, ('delete_vote_threshold', '50'))
    conn.commit()
    conn.close()

def get_delete_vote_threshold():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT value FROM court_settings WHERE key='delete_vote_threshold'")
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else 50

def set_delete_vote_threshold(value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE court_settings SET value=? WHERE key='delete_vote_threshold'", (str(value),))
    conn.commit()
    conn.close()

def init_notifications_table():
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
    conn.commit()
    conn.close()

ITEM_LABELS = {
    'topic': 'topic',
    'issue': 'issue',
    'comment': 'comment'
}

MESSAGE_TEMPLATES = {
    'auto_delete': "Aapka {label} mein users ko kuch galat laga, isliye reasons aur voting se unhone aapka comment delete karwaya hai",
    'admin_delete': "Aapka {label} admin ke dwara delete kiya gaya hai.",
}

def build_message(template_key, item_type, reason_text=""):
    label = ITEM_LABELS.get(item_type, 'post')
    msg = MESSAGE_TEMPLATES[template_key].format(label=label)
    return msg + reason_text

def build_reasons_text_from_row(row):
    if not row:
        return ""
    lines = []
    for i in range(3):
        text = row[i*2]
        by = row[i*2 + 1]
        if text:
            lines.append(f"{len(lines)+1}. {text} (by @{by})")
    if not lines:
        return ""
    return "\n\nAapka card delete karne ka reason, jo users ne diya hai:\n" + "\n".join(lines)

def get_notifications(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id message, created_at, is_read FROM notifications WHERE nickname=? AND is_read=0 ORDER BY created_at DESC', (nickname,))
    rows = c.fetchall()
    conn.close()
    return rows

def count_filled_reasons(entry_id): #
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT reason1, reason2, reason3 FROM court_reasons WHERE entry_id=?', (entry_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return 0
    return sum(1 for r in row if r)

def auto_delete_if_threshold_met(entry_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT item_type, item_id, posted_by, delete_votes FROM court_entries WHERE id=?', (entry_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return

    item_type, item_id, posted_by, votes = row
    reasons_filled = count_filled_reasons(entry_id)

    vote_threshold = get_setting('delete_vote_threshold', 50)
    reason_with_vote_threshold = get_setting('delete_reason_with_vote_threshold', 1)
    reason_only_threshold = get_setting('delete_reason_only_threshold', 3)

    condition1 = votes >= vote_threshold and reasons_filled >= reason_with_vote_threshold
    condition2 = reasons_filled >= reason_only_threshold

    if condition1 or condition2:
        _perform_court_auto_delete(entry_id, item_type, item_id, posted_by)

    
def _perform_court_auto_delete(entry_id, item_type, item_id, posted_by):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('SELECT reason1, reason1_by, reason2, reason2_by, reason3, reason3_by FROM court_reasons WHERE entry_id=?', (entry_id,))
    reason_row = c.fetchone()

    if item_type == 'topic':
        c.execute('SELECT id FROM issues WHERE topic_id=?', (item_id,))
        issue_ids = [r[0] for r in c.fetchall()]
        for iid in issue_ids:
            c.execute('DELETE FROM comments WHERE issue_id=?', (iid,))
        c.execute('DELETE FROM issues WHERE topic_id=?', (item_id,))
        c.execute('DELETE FROM topics WHERE id=?', (item_id,))

    elif item_type == 'issue':
        c.execute('DELETE FROM comments WHERE issue_id=?', (item_id,))
        c.execute('DELETE FROM issues WHERE id=?', (item_id,))

    elif item_type == 'comment':
        c.execute('DELETE FROM comments WHERE id=?', (item_id,))

    c.execute('DELETE FROM court_entries WHERE id=?', (entry_id,))
    c.execute('DELETE FROM court_reasons WHERE entry_id=?', (entry_id,))

    conn.commit()
    conn.close()

    if posted_by:
        reasons_text = build_reasons_text_from_row(reason_row)
        add_notification(posted_by, build_message('auto_delete', item_type, reasons_text))

def mark_notifications_read(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:?')
    c.execute('UPDATE notifications SET is_read=1, read_at=? WHERE nickname=? AND is_read=0', (now, nickname,))
    conn.commit()
    conn.close()

def get_setting(key, default):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT value FROM court_settings WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO court_settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def auto_retain_expired_entries():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, item_type, item_id, created_at FROM court_entries')
    entries = c.fetchall()
    conn.close()

    cutoff = datetime.now() - timedelta(days=3)

    for entry_id, item_type, item_id, created_at in entries:
        try:
            created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:?')
        except (ValueError, TypeError):
            continue
        if created_dt <= cutoff:
            retain_court_entry(entry_id, item_type, item_id)

def get_all_notifications(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    cutoff = datetime.now() - timedelta(days=3)
    cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:?')
    c.execute("""
        DELETE FROM notifications
        WHERE nickname=? AND is_read=1
        AND COALESCE(read_at, created_at) <= ?
    """, (nickname, cutoff_str))
    conn.commit()

    c.execute('SELECT id, message, created_at, is_read FROM notifications WHERE nickname=? ORDER BY created_at DESC', (nickname,))
    rows = c.fetchall()
    conn.close()
    return rows

def has_user_submitted_reason(entry_id, nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT reason1_by, reason2_by, reason3_by FROM court_reasons WHERE entry_id=?', (entry_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    return nickname in row

def has_user_upvoted_reason(entry_id, slot_num, nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT 1 FROM court_reason_upvotes WHERE entry_id=? AND slot_num=? AND nickname=?', (entry_id, slot_num, nickname))
    row = c.fetchone()
    conn.close()
    return row is not None

def add_reason_upvote(entry_id, slot_num, nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('SELECT 1 FROM court_reason_upvotes WHERE entry_id=? AND slot_num=? AND nickname=?', (entry_id, slot_num, nickname))
    if c.fetchone():
        conn.close()
        return False

    c.execute('INSERT INTO court_reason_upvotes (entry_id, slot_num, nickname) VALUES (?, ?, ?)', (entry_id, slot_num, nickname))

    col = f'reason{slot_num}_upvotes'
    c.execute(f'UPDATE court_reasons SET {col} = {col} + 1 WHERE entry_id=?', (entry_id,))

    conn.commit()
    conn.close()
    return True

def get_justification(entry_id, nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT posted_by, justification FROM court_entries WHERE id=?', (entry_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {'justification': None, 'is_owner': False}
    posted_by, justification = row
    return {'justification': justification, 'is_owner': (nickname == posted_by) if nickname else False}

def set_justification(entry_id, nickname, text):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT posted_by FROM court_entries WHERE id=?', (entry_id,))
    row = c.fetchone()
    if not row or row[0] != nickname:
        conn.close()
        return False
    c.execute('UPDATE court_entries SET justification=? WHERE id=?', (text, entry_id))
    conn.commit()
    conn.close()
    return True




