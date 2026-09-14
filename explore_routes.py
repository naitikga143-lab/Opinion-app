from flask import Blueprint, render_template, request, jsonify, session, redirect
from explore_model import search_topics, get_all_topics_for_explore
from topic_model import get_topic_heat_count, has_user_heated, time_ago
from recommend_model import get_for_you_topics
from profile_model import get_following_list
import sqlite3

explore_bp = Blueprint('explore', __name__)

DB = 'opinion.db'

def _serialize(topics):
    result = []
    for t in topics:
        result.append({
            'id': t[0],
            'nickname': t[1],
            'title': t[2],
            'description': t[3],
            'heat_count': get_topic_heat_count(t[0]),
            'user_heated': has_user_heated(session.get('nickname'), t[0]),
            'time_ago': time_ago(t[4]),
        })
    return result

@explore_bp.route('/explore')
def explore():
    nickname = session.get('nickname')
    if nickname:
        for_you_topics = get_for_you_topics(nickname)
        print("DEBUG: for_you_topics length =", len(for_you_topics))
    else:
        for_you_topics = _serialize(get_all_topics_for_explore())
    return render_template('explore.html', for_you_topics=for_you_topics)

@explore_bp.route('/explore/search')
def explore_search():
    query = request.args.get('q', '')
    topics = search_topics(query)
    return jsonify(_serialize(topics))

@explore_bp.route('/explore/following')
def explore_following():
    if not session.get('nickname'):
        return redirect('/auth')
    followed = get_following_list(session['nickname'])
    if not followed:
        topics = []
    else:
        placeholders = ','.join('?' for _ in followed)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(f'SELECT * FROM topics WHERE nickname IN ({placeholders}) ORDER BY created_at DESC', followed)
        topics = c.fetchall()
        conn.close()
    return jsonify(_serialize(topics))
