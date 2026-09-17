from flask import Flask, render_template, request, redirect, session
from admin_routes import admin_bp
from users_routes import users_bp
from profile_routes import profile_bp
from profile_model import init_follows_table
from discuss_routes import discuss_bp
from user_model import init_db
from auth_routes import auth_bp
from topic_routes import topic_bp
from topic_model import init_topics_table, get_topic_retain_count, get_topic_conclusions, get_topic_heat_count, has_user_heated, time_ago, init_interactions_table
from issue_model import init_votes_tables, init_issues_table, get_issue_retain_count, time_ago_issues
from comment_model import init_comments_table, get_comment_retain_count, time_ago_comments
from issue_routes import issue_bp
from reply_routes import reply_bp
from report_routes import report_bp
from court_routes import court_bp
from trending_routes import trending_bp
from setup_db import init_issue_votes_table, run_migrations
from court_model import init_court_table, init_court_reasons_table, init_court_setting_table, init_notifications_table, init_court_delete_votes_table
from reply_model import (
    get_reply_count,
    init_replies_table,
    time_ago_replies,
    )
from flask_wtf.csrf import CSRFProtect
from limiter_instance import limiter
from dotenv import load_dotenv
from message_model import init_message_tables, get_unread_count
from message_routes import message_bp
from explore_routes import explore_bp
import os
from datetime import timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.jinja_env.globals['get_reply_count'] = get_reply_count
app.jinja_env.globals['get_topic_retain_count'] = get_topic_retain_count
app.jinja_env.globals['get_issue_retain_count'] = get_issue_retain_count
app.jinja_env.globals['get_comment_retain_count'] = get_comment_retain_count
app.jinja_env.globals['get_topic_conclusions'] = get_topic_conclusions
app.jinja_env.globals.update(
    get_topic_heat_count=get_topic_heat_count,
    has_user_heated=has_user_heated
)
app.jinja_env.globals.update(time_ago=time_ago)
app.jinja_env.globals.update(time_ago_issues=time_ago_issues)
app.jinja_env.globals.update(time_ago_comments=time_ago_comments)
app.jinja_env.globals.update(time_ago_replies=time_ago_replies)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='LAX',
    WTF_CSRF_TIME_LIMIT = 86400,
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)
)

crsf = CSRFProtect(app)

limiter.init_app(app)

init_db()
init_topics_table()
init_issues_table()
init_comments_table()
init_replies_table()
init_votes_tables()
init_court_table()
init_court_reasons_table()
init_court_setting_table()
init_notifications_table()
init_issue_votes_table()
init_court_delete_votes_table()
init_message_tables()
init_interactions_table()
init_follows_table()


app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(discuss_bp)
app.register_blueprint(topic_bp)
app.register_blueprint(issue_bp)
app.register_blueprint(reply_bp)
app.register_blueprint(report_bp)
app.register_blueprint(court_bp) 
app.register_blueprint(message_bp)
app.register_blueprint(explore_bp)
app.register_blueprint(trending_bp)


@app.before_request
def check_banned():
    if session.get('nickname'):
        from user_model import get_user_status
        if get_user_status(session['nickname']) == 1:
            session.clear()
            return render_template('auth.html',
                error="ACCOUNT BAN HO CHUKA HAI!")

@app.context_processor
def inject_unread_count():
    if session.get('nickname'):
        return {'unread_count': get_unread_count(session['nickname'])}
    return {'unread_count': 0}

@app.route('/')
def home():
    return render_template('index.html')
    
if __name__ == '__main__':
    app.run(debug=True)