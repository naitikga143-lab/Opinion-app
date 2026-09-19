from flask import Blueprint, render_template, jsonify, session, redirect, request
from court_model import (
    get_court_entries, add_vote, get_court_reasons,
    fill_court_reason_slot, auto_delete_if_threshold_met,
    has_user_voted, has_user_submitted_reason, add_reason_upvote, get_justification, set_justification
)
import sqlite3
import unicodedata
from profanity_filter import contains_abuse

court_bp = Blueprint('court_bp', __name__)

DB = 'opinion.db'

@court_bp.route('/court')
def court():
    return render_template('court.html')

@court_bp.route('/court/data/<category>')
def court_data(category):
    from court_model import auto_retain_expired_entries
    auto_retain_expired_entries()
    entries = get_court_entries(category)
    nickname = session.get('nickname')
    result = [
        {
            'id': e[0], 'item_type': e[1], 'item_id': e[2],
            'content': e[3], 'posted_by': e[4], 'reported_by':  e[5], 'created_at': e[6],
            'category': e[7],
            'has_voted': has_user_voted(e[0], nickname) if nickname else False
        }
        for e in entries
    ]
    return jsonify(result)

@court_bp.route('/court/vote/<int:entry_id>', methods=['POST']) 
def court_vote(entry_id):
    if not session.get('nickname'):
        return jsonify(success=False, message='Login karo pehle'), 401

    nickname = session.get('nickname')
    voted = add_vote(entry_id, nickname, 'delete')

    if not voted:
        return jsonify(success=False, message='Aap already vote kar chuke hain'), 409
    
    auto_delete_if_threshold_met(entry_id)
    return jsonify(success=True)

@court_bp.route('/court/keep/<int:entry_id>', methods=['POST'])
def court_keep(entry_id):
    if not session.get('nickname'):
        return jsonify(success=False, message='Login karo pehle'), 401

    nickname = session.get('nickname')
    voted = add_vote(entry_id, nickname, 'keep')

    if not voted:
        return jsonify(success=False, message='Aap already vote kar chuke hain'), 409

    return jsonify(success=True)

@court_bp.route('/court/goto/<item_type>/<int:item_id>')
def court_goto(item_type, item_id):
    if not session.get('nickname'):
        return redirect('/auth')
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if item_type == 'topic':
        conn.close()
        return redirect(f'/discuss#topic-{item_id}')

    elif item_type == 'issue':
        c.execute('SELECT topic_id FROM issues WHERE id=?', (item_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return redirect(f'/discuss/topic/{row[0]}#issue-{item_id}')
        return redirect('/court')

    elif item_type == 'comment':
        c.execute('SELECT issue_id FROM comments WHERE id=?', (item_id,))
        crow = c.fetchone()
        if crow:
            c.execute('SELECT topic_id FROM issues WHERE id=?', (crow[0],))
            irow = c.fetchone()
            conn.close()
            if irow:
                return redirect(f'/discuss/topic/{irow[0]}/issue/{crow[0]}#comment-{item_id}')
            return redirect('/court')

    conn.close()
    return redirect('/court')

@court_bp.route('/court/reasons/<int:entry_id>')
def court_get_reasons(entry_id):
    nickname = session.get('nickname')
    return jsonify(get_court_reasons(entry_id, nickname))

@court_bp.route('/court/reason/<int:entry_id>/<int:slot_num>', methods=['POST'])
def court_submit_reason(entry_id, slot_num):
    if not session.get('nickname'):
        return jsonify(success=False, message='Login karo pehle'), 401

    if slot_num not in (1, 2, 3):
        return jsonify(success=False, message='Invalid slot'), 400

    submitted_by = session.get('nickname')

    if has_user_submitted_reason(entry_id, submitted_by):
        return jsonify(success=False, message='Aap already el reason de chuke hain'), 409

    data = request.get_json()
    text = (data.get('text') or '').strip()

    if not text:
        return jsonify(success=False, message='Reason khaali nahi ho sakta'), 400

    if len(text.split()) > 75:
        return jsonify(success=False, message='Reason 75 words se kam mein likhiye'), 400

    non_emoji = [c for c in text if not unicodedata.category(c).startswith('So') and c.strip()]
    if not non_emoji:
        return jsonify(success=False, message='Sirf emoji nahi submit kar sakte, koi valid reason ho to submit karein'), 400

    if contains_abuse(text):
        return jsonify(success=False, message='Abusive ya hatefull language allow nahi hai'), 400

    filled = fill_court_reason_slot(entry_id, slot_num, text, submitted_by)

    if not filled:
        return jsonify(success=False, message='Ye box full ho chuka hai'), 409
    
    auto_delete_if_threshold_met(entry_id)
    return jsonify(success=True)

#mere ghar mein aaj khana nahi bana hai please koi 2 roti digital walli khilla do

@court_bp.route('/court/reason/upvote/<int:entry_id>/<int:slot_num>', methods=['POST'])
def court_reason_upvote(entry_id, slot_num):
    if not session.get('nickname'):
        return jsonify(success=False, message='Login karo pehle'), 401

    if slot_num not in (1, 2, 3):
        return jsonify(success=False, message='Invalid slot'), 400

    nickname = session.get('nickname')
    upvoted = add_reason_upvote(entry_id, slot_num, nickname)

    if not upvoted:
        return jsonify(success=False, message='Aap already upvote kar chuke hain'), 409

    return jsonify(success=True)

@court_bp.route('/court/justification/<int:entry_id>')
def court_get_justification(entry_id):
    nickname = session.get('nickname')
    return jsonify(get_justification(entry_id, nickname))

@court_bp.route('/court/justification/<int:entry_id>', methods=['POST'])
def court_submit_justification(entry_id):
    if not session.get('nickname'):
        return jsonify(success=False, message='Login karo pehle'), 401

    nickname = session.get('nickname')
    data = request.get_json()
    text = (data.get('text') or '').strip()

    if not text:
        return jsonify(success=True, skipped=True)

    if len(text.split()) > 200:
        return jsonify(success=False, message='Justification 200 words ke andar likhiye'), 400

    if contains_abuse(text):
        return jsonify(success=False, message='Abusive ya hatefull language allow nahi hai'), 400

    saved = set_justification(entry_id, nickname, text)
    if not saved:
        return jsonify(success=False, message='Sirf card ka owner justification de sakta hai'), 403

    return jsonify(success=True)
