import sqlite3
from topic_model import DB, time_ago

DB = 'opinion.db'

from helper import get_db

VALID_PERIODS = ('day', 'month', 'year', 'all')

def _period_clause(period, column='created_at'):
    """Returns a SQL WHERE fragment (or '') restricting rows to the period."""
    if period == 'day':
        return f"WHERE {column} >= datetime('now', '-1 day')"
    if period == 'month':
        return f"WHERE strftime('%Y-%m', {column}) = strftime('%Y-%m', 'now')"
    if period == 'year':
        return f"WHERE strftime('%Y', {column}) = strftime('%Y', 'now')"
    return ''

def get_most_heated_topics(limit=20, period='all'):
    """Topics created within `period`, sorted by heat_count (highest first)."""
    where = _period_clause(period, 't.created_at')
    conn = get_db()
    c = conn.cursor()
    c.execute(f'''
        SELECT id, nickname, title, description, created_at, heat_count
        FROM topics t
        {where}
        ORDER BY heat_count DESC, created_at DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()

    topics = []
    for r in rows:
        topics.append({
            'id': r[0],
            'nickname': r[1],
            'title': r[2],
            'description': r[3],
            'created_at': time_ago(r[4]),
            'heat_count': r[5] or 0
        })
    return topics

def get_most_clicked_topics(limit=20, period='all'):
    """Topics created within `period`, sorted by number of 'click' interactions."""
    where = _period_clause(period, 't.created_at')
    conn = get_db()
    c = conn.cursor()
    c.execute(f'''
        SELECT t.id, t.nickname, t.title, t.description, t.created_at,
               COUNT(ui.id) AS click_count
        FROM topics t
        LEFT JOIN user_interactions ui
            ON ui.topic_id = t.id AND ui.action = 'click'
        {where}
        GROUP BY t.id
        ORDER BY click_count DESC, t.created_at DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()

    topics = []
    for r in rows:
        topics.append({
            'id': r[0],
            'nickname': r[1],
            'title': r[2],
            'description': r[3],
            'created_at': time_ago(r[4]),
            'click_count': r[5] or 0
        })
    return topics

def add_interaction_target_columns():
    conn = get_db()
    c = conn.cursor()
    c.execute("PRAGMA table_info(user_interactions)")
    cols = [r[1] for r in c.fetchall()]
    if 'target_type' not in cols:
        c.execute("ALTER TABLE user_interactions ADD COLUMN target_type TEXT DEFAULT 'topic'")
    if 'target_id' not in cols:
        c.execute("ALTER TABLE user_interactions ADD COLUMN target_id INTEGER")
    c.execute("UPDATE user_interactions SET target_id = topic_id WHERE target_id IS NULL")
    conn.commit()
    conn.close()

CLICK_COOLDOWN = '-1 hour'

def record_click(nickname, topic_id, target_type='topic', target_id=None):
    if target_id is None:
        target_id = topic_id

    conn = get_db()
    c = conn.cursor()
    try:
        if target_type == 'issue':
            c.execute("SELECT nickname FROM issues WHERE id = ?", (target_id,))
        else:
            c.execute("SELECT nickname FROM topics WHERE id = ?", (target_id,))
        row = c.fetchone()
        if not row or row[0] == nickname:
            return False

        c.execute('''
            SELECT 1 FROM user_interactions
            WHERE nickname = ?
              AND action = 'click' 
              AND target_type = ?
              AND target_id = ?
              AND created_at >= datetime('now', ?)
            LIMIT 1
        ''', (nickname, target_type, target_id, CLICK_COOLDOWN))
        if c.fetchone():
            return False

        c.execute('''
            INSERT INTO user_interactions
                (nickname, topic_id, action, weight, target_type, target_id)
            VALUES (?, ?, 'click', 1, ?, ?)
        ''', (nickname, topic_id, target_type, target_id))
        conn.commit()
        return True
    finally:
        conn.close()