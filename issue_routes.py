from flask import Blueprint, render_template, request, redirect, session
from topic_model import get_topic_by_id, record_interaction
from issue_model import get_issue_by_id, get_issue_owner, get_issue_topic_id
from comment_model import (
    get_comments,
    get_votes,
    get_user_vote,
    add_comment,
    get_comments_by_id,
    toggle_vote,
    delete_comment,
    update_comment,
    toggle_conclusion_vote,
    has_supported_conclusion,
    get_conclusion_count,
    toggle_replies,
    get_comment_owner
)
from message_model import notify_with_checkpoint
import re
import unicodedata
from trending_model import record_click

issue_bp = Blueprint('issue_bp', __name__)

@issue_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>')
def issue_detail(topic_id,  issue_id):
    
    topic = get_topic_by_id(topic_id)
    issue = get_issue_by_id(issue_id)
    if not topic or not issue:
        return redirect('/discuss')

    record_click(session['nickname'], topic_id, 'issue', issue_id)
    
    comments = get_comments(issue_id)
    comments_data = []
    for comment in comments:
        likes, dislikes = get_votes(comment[0])
        user_vote = get_user_vote(comment[0], session['nickname'])
        comments_data.append({
            'id': comment[0],
            'nickname': comment[3],
            'comment': comment[4],
            'likes': likes,
            'dislikes': dislikes,
            'user_vote': user_vote,
            'edited': comment[8],
            'conclusion_count': get_conclusion_count(comment[0]),
            'user_supported_conclusion': has_supported_conclusion(comment[0], session['nickname']),
            'replies_enabled': comment[6],
            'created_at': comment[5]
        })

    return render_template('issue.html', topic=topic, issue=issue, comments=comments_data)

@issue_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>/comment', methods=['POST'])
def add_comment_route(topic_id, issue_id):
    if not session.get('nickname'):
        return redirect('/auth')
    
    comment = request.form['comment'].strip()

    words = re.findall(r'\w+', comment)
    if len(words) < 15:
        return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}?error=short')

    non_emoji = [c for c in comment if not unicodedata.category(c).startswith('So') and c.strip()]
    if not non_emoji:
        return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}?error=emoji')

    nickname = session['nickname']
    result = add_comment(issue_id, topic_id, session['nickname'], comment)
    if result.get('error') == 'abusive_language':
        return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}?error=abusive')

    record_interaction(nickname, topic_id, 'comment', 4)

    owner_nickname = get_issue_owner(issue_id)
    if owner_nickname and owner_nickname != nickname:
        try:
            comment_id = result.get('comment_id')
            message = f"{nickname} ne aapke issue pe comment kiya hai"
            notify_with_checkpoint(
                nickname=owner_nickname,
                entity_type='comment',
                entity_id=comment_id,
                message=message,
                link=f"/discuss/topic/{topic_id}/issue/{issue_id}#comment-{comment_id}"
            )
        except Exception as e:
            print("comment notify failed:", e)
    
    return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}')

@issue_bp.route('/vote/<int:comment_id>', methods=['POST'])
def vote(comment_id):
    if not session.get('nickname'):
        return {'error': 'not_logged_in'}, 401
    
    vote_val = int(request.form['vote'])
    comment = get_comments_by_id(comment_id)
    if not comment:
        return {'error': 'not_found'}, 404
    
    nickname = session['nickname']
    new_user_vote, action = toggle_vote(comment_id, session['nickname'], vote_val)
    likes, dislikes = get_votes(comment_id)

    issue_id = comment['issue_id']
    sorted_comments = get_comments(issue_id)
    order = [c[0] for c in sorted_comments]

    topic_id = get_issue_topic_id(issue_id)

    if vote_val == 1 and action in ('added', 'changed'):
        owner_nickname = get_comment_owner(comment_id)
        if owner_nickname and owner_nickname != nickname:
            try:
                message = f"Aapke comment ko {likes} likes millein hain"
                notify_with_checkpoint(
                    nickname=owner_nickname,
                    entity_type='comment_like',
                    entity_id=comment_id,
                    message=message,
                    link=f"/discuss/topic/{topic_id}/issue/{issue_id}#comment-{comment_id}"
                )
            except Exception as e:
                print("like notify failed:", e)

    if vote_val == 1 and action in ('added', 'changed'):
        record_interaction(nickname, topic_id, 'vote', 1)
    
    return {
        'likes': likes,
        'dislikes': dislikes,
        'user_vote': new_user_vote,
        'order': order
    }

@issue_bp.route('/comment/conclusion/<int:comment_id>', methods=['POST'])
def conclusion_vote(comment_id):
    if not session.get('nickname'):
        return {'error': 'not_logged_in'}, 401

    comment = get_comments_by_id(comment_id)
    if not comment:
        return {'error': 'not_found'}, 404

    nickname = session['nickname']
    supported = toggle_conclusion_vote(comment_id, session['nickname'])
    count = get_conclusion_count(comment_id)

    issue_id = comment['issue_id']
    sorted_comments = get_comments(issue_id)
    order = [c[0] for c in sorted_comments]

    topic_id = get_issue_topic_id(issue_id)

    if supported:
        owner_nickname = get_comment_owner(comment_id)
        if owner_nickname and owner_nickname != nickname:
            try:
                message = f"Aapke comment ko {count} conclusion votes mille hain"
                notify_with_checkpoint(
                    nickname=owner_nickname,
                    entity_type='comment_conclusion',
                    entity_id=comment_id,
                    message=message,
                    link=f"/discuss/topic/{topic_id}/issue/{issue_id}#comment-{comment_id}"
                )
            except Exception as e:
                print("conclusion notify failed:", e)

    if supported:
        record_interaction(nickname, topic_id, 'conclusion_support', 3)

    return {
        'supported': supported,
        'count': count,
        'order': order
    }

@issue_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment_route(topic_id, issue_id, comment_id):
    if not session.get('nickname'):
        return redirect('/auth')

    delete_comment(comment_id, session['nickname'])
    return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}')

@issue_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>/comment/<int:comment_id>/edit', methods=['POST'])
def edit_comment_route(topic_id, issue_id, comment_id):
    if not session.get('nickname'):
        return redirect('/auth')
    new_comment = request.form.get('comment', '').strip()
    if new_comment:
        result = update_comment(comment_id, session['nickname'], new_comment)
        if result and result.get('error') == 'abusive_language':
            return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}?error=abusive')
        
    return redirect(f'/discuss/topic/{topic_id}/issue/{issue_id}')

@issue_bp.route('/comment/<int:comment_id>/toggle-replies', methods=['POST'])
def toggle_replies_route(comment_id):
    if not session.get('nickname'):
        return {'error': 'not_logged_in'}, 401

    new_state = toggle_replies(comment_id, session['nickname'])
    if new_state is None:
        return {'error': 'not_owner_or_not_found'}, 403

    return {'success': True, 'replies_enabled': new_state}


