from flask import Blueprint, render_template, request, redirect, session
from topic_model import get_all_topics, add_topic, toggle_topic_heat, record_interaction
import unicodedata
from flask import jsonify

discuss_bp = Blueprint('discuss', __name__)

@discuss_bp.route('/discuss')
def discuss():
    topics = get_all_topics()
    return render_template('discuss.html', topics=topics)

@discuss_bp.route('/discuss/add', methods=['POST'])
def discuss_add():
    if not session.get('nickname'):
        return redirect('/auth')
    
    title = request.form['title'].strip()
    description = request.form['description'].strip()

    non_emoji = [c for c in description if not unicodedata.category(c).startswith('So') and c.strip()]
    if not non_emoji:
        return redirect('/discuss?error=emoji')

    result = add_topic(session['nickname'], title, description)
    if result.get('error') == 'abusive_language':
        return redirect('/discuss?error=abusive')
    
    return redirect('/discuss')

@discuss_bp.route('/discuss/topic/<int:topic_id>/heat', methods=['POST'])
def discuss_heat(topic_id):
    if not session.get('nickname'):
        return jsonify({'error': 'login_required'}), 401
    result = toggle_topic_heat(session['nickname'], topic_id)
    record_interaction(session['nickname'], topic_id, 'heat', 2)
    return jsonify(result)
    
