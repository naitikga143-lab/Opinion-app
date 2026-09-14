from flask import Blueprint, render_template, request, jsonify, session
from court_model import is_already_reported, add_court_entry
from message_model import notify_with_checkpoint

report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/report/<target_type>/<int:target_id>')
def report_page(target_type, target_id):
    return render_template('report.html', target_type=target_type, target_id=target_id)

@report_bp.route('/report/submit', methods=['POST'])
def submit_report():
    print("REPORT HIT!")
    data = request.get_json()
    print("RECIEVED DATA:", data)
    item_type = data.get('item_type')
    item_id = data.get('item_id')
    category = data.get('category')
    content = data.get('content')
    posted_by = data.get('posted_by')

    valid_categories = ['abuse', 'personal_attack', 'engagement_bait', 'useless_talk', 'others']

    if not all([item_type, item_id, category, content]) or category not in valid_categories:
        return jsonify(success=False, message='Invalid data'), 400

    if is_already_reported(item_type, item_id):
        return jsonify(success=False, message='Ye card ek baar already report ho chuka hai'), 409

    reported_by = session.get('nickname', 'anonymous')
    entry_id = add_court_entry(item_type, item_id, category, content, posted_by, reported_by)

    import sqlite3
    conn = sqlite3.connect('opinion.db')
    c = conn.cursor()
    owner_nickname = None
    if item_type == 'topic':
        c.execute('SELECT nickname FROM topics WHERE id=?', (item_id,))
    elif item_type == 'issue':
        c.execute('SELECT nickname FROM issues WHERE id=?', (item_id,))
    elif item_type == 'comment':
        c.execute('SELECT nickname FROM comments WHERE id=?', (item_id,))
    row = c.fetchone()
    owner_nickname = row[0] if row else None
    conn.close()

    if owner_nickname:
        try:
            category_label = category.replace('_', ' ')
            message = f"Aapka {item_type} '{category_label}' mein report kiya gaya hai"
            notify_with_checkpoint(
                nickname=owner_nickname,
                entity_type='court_entry',
                entity_id=entry_id,
                message=message,
                link=f"/court?category={category}#entry-{entry_id}"
            )
        except Exception as e:
            print("report notify failed:", e)

    return jsonify(success=True)