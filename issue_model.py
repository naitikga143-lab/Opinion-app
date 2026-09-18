import sqlite3
from profanity_filter import contains_abuse
from message_model import notify_with_checkpoint
from datetime import datetime

from helper import get_db

DB = 'opinion.db'

def init_issues_table():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS issues (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              topic_id INTEGER NOT NULL,
              nickname TEXT NOT NULL,
              description TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def init_votes_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              issue_id INTEGER NOT NULL,
              nickname TEXT NOT NULL,
              vote TEXT NOT NULL,
              UNIQUE(issue_id, nickname)
        )
    ''')
    conn.commit()
    conn.close()

def add_issue(topic_id, nickname, description):
    if contains_abuse(description):
        return {'error': 'abusive_language'}
    
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO issues (topic_id, nickname, description) VALUES (?, ?, ?)',
        (topic_id, nickname, description)
    )
    conn.commit()
    issue_id = c.lastrowid

    c.execute('SELECT nickname FROM topics WHERE id=?', (topic_id,))
    owner_row = c.fetchone()
    owner_nickname = owner_row[0] if owner_row else None
    conn.close()

    if owner_nickname and owner_nickname != nickname:
        try:
            message = f"{nickname} ne aapke topic pe ek issue raise kiya hai"
            notify_with_checkpoint(
                nickname=owner_nickname,
                entity_type='issue',
                entity_id=issue_id,
                message=message,
                link=f"/discuss/topic/{topic_id}#issue-{issue_id}"
            )
        except Exception as e:
            print("issue notify failed:", e)

    return {'success': True}

def get_issues(topic_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM issues WHERE topic_id = ? ORDER BY created_at ASC', (topic_id,))
    issues = c.fetchall()
    conn.close()
    return issues

def get_issue_by_id(issue_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM issues WHERE id = ?', (issue_id,))
    issue = c.fetchone()
    conn.close()
    return issue

def delete_issue_db(issue_id, nickname):
    conn = get_db()
    c =  conn.cursor()
    c.execute('SELECT id FROM comments WHERE issue_id = ?', (issue_id,))
    comment_ids = [row[0] for row in c.fetchall()]

    for cid in comment_ids:
        c.execute('DELETE FROM replies WHERE comment_id = ?', (cid,))

    c.execute('DELETE FROM comments WHERE issue_id = ?', (issue_id,))

    c.execute('DELETE FROM issue_votes WHERE issue_id = ?', (issue_id,))

    c.execute('DELETE FROM issues WHERE id = ? AND nickname = ?', (issue_id, nickname))

    conn.commit()
    conn.close()

def update_issue(issue_id, nickname, new_description):
    if contains_abuse(new_description):
        return {'error': 'abusive_language'}
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM issues WHERE id = ? AND nickname = ?', (issue_id, nickname))
    owns = c.fetchone()
    if owns:
        c.execute('UPDATE issues SET description = ?, edited = 1 WHERE id = ? AND nickname = ?',
                  (new_description, issue_id, nickname))
        conn.commit()
    conn.close()
    return {'success': True}

def add_vote(issue_id,  nickname, vote):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute('SELECT vote FROM issue_votes WHERE issue_id = ? AND nickname = ?', (issue_id, nickname))
        existing = c.fetchone()

        if existing:
            if existing[0] == vote:
                c.execute('DELETE FROM issue_votes WHERE issue_id = ? AND nickname = ?', (issue_id, nickname))
                action = 'removed'
            else:
                c.execute('UPDATE issue_votes SET vote = ? WHERE issue_id = ? AND nickname = ?', (vote, issue_id, nickname))
                action = 'changed'
        else:
            c.execute('INSERT INTO issue_votes (issue_id, nickname, vote) VALUES (?, ?, ?)', (issue_id, nickname, vote))
            action = 'added'
    
        conn.commit()
        return action
    finally:
        conn.close()

def get_votes_for_issue(issue_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM issue_votes WHERE issue_id = ?', (issue_id,))
    total = c.fetchone()[0]
    conn.close()
    return {'total': total}

    
def get_user_vote_for_issues(issue_id, nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT vote FROM issue_votes WHERE issue_id = ? AND nickname = ?', (issue_id, nickname))
    row = c.fetchone()
    conn.close()
    return row

def get_issue_retain_count(issue_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT retain_count FROM issues WHERE id=?', (issue_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_top_conclusions_comments(issue_id, limit=10):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT c.id, c.nickname, c.comment, COUNT(cv.id) as conclusion_count,
            COALESCE(SUM(CASE WHEN v.vote = 1 THEN 1 ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN v.vote = -1 THEN 1 ELSE 0 END), 0) AS net_votes
        FROM comments c
        LEFT JOIN conclusion_votes cv ON cv.comment_id = c.id
        LEFT JOIN votes v ON v.comment_id = c.id
        WHERE c.issue_id = ?
        GROUP BY c.id
        HAVING COUNT(cv.id) > 0
        ORDER BY conclusion_count DESC, net_votes DESC
        LIMIT ?
    ''', (issue_id, limit))
    rows = c.fetchall()
    conn.close()
    return [
        {'id': r[0], 'nickname': r[1], 'comment': r[2], 'conclusion_count': r[3]}
        for r in rows
    ]

def get_issues_sorted_by_votes(topic_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT i.*,
               COALESCE(SUM(CASE WHEN v.vote = 'upvote' THEN 1 ELSE 0 END), 0) -
               COALESCE(SUM(CASE WHEN v.vote = 'downvote' THEN 1 ELSE 0 END), 0) AS net_votes
        FROM issues i
        LEFT JOIN issue_votes v ON v.issue_id = i.id
        WHERE i.topic_id = ?
        GROUP BY i.id
        ORDER BY net_votes DESC, i.created_at ASC
    ''', (topic_id,))
    issues = c.fetchall()
    conn.close()
    return issues

def time_ago_issues(timestamp_str):
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

def get_issue_owner(issue_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT nickname FROM issues WHERE id=?', (issue_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_issue_topic_id(issue_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT topic_id FROM issues WHERE id=?', (issue_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_users_issues(nickname):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, topic_id, description, created_At FROM issues WHERE nickname = ? ORDER BY created_at DESC', (nickname,))
    issues = c.fetchall()
    conn.close()
    return issues