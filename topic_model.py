import sqlite3
from issue_model import get_issues_sorted_by_votes, get_top_conclusions_comments
from profanity_filter import contains_abuse
from message_model import notify_with_checkpoint
from datetime import datetime

DB = 'opinion.db'

def init_topics_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS topics (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              nickname TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def init_interactions_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''   
        CREATE TABLE IF NOT EXISTS user_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            topic_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            weight REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_topic(nickname, title, description):
    if contains_abuse(title) or contains_abuse(description):
        return {'error': 'abusive_language'}
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        'INSERT INTO topics (nickname, title, description) VALUES (?, ?, ?)',
        (nickname, title, description)
    )
    conn.commit()
    conn.close()
    return {'success': True}

def get_all_topics():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM topics ORDER BY created_at DESC')
    topics = c.fetchall()
    conn.close()
    return topics

def get_topic_by_id(topic_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM topics WHERE id = ?', (topic_id,))
    topic = c.fetchone()
    conn.close()
    return topic

def get_topic_retain_count(topic_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT retain_count FROM topics WHERE id=?', (topic_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_topic_conclusions(topic_id):
    issues = get_issues_sorted_by_votes(topic_id)
    conclusions = []
    for issue in issues:
        top = get_top_conclusions_comments(issue[0], 1)
        if top:
            conclusions.append({
                'issue_id': issue[0],
                'issue_description': issue[3],
                'comment': top[0]
            })
    return conclusions

def get_topic_heat_count(topic_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT heat_count FROM topics WHERE id=?', (topic_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def has_user_heated(nickname, topic_id):
    if not nickname:
        return False
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT 1 FROM topic_heats WHERE topic_id=? AND nickname=?', (topic_id, nickname))
    row = c.fetchone()
    conn.close()
    return row is not None

def toggle_topic_heat(nickname, topic_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT 1 FROM topic_heats WHERE topic_id=? AND nickname=?', (topic_id, nickname))
    exists = c.fetchone()

    if exists:
        c.execute('DELETE FROM topic_heats WHERE topic_id=? AND nickname=?', (topic_id, nickname))
        c.execute('UPDATE topics SET heat_count = heat_count - 1 WHERE id=?', (topic_id,))
        heated = False
    else:
        c.execute('INSERT INTO topic_heats (topic_id, nickname) VALUES (?, ?)', (topic_id, nickname))
        c.execute('UPDATE topics SET heat_count = heat_count + 1 WHERE id=?', (topic_id,))
        heated = True

    conn.commit()
    c.execute('SELECT heat_count FROM topics WHERE id=?', (topic_id,))
    count = c.fetchone()[0]

    c.execute('SELECT nickname FROM topics WHERE id=?', (topic_id,))
    owner_row = c.fetchone()
    owner_nickname = owner_row[0] if owner_row else None
    conn.close()

    if heated:
        try:
            message = f"Your topic got {count} heats"
            notify_with_checkpoint(
                nickname=owner_nickname,
                entity_type='topic',
                message=message,
                entity_id=topic_id,
                link=f"/discuss#topic-{topic_id}"
            )
        except Exception as e:
            print("notify_topic_heat failed:", e)

    return {'heated': heated, 'count': count}

def time_ago(timestamp_str):
    if not timestamp_str:
        return ""

    if isinstance(timestamp_str, datetime):
        created = timestamp_str
    else:
        try:
            created = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:?")
        except ValueError:
            created = datetime.fromisoformat(timestamp_str)
            
    diff = datetime.utcnow() - created

    if diff.total_seconds() < 0:
            return "just now"
    
    days = diff.days
    if days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            return "just now" if minutes == 0 else f"{minutes} min ago"
        return f"{hours} hour{'s' if hours > 1 else ''}ago"
    elif days == 1:
        return "1 day ago"
    else:
        return f"{days} days ago"

def record_interaction(nickname, topic_id, action, weight):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT INTO user_interactions (nickname, topic_id, action, weight) VALUES (?, ?, ?, ?)',
              (nickname, topic_id, action, weight))
    conn.commit()
    conn.close()

