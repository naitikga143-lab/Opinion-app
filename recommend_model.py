import sqlite3
import re
import random
import math
from datetime import datetime, timedelta
from collections import Counter
from topic_model import get_topic_heat_count, has_user_heated, time_ago

DB = 'opinion.db'
STOPWORDS = {'the', 'is', 'a', 'an', 'of', 'to', 'and', 'in', 'on', 'for', 'with', 'this', 'that', 'ka', 'ki', 'hai', 'ko'}

def _tokenize(text):
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

def get_user_interest_profile(nickname, days=30):
    """
    User ke last N din ke interactions se ek keyword-weight profile banta hai.
    Zyada weight wale actions (comment, court_join) us topic ke keywords ko
    zyada importance denge.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute('''
        SELECT t.title, t.description, ui.weight
        FROM user_interactions ui
        JOIN topics t ON t.id = ui.topic_id
        WHERE ui.nickname = ? AND ui.created_at >= ?
    ''', (nickname, since))
    rows = c.fetchall()
    conn.close()

    profile = Counter()
    for title, desc, weight in rows:
        for word in _tokenize(f"{title} {desc}"):
            profile[word] += weight
    return profile

def _recency_score(created_at_str, half_life_hours=48):
    """"Exponential decay - jitna purana topic, utna kam score."""
    try:
        created = datetime.fromisoformat(created_at_str)
    except Exception:
        return 0.3
    age_hours = (datetime.utcnow() - created).total_seconds() / 3600
    return math.exp( -age_hours * math.log(2) / half_life_hours)


def _dominant_keyword(title, desc, interest_profile):
    """Topic ka sabse strong theme-word nikaalta hai -- diversity grouping ke liye."""
    words = _tokenize(f"{title} {desc}")
    if not words:
        return None
    if interest_profile:
        best = max(words, key=lambda w: interest_profile.get(w, 0))
        if interest_profile.get(best, 0) > 0:
            return best
        return words[0]

def _is_recent(created_at_str, max_age_hours=72):
    """Exploration ke liye sirf genuinely fresh topics allow karte hai."""
    try:
        created = datetime.fromisoformat(created_at_str)
    except Exception:
        return False
    age_hours = (datetime.utcnow() - created).total_seconds() / 3600
    return age_hours <= max_age_hours

def _diversify(candidates, limit, max_per_keywords=2, window=4):
    """
    Greedy re-ranking: score-order ko largely preserve karta hai,
    lekin same dominant-keyword wale topics ko ek chote window mein
    over-repeat hone se rokta hai.
    """
    pool = candidates.copy()
    result = []
    recent_keywords = []

    while pool and len(result) < limit:
        chosen_idx = None
        for i, cand in enumerate(pool):
            kw = cand['keyword']
            count_in_window = recent_keywords[-window:].count(kw)
            if kw is None or count_in_window < max_per_keywords:
                chosen_idx = i
                break
        if chosen_idx is None:
            chosen_idx = 0

        chosen = pool.pop(chosen_idx)
        result.append(chosen)
        recent_keywords.append(chosen['keyword'])
    return result
    
def get_for_you_topics(nickname, limit=20, explore_ratio=0.25):
    print("CP1: function start")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, nickname, title, description, created_at FROM topics ORDER BY created_at DESC LIMIT 500')
    all_topics = c.fetchall()
    print("CP2: all_topics fetched, count =", len(all_topics))

    c.execute('SELECT DISTINCT topic_id FROM user_interactions WHERE nickname=? AND action IN ("comment","conclusion_support")', (nickname,))
    seen_deep = {r[0] for r in c.fetchall()}
    conn.close()
    print("CP3: seen_deep fetched, count =", len(seen_deep))

    interest_profile = get_user_interest_profile(nickname)
    print("CP4: interest_profile ready, cold_start =", len(interest_profile) == 0)
    cold_start = len(interest_profile) == 0

    scored = []
    for topic_id, tnick, title, desc, created_at in all_topics:
        if topic_id in seen_deep:
            continue

        words = _tokenize(f"{title} {desc}")
        interest_score = math.log1p(sum(interest_profile.get(w, 0) for w in words))
        recency = _recency_score(created_at)
        jitter = random.uniform(0, 0.05)

        if cold_start:
            final_score = (0.7 * recency) + jitter
        else:
            final_score = (0.65 * interest_score) + (0.30 * recency) + jitter

        keyword = _dominant_keyword(title, desc, interest_profile)

        scored.append({
            'score': final_score,
            'id': topic_id, 'nickname': tnick, 'title': title,
            'description': desc, 'created_at': created_at,
            'keyword': keyword,
            'heat_count': get_topic_heat_count(topic_id),
            'user_heated': has_user_heated(nickname, topic_id),
            'time_ago': time_ago(created_at)
        })

    print("CP5: scoring loop done, scored_count =", len(scored))
    scored.sort(key=lambda x: x['score'], reverse=True)

    explore_count = int(limit * explore_ratio)
    main_count = limit - explore_count

    top_ranked = scored[:main_count]
    rest = scored[main_count:]

    fresh_pool = [t for t in rest if _is_recent(t['created_at'])]
    random.shuffle(fresh_pool)
    explore_picks = fresh_pool[:explore_count]

    used_ids = {t['id'] for t in top_ranked} | {t['id'] for t in explore_picks}
    missing = explore_count - len(explore_picks)
    if missing > 0:
        fallback_pool = [t for t in rest if t['id'] not in used_ids]

        explore_picks += fallback_pool[:missing]

    combined = top_ranked + explore_picks
    combined.sort(key=lambda x: x['score'], reverse=True)

    final_feed = _diversify(combined, limit=limit)

    print("CP6: about to return final feed")
    return [
        {k: v for k, v in item.items() if k != 'score' and k != 'keyword'}
        for item in final_feed
    ]