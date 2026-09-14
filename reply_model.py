import psycopg2
import os
from profanity_filter import contains_abuse
from datetime import datetime

DB = 'opinion.db'


def init_replies_table():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS replies (
              id SERIAL PRIMARY KEY,
              comment_id INTEGER NOT NULL,
              parent_reply_id INTEGER NOT NULL,
              nickname TEXT NOT NULL,
              reply_text TEXT NOT NULL,
              created_at TEXT,
              edited INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_reply(comment_id, nickname, reply_text, parent_reply_id=None):
    if contains_abuse(reply_text):
        return {'error': 'abusive_language'}
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute(
        '''INSERT INTO replies (comment_id, parent_reply_id, nickname, reply_text, created_at) VALUES (%s, %s, %s, %s, datetime("now"))''',
        (comment_id, parent_reply_id, nickname, reply_text)
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {'success': True, 'id': new_id}

def get_replies(comment_id):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT * FROM replies WHERE comment_id = %s ORDER BY created_at ASC', (comment_id,))
    replies = c.fetchall()
    conn.close()
    return replies

def get_reply_count(comment_id):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM replies WHERE comment_id = %s', (comment_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def delete_reply(reply_id, nickname):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('DELETE FROM replies WHERE id = %s AND nickname = %s', (reply_id, nickname))
    conn.commit()
    conn.close()

def update_reply(reply_id, nickname, new_text):
    if contains_abuse(new_text):
        return {'error': 'abusive_language'}
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT id FROM replies WHERE id = %s AND nickname = %s', (reply_id, nickname))
    owns = c.fetchone()
    if owns:
        c.execute('UPDATE replies SET reply_text = %s, edited = 1 WHERE id = %s AND nickname = %s',
                  (new_text, reply_id, nickname))
        conn.commit()
    conn.close()
    return {'success': True}

def time_ago_replies(timestamp_str):
    if not timestamp_str:
        return ""

    if isinstance(timestamp_str, datetime):
        created = timestamp_str
    else:
        try:
            created = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
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

def vote_reply(reply_id, nickname, vote):
    if vote not in ('like', 'dislike'):
        return {'error': 'invalid_vote'}

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()

    c.execute('SELECT vote FROM reply_votes WHERE reply_id = %s AND nickname = %s', (reply_id, nickname))
    existing = c.fetchone()

    if existing:
        old_vote = existing[0]
        if old_vote == vote:
            c.execute('DELETE FROM reply_votes WHERE reply_id = %s AND nickname = %s', (reply_id, nickname))
            c.execute(f'UPDATE replies SET {vote}s = {vote}s - 1 WHERE id = %s', (reply_id,))
            new_user_vote = None
        else:
            c.execute('UPDATE reply_votes SET vote = %s WHERE reply_id = %s AND nickname = %s',
                      (vote, reply_id, nickname))
            c.execute(f'UPDATE replies SET {old_vote}s = {old_vote}s - 1 WHERE id = %s', (reply_id,))
            c.execute(f'UPDATE replies SET {vote}s = {vote}s + 1 WHERE id = %s', (reply_id,))
            new_user_vote = vote
    else:
        c.execute('INSERT INTO reply_votes (reply_id, nickname, vote) VALUES (%s, %s, %s)',
                  (reply_id, nickname, vote))
        c.execute(f'UPDATE replies SET {vote}s = {vote}s + 1 WHERE id = %s', (reply_id,))
        new_user_vote = vote

    conn.commit()

    c.execute('SELECT likes, dislikes FROM replies WHERE id = %s', (reply_id,))
    likes, dislikes = c.fetchone()
    conn.close()

    return {'success': True, 'likes': likes, 'dislikes': dislikes, 'user_vote': new_user_vote}

def get_user_votes_for_comment(comment_id, nickname):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('''  
        SELECT rv.reply_id, rv.vote FROM reply_votes rv
        JOIN replies r ON r.id = rv.reply_id
        WHERE r.comment_id = %s AND rv.nickname = %s
    ''', (comment_id, nickname))
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def sort_replies(replies_list):
    replies_list.sort(key=lambda r: (r['likes'] - r['dislikes']), reverse=True)
    for r in replies_list:
        if r['children']:
            sort_replies(r['children'])
    return replies_list

def get_reply_owner(reply_id):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT nickname FROM replies WHERE id=%s', (reply_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_reply_meta(reply_id):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT nickname, comment_id FROM replies WHERE id=%s', (reply_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'nickname': row[0], 'comment_id': row[1]}
    return None