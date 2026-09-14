from flask import Blueprint, render_template, session, redirect
from message_model import get_all_notifications, mark_all_read, get_unread_count, delete_all_notifications, delete_notification

message_bp = Blueprint('message', __name__)

@message_bp.route('/messages')
def messages():
    if not session.get('nickname'):
        return redirect('/auth')

    nickname = session['nickname']
    notifications = get_all_notifications(nickname)
    mark_all_read(nickname)

    return render_template('message.html', notifications=notifications)

@message_bp.route('/messages/delete/<int:notif_id>', methods=['POST'])
def delete_notification_route(notif_id):
    if not session.get('nickname'):
        return redirect('/auth')
    delete_notification(notif_id, session['nickname'])
    return redirect('/messages')

@message_bp.route('/messages/delete-all', methods=['POST'])
def delete_all_notifications_route():
    if not session.get('nickname'):
        return redirect('/auth')
    delete_all_notifications(session['nickname'])
    return redirect('/messages')
