import psycopg2
import os
from topic_model import DB, time_ago

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
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute(f'''
        SELECT id, nickname, title, description, created_at, heat_count
        FROM topics t
        {where}
        ORDER BY heat_count DESC, created_at DESC
        LIMIT %s
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
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
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
        LIMIT %s
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