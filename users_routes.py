from flask import Blueprint, render_template, request, redirect
from user_model import search_user

users_bp = Blueprint('users', __name__)

@users_bp.route('/search')
def search():
    nickname = request.args.get('q', '').strip()
    if not nickname:
        return redirect('/users')

    user = search_user(nickname)
    if user:
        return redirect(f'/profile/{user[0]}')
    else:
        return render_template('users.html', search_error="nickname galat hai!!")

@users_bp.route('/users')
def users():
    return render_template('users.html')