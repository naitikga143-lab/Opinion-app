from flask import Blueprint, render_template, request, session
from trending_model import get_most_clicked_topics, get_most_heated_topics, VALID_PERIODS

trending_bp = Blueprint('trending', __name__)

@trending_bp.route('/trending')
def trending():
    if not session.get('nickname'):
        return render_template('index.html', show_toast=True)

    period = request.args.get('period', 'all')
    if period not in VALID_PERIODS:
        period = 'all'

    active_tab = request.args.get('tab', 'heated')
    if active_tab not in ('heated', 'clicked'):
        active_tab = 'heated'

    heated_topics = get_most_heated_topics(period=period)
    clicked_topics = get_most_clicked_topics(period=period)

    return render_template(
        'trending.html',
        heated_topics=heated_topics,
        clicked_topics=clicked_topics,
        period=period,
        active_tab=active_tab
    )