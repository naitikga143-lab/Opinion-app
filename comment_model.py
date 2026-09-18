import sqlite3
from profanity_filter import contains_abuse
from datetime import datetime

from helper import get_db

DB = 'opinion.db'

def init_comments_table():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              issue_id INTEGER NOT NULL,
              topic_id INTEGER NOT NULL,
              nickname TEXT NOT NULL,
              comment TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              comment_id INTEGER NOT NULL,
              nickname TEXT NOT NULL,
              vote INTEGER NOT NULL,
              UNIQUE(comment_id, nickname)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS conclusion_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            UNIQUE(comment_id, nickname)
        )
    ''')
    conn.commit()
    conn.close()

def add_comment(issue_id, topic_id, nickname, comment):
    if contains_abuse(comment):
        return {'error': 'abusive_language'}
    
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO comments (issue_id, topic_id, nickname, comment, replies_enabled) VALUES (?, ?, ?, ?, 1)',
        (issue_id, topic_id, nickname, comment)
    )
    conn.commit()
    comment_id = c.lastrowid
    conn.close()
    return {'success': True, 'comment_id': comment_id}

def get_comments(issue_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT c.*,
               (SELECT COUNT(*) FROM conclusion_votes cv WHERE cv.comment_id = c.id) AS conclusion_count,
               (SELECT COUNT(*) FROM votes v WHERE v.comment_id = c.id AND v.vote = 1) AS like_count,
               (SELECT COUNT(*) FROM votes v WHERE v.comment_id = c.id AND v.vote = -1) AS dislike_count
        FROM comments c
        WHERE c.issue_id = ?
        ORDER BY conclusion_count DESC, (like_count - dislike_count) DESC, c.created_at ASC
    ''', (issue_id,))
    comments = c.fetchall()
    conn.close()
    return comments

def get_comments_by_id(comment_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_comment(comment_id, nickname, new_comment):
    if contains_abuse(new_comment):
        return {'error': 'abusive_language'}
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM comments WHERE id = ? AND nickname = ?', (comment_id, nickname))
    owns = c.fetchone()
    if owns:
        c.execute('UPDATE comments SET comment = ?, edited = 1 WHERE id = ? AND nickname = ?',
                  (new_comment, comment_id, nickname))
        conn.commit()
    conn.close()
    return {'success': True}

def delete_comment(comment_id, nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM comments WHERE id = ? AND nickname = ?', (comment_id, nickname))
    owns_comment = c.fetchone()

    if owns_comment:
        c.execute('DELETE FROM replies WHERE comment_id = ?', (comment_id,))
        c.execute('DELETE FROM comments WHERE id = ? AND nickname = ?', (comment_id, nickname))
        conn.commit()
        
    conn.close()

def toggle_vote(comment_id, nickname, vote):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT vote FROM votes WHERE comment_id = ? AND nickname = ?', (comment_id, nickname))
    existing = c.fetchone()
    if existing:
        if int(existing[0]) == vote:
            c.execute('DELETE FROM votes WHERE comment_id = ? AND nickname = ?', (comment_id, nickname))
            new_user_vote = 0
            action = 'removed'
        else:
            c.execute('UPDATE votes SET vote = ? WHERE comment_id = ? AND nickname = ?', (vote, comment_id, nickname))
            new_user_vote = vote
            action = 'changed'
    else:
        c.execute('INSERT INTO votes (comment_id, nickname, vote) VALUES (?, ?, ?)', (comment_id, nickname, vote))
        new_user_vote = vote
        action = 'added'

    conn.commit()
    conn.close()
    return new_user_vote, action

def get_votes(comment_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT vote FROM votes WHERE comment_id = ?', (comment_id,))
    votes = c.fetchall()
    conn.close()
    likes = sum(1 for v in votes if int(v[0]) == 1)
    dislikes = sum(1 for v in votes if int(v[0]) == -1)
    return likes, dislikes

def get_user_vote(comment_id, nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT vote FROM votes WHERE comment_id = ? AND nickname = ?', (comment_id, nickname))
    vote = c.fetchone()
    conn.close()
    return int(vote[0]) if vote else 0

def get_comment_retain_count(comment_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT retain_count FROM comments WHERE id=?', (comment_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def toggle_conclusion_vote(comment_id, nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM conclusion_votes WHERE comment_id=? AND nickname=?', (comment_id, nickname))
    existing = c.fetchone()

    if existing:
        c.execute('DELETE FROM conclusion_votes WHERE comment_id=? AND nickname=?', (comment_id, nickname))
        new_state = False
    else:
        c.execute('INSERT INTO conclusion_votes (comment_id, nickname) VALUES (?, ?)', (comment_id, nickname))
        new_state = True

    conn.commit()
    conn.close()
    return new_state

def get_conclusion_count(comment_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM conclusion_votes WHERE comment_id=?', (comment_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def has_supported_conclusion(comment_id, nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM conclusion_votes WHERE comment_id=? AND nickname=?', (comment_id, nickname))
    row = c.fetchone()
    conn.close()
    return row is not None

def toggle_replies(comment_id, nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, replies_enabled FROM comments WHERE id = ? AND nickname = ?', (comment_id, nickname))
    row = c.fetchone()
    if not row:
        conn.close()
        return None

    new_state = 0 if row[1] == 1 else 1
    c.execute('UPDATE comments SET replies_enabled = ? WHERE id = ?', (new_state, comment_id))

    if new_state == 0:
        c.execute('SELECT id FROM replies WHERE comment_id = ?', (comment_id,))
        reply_ids = [r[0] for r in c.fetchall()]
        c.execute('DELETE FROM replies WHERE comment_id = ?', (comment_id,))

    conn.commit()
    conn.close()
    return new_state

def time_ago_comments(timestamp_str):
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

def get_comment_owner(comment_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT nickname FROM comments WHERE id=?', (comment_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
