from flask import Blueprint, render_template, request, redirect, session
from issue_model import(
    get_issues_sorted_by_votes, get_votes_for_issue,
    get_user_vote_for_issues, add_issue, delete_issue_db,
    update_issue, add_vote, get_top_conclusions_comments,
    get_issue_owner
)
from message_model import notify_with_checkpoint
from topic_model import get_topic_by_id, record_interaction

topic_bp = Blueprint('topic', __name__)

@topic_bp.route('/discuss/topic/<int:topic_id>')
def topic_detail(topic_id):
    if not session.get('nickname'):
        return render_template('index.html', show_toast=True)
    
    topic = get_topic_by_id(topic_id)
    if not topic:
        return redirect('/discuss')
    
    record_interaction(session['nickname'], topic_id, 'click', 1)
    
    issues = get_issues_sorted_by_votes(topic_id)
    votes_data = {}
    user_votes = {}
    for issue in issues:
        votes_data[issue[0]] = get_votes_for_issue(issue[0])
        user_votes[issue[0]] = get_user_vote_for_issues(issue[0], session['nickname'])

    return render_template('topic.html', topic=topic, issues=issues,
                           votes_data=votes_data, user_votes=user_votes)

@topic_bp.route('/discuss/topic/<int:topic_id>/issue', methods=['POST'])
def add_issue_route(topic_id):
    if not session.get('nickname'):
        return redirect('/auth')
    
    description = request.form['description'].strip()

    import unicodedata
    non_emoji = [c for c in description if not unicodedata.category(c).startswith('So') and c.strip()]
    if not non_emoji:
        return redirect('/discuss/topic/' + str(topic_id) + '?error=emoji')

    result = add_issue(topic_id, session['nickname'], description)
    if result.get('error') == 'abusive_language':
        return redirect('/discuss/topic/' + str(topic_id) + '?error=abusive')
    record_interaction(session['nickname'], topic_id, 'issue_create', 3)

    return redirect('/discuss/topic/' + str(topic_id))

@topic_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>/delete', methods=['POST'])
def delete_issue_route(topic_id, issue_id):
    if not session.get('nickname'):
        return redirect('/auth')
    delete_issue_db(issue_id, session['nickname'])
    return redirect('/discuss/topic/' + str(topic_id))

@topic_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>/vote', methods=['POST'])
def vote_issue(topic_id, issue_id):
    if not session.get('nickname'):
        return redirect('/auth')
    
    vote_val = int(request.form['vote'])
    nickname = session['nickname']
    action = add_vote(issue_id, session['nickname'], vote_val)

    if vote_val == 1 and action in ('added', 'changed'):
        record_interaction(nickname, topic_id, 'issue_vote', 2)

    if action in ('added', 'changed'):
        owner_nickname = get_issue_owner(issue_id)
        if owner_nickname and owner_nickname != nickname:
            try:
                votes = get_votes_for_issue(issue_id)
                message = f"Aapke issue ko {votes['total']} upvotes mile hain"
                notify_with_checkpoint(
                    nickname=owner_nickname,
                    entity_type='issue_vote',
                    entity_id=issue_id,
                    message=message,
                    link=f"/discuss/topic/{topic_id}#issue-{issue_id}"
                )
            except Exception as e:
                print("issue vote notify failed:", e)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        votes = get_votes_for_issue(issue_id)
        user_vote = get_user_vote_for_issues(issue_id, session['nickname'])
        issues = get_issues_sorted_by_votes(topic_id)
        order = [i[0] for i in issues]
        return {'total': votes['total'], 'voted': bool(user_vote), 'order': order}

    return redirect('/discuss/topic/' + str(topic_id))

@topic_bp.route('/discuss/topic/<int:topic_id>/issue/<int:issue_id>/edit', methods=['POST'])
def edit_issue_route(topic_id, issue_id):
    if not session.get('nickname'):
        return redirect('/auth')
    
    new_description = request.form.get('description', '').strip()

    import unicodedata
    non_emoji = [c for c in new_description if not unicodedata.category(c).startswith('So') and c.strip()]
    if not non_emoji:
        return redirect(f'/discuss/topic/{topic_id}?error=emoji')

    if new_description:
        result = update_issue(issue_id, session['nickname'], new_description)
        if result and result.get('error') == 'abusive_language':
            return redirect(f'/discuss/topic/{topic_id}?error=abusive')

    return redirect(f'/discuss/topic/{topic_id}')

@topic_bp.route('/issue/conclusion/<int:issue_id>')
def issue_conclusion_panel(issue_id):
    if not session.get('nickname'):
        return {'error': 'not_logged_in'}, 401
    top_comments = get_top_conclusions_comments(issue_id, 10)
    return {'comments': top_comments}
