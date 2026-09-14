from flask import Blueprint, render_template, request, redirect, session
from admin_model import get_all_users, ban_user, delete_court_entry, retain_court_entry
from court_model import get_court_entries_with_vote, get_court_reasons, get_setting, set_setting
import bcrypt
import os

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']

        stored_hash = os.getenv('ADMIN_PASSWORD_HASH').encode()
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            session['admin'] = True
            return redirect('/admin/users')

        return render_template('admin_login.html',
                               error="kyu nahi ho rahi padhai ?")

    return render_template('admin_login.html')

@admin_bp.route('/admin/users')
def admin_users():
    if not session.get('admin'):
        return redirect('/admin')
    users = get_all_users()
    return render_template('admin_users.html', users=users)

@admin_bp.route('/admin/ban/<user_id>', methods=['GET', 'POST'])
def admin_ban(user_id):
    if not session.get('admin'):
        return redirect('/admin')
    ban_user(user_id, 1)
    return redirect('/admin/users')

@admin_bp.route('/admin/unban/<user_id>', methods=['GET', 'POST'])
def admin_unban(user_id):
    if not session.get('admin'):
        return redirect('/admin')
    ban_user(user_id, 0)
    return redirect('/admin/users')

@admin_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/')

@admin_bp.route('/admin/court')
def admin_court():
    if not session.get('admin'):
        return redirect('/admin')
    return render_template('admin_court.html')

@admin_bp.route('/admin/court/data/<category>')
def admin_court_data(category):
    if not session.get('admin'):
        return redirect('/admin')
    from court_model import auto_retain_expired_entries
    auto_retain_expired_entries()
    entries = get_court_entries_with_vote(category)
    result = [
        {
            'id': e[0], 'item_type': e[1], 'item_id': e[2],
            'content': e[3], 'posted_by': e[4], 'reported_by': e[5],
            'created_at': e[6], 'category': e[7], 'delete_votes': e[8]
        }
        for e in entries
    ]
    from flask import jsonify
    return jsonify(result)

@admin_bp.route('/admin/court/delete/<int:entry_id>/<item_type>/<int:item_id>', methods=['POST'])
def admin_court_delete(entry_id, item_type, item_id):
    if not session.get('admin'):
        return redirect('/admin')
    from flask import jsonify
    from court_model import add_notification, build_message, build_reasons_text_from_row
    posted_by, reason_row = delete_court_entry(entry_id, item_type, item_id)
    if posted_by:
        reasons_text = build_reasons_text_from_row(reason_row)
        add_notification(posted_by, build_message('admin_delete', item_type, reasons_text))
    return jsonify(success=True)

@admin_bp.route('/admin/court/retain/<int:entry_id>/<item_type>/<int:item_id>', methods=['POST'])
def admin_court_retain(entry_id, item_type, item_id):
    if not session.get('admin'):
        return redirect('/admin')
    from flask import jsonify
    retain_court_entry(entry_id, item_type, item_id)
    return jsonify(success=True)

@admin_bp.route('/admin/court/settings')
def admin_court_settings():
    if not session.get('admin'):
        return redirect('/admin')
    from flask import jsonify
    return jsonify({
        'vote_threshold': get_setting('delete_vote_threshold', 50),
        'reason_with_vote_threshold': get_setting('delete_reason_with_vote_threshold', 1),
        'reason_only_threshold': get_setting('delete_reason_only_threshold', 3)
    })

@admin_bp.route('/admin/court/settings/update', methods=['POST'])
def admin_court_settings_update():
    if not session.get('admin'):
        return redirect('/admin')
    from flask import jsonify, request
    data = request.get_json()

    try:
        vote_threshold = int(data.get('vote_threshold'))
        reason_with_vote_threshold = int(data.get('reason_with_vote_threshold'))
        reason_only_threshold = int(data.get('reason_only_threshold'))
    except (TypeError, ValueError):
        return jsonify(success=False, message='Sahi number dalo chaman singh'), 400

    set_setting('delete_vote_threshold', vote_threshold)
    set_setting('delete_reason_with_vote_threshold', reason_with_vote_threshold)
    set_setting('delete_reason_only_threshold', reason_only_threshold)
    return jsonify(success=True)
