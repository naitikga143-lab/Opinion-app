from flask import Blueprint, render_template, request, redirect, session, jsonify
from comment_model import get_comments_by_id
from reply_model import (
    get_replies,
    add_reply,
    delete_reply,
    update_reply,
    vote_reply,
    get_user_votes_for_comment,
    sort_replies,
    get_reply_count,
    get_reply_owner,
    get_reply_meta
)
from message_model import add_notification, notify_with_checkpoint

import unicodedata

reply_bp = Blueprint('reply_bp', __name__)

@reply_bp.route('/reply/<int:comment_id>', methods=['GET', 'POST'])
def reply_page(comment_id):
    if not session.get('nickname'):
        return redirect('/auth')

    comment = get_comments_by_id(comment_id)

    if not comment:
        return "Comment nahi milla (delete ho chuka hoga)", 404

    issue_id = comment['issue_id']
    topic_id = comment['topic_id']
    replies = get_replies(comment_id)

    nickname = session.get('nickname')
    user_votes = get_user_votes_for_comment(comment_id, nickname) if nickname else {}

    reply_map = {}
    top_level = []

    for r in replies:
        reply_map[r[0]] = {
            'id': r[0],
            'comment_id': r[1],
            'nickname': r[3],
            'reply_text': r[6],
            'created_at': r[4],
            'parent_reply_id': r[2],
            'edited': r[5],
            'likes':r[7],
            'dislikes': r[8],
            'user_vote': user_votes.get(r[0]),
            'children': []
        }

    for r in reply_map.values():
        if r['parent_reply_id'] is None:
            top_level.append(r)
        else:
            parent = reply_map.get(r['parent_reply_id'])
            if parent:
                parent['children'].append(r)

    sort_replies(top_level)

    if request.method == 'POST':
        reply_text = request.form.get('reply_text', '').strip()
        parent_reply_id = request.form.get('parent_reply_id')
        parent_reply_id = int(parent_reply_id) if parent_reply_id else None

        if reply_text:
            non_emoji = [c for c in reply_text if not unicodedata.category(c).startswith('So') and c.strip()]
            if not non_emoji:
                return redirect(f'/reply/{comment_id}?error=emoji')
            
            result = add_reply(comment_id, session['nickname'], reply_text, parent_reply_id)
            if result.get('error') == 'abusive_language':
                return redirect(f'/reply/{comment_id}?error=abusive')

            replier_nickname = session['nickname']
            new_reply_id = result.get('id')

            if parent_reply_id:
                direct_target = get_reply_owner(parent_reply_id)
                direct_message = f"Aapke reply pe {replier_nickname} ne reply diya hai :-\n{reply_text}"
            else:
                direct_target = comment['nickname']
                direct_message = f"Aapke comment pe {replier_nickname} ne reply diya hai :-\n{reply_text}"

            if direct_target and direct_target != replier_nickname:
                try:
                    reply_link = f"/reply/{comment_id}#reply-{new_reply_id}"
                    add_notification(nickname=direct_target, message=direct_message, link=reply_link)
                except Exception as e:
                    print("direct reply notify failed:", e)

            comment_owner = comment['nickname']
            if comment_owner and comment_owner != replier_nickname:
                try:
                    comment_link = f"/discuss/topic/{topic_id}/issue/{issue_id}#comment-{comment_id}"
                    reply_count = get_reply_count(comment_id)
                    notify_with_checkpoint(
                        nickname=comment_owner,
                        entity_type='comment_reply_count',
                        entity_id=comment_id,
                        message=f"Aapke comment pe {reply_count} replies aae hain",
                        link=comment_link
                    )
                except Exception as e:
                    print("reply count notify failed:", e)

        return redirect(f'/reply/{comment_id}')

    error = request.args.get('error')
    return render_template('reply.html', comment=comment, top_level=top_level, error=error, topic_id=topic_id, issue_id=issue_id)

@reply_bp.route('/reply/<int:comment_id>/delete/<int:reply_id>', methods=['POST'])
def delete_reply_route(comment_id, reply_id):
    if not session.get('nickname'):
        return redirect('/auth')

    delete_reply(reply_id, session['nickname'])
    return redirect(f'/reply/{comment_id}')



@reply_bp.route('/reply/<int:comment_id>/edit/<int:reply_id>', methods=['POST'])
def edit_reply_route(comment_id, reply_id):
    if not session.get('nickname'):
        return redirect('/auth')
    
    new_text = request.form.get('reply_text', '').strip()
    if new_text:
        result = update_reply(reply_id, session['nickname'], new_text)
        if result and result.get('error') == 'abusive_language':
            return redirect(f'/reply/{comment_id}?error=abusive')
        
    return redirect(f'/reply/{comment_id}')

@reply_bp.route('/reply/<int:reply_id>/vote', methods=['POST'])
def vote_reply_route(reply_id):
    if not session.get('nickname'):
        return jsonify({'error': 'login_required'}), 401

    vote = request.form.get('vote')
    if vote not in ('like', 'dislike'):
        return jsonify({'error': 'invalid_vote'}), 400

    nickname = session['nickname']
    result = vote_reply(reply_id, session['nickname'], vote)

    if vote == 'like' and result.get('user_vote') == 'like':
        try:
            meta = get_reply_meta(reply_id)
            if meta and meta['nickname'] and meta['nickname'] != nickname:
                link = f"/reply/{meta['comment_id']}#reply-{reply_id}"
                likes = result.get('likes', 0)
                notify_with_checkpoint(
                    nickname=meta['nickname'],
                    entity_type='reply_like',
                    entity_id=reply_id,
                    message=f"Aapke reply ko {likes} like mille hain",
                    link=link
                )
        except Exception as e:
            print("reply like notify failed:", e)

    return jsonify(result)