import psycopg2
import os
import re

DB = 'opinion.db'

def search_topics(query):
    """
    Word-prefix search: 'cri' matches any topic jiske title mein
    koi word 'cri' se start hota ho (cria, crib, cric, crid...)
    Case-insensetive.
    """
    query = query.strip().lower()
    if not query:
        return get_all_topics_for_explore()

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT * FROM topics ORDER BY created_at DESC')
    all_topics = c.fetchall()
    conn.close()

    pattern = re.compile(r'\b' + re.escape(query), re.IGNORECASE)

    matched = []
    for topic in all_topics:
        title = topic[2]
        if pattern.search(title):
            matched.append(topic)

    return matched

def get_all_topics_for_explore():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    c = conn.cursor()
    c.execute('SELECT * FROM topics ORDER BY created_at DESC')
    topics = c.fetchall()
    conn.close()
    return topics