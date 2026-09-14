from flask import Blueprint, render_template, request, redirect, session, jsonify
from user_model import search_user
from profile_model import get_users_topics, delete_topic, follow_user, unfollow_user, is_following, get_following_list, get_followers_count, get_following_count, get_followers_list
from court_model import get_notifications, mark_notifications_read, get_all_notifications
from issue_model import get_users_issues

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile/<nickname>')
def profile(nickname):
    if 'nickname' not in session:
        return redirect('/auth')

    user = search_user(nickname)
    if not user:
        return render_template('index.html',
                            search_error="aisa koi user yanha nahi hai")

    topics = get_users_topics(nickname)
    issues = get_users_issues(nickname)
    is_owner= session.get('nickname') == nickname
    notifications = get_notifications(nickname) if is_owner else []
    all_messages = get_all_notifications(nickname) if is_owner else []
    if is_owner and notifications:
        mark_notifications_read(nickname)

    following = is_following(session.get('nickname'), nickname) if session.get('nickname') else False
    followers_count = get_followers_count(nickname)
    following_count = get_following_count(nickname)

    return render_template('profile.html', 
                           nickname=user[0], topics=topics, issues=issues, is_owner=is_owner,
                           notifications=notifications, all_messages=all_messages,
                           following=following, followers_count=followers_count, following_count=following_count)

@profile_bp.route('/discuss/delete/<int:topic_id>', methods=['POST'])
def discuss_delete(topic_id):
    if not session.get('nickname'):
        return redirect('/auth')
    success = delete_topic(topic_id, session['nickname'])
    if not success:
        return redirect('/profile/' + session['nickname'] + '?delete_failed=1')
    return redirect('/profile/' + session['nickname'])

@profile_bp.route('/follow/<nickname>', methods=['POST'])
def follow(nickname):
    if not session.get('nickname'):
        return redirect('/auth')
    follow_user(session['nickname'], nickname)
    return redirect('/profile/' + nickname)

@profile_bp.route('/unfollow/<nickname>', methods=['POST'])
def unfollow(nickname):
    if not session.get('nickname'):
        return redirect('/auth')
    unfollow_user(session['nickname'], nickname)
    return redirect('/profile/' + nickname)

@profile_bp.route('/profile/<nickname>/followers')
def profile_followers(nickname):
    return jsonify(get_followers_list(nickname))

@profile_bp.route('/profile/<nickname>/following')
def profile_following(nickname):
    return jsonify(get_following_list(nickname))
