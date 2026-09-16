import sqlite3
import datetime
from message_model import add_notification

DB = 'opinion.db'

def init_follows_table():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower TEXT NOT NULL,
        following TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(follower, following)
    )''')
    conn.commit()
    conn.close()

def get_users_topics(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM topics WHERE nickname = ? ORDER BY created_at DESC', (nickname,))
    topics = c.fetchall()
    conn.close()
    return topics

def delete_topic(topic_id, nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT nickname, created_at FROM topics WHERE id = ?', (topic_id,))
    topic = c.fetchone()

    if not topic or topic[0] != nickname:
        conn.close()
        return False
    
    created = datetime.datetime.strptime(topic[1], '%Y-%m-%d %H:%M:?')
    if (datetime.datetime.now() - created).days >= 7:
        conn.close()
        return False
    
    c.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
    conn.commit()
    conn.close()
    return True

def follow_user(follower, following):
    if follower == following:
        return False
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO follows (follower, following) VALUES (?, ?)', (follower, following))
        conn.commit()
        add_notification(following, f"{follower} is now following you", link=f"/profile/{follower}")
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False
    finally:
        conn.close()

def unfollow_user(follower, following):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('DELETE FROM follows WHERE follower = ? AND following = ?',(follower, following))
    conn.commit()
    conn.close()

def is_following(follower, following):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT 1 FROM follows WHERE follower = ? AND following = ?', (follower, following))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_following_list(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT following FROM follows WHERE follower = ?', (nickname,))
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def get_followers_count(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM follows WHERE following = ?', (nickname,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_following_count(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM follows WHERE follower = ?', (nickname,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_followers_list(nickname):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT follower FROM follows WHERE following = ?', (nickname,))
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result