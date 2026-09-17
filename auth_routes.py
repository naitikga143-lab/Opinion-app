from flask import Blueprint, render_template, request, redirect, session
from user_model import add_user, get_user
from limiter_instance import limiter

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth')
def auth():
    return render_template('auth.html')

@auth_bp.route('/signup', methods=['POST'])
@limiter.limit("30 per 15 minute")
def signup():
    nickname = request.form['nickname'].strip()
    email = request.form['email'].strip().lower()
    password = request.form['password']

    if len(nickname) < 3 or len(nickname) > 20:
        return render_template('auth.html',
            error="kripya 3 letters se bada aur 20 letters se bada nickname apply karein!")

    if not nickname.isalnum():
        return render_template('auth.html',
            error="Nickname mein sirf letters aur number allowed hain!")
    
    if len(password) < 8:
        return render_template('auth.html',
            error="aapke password mein kam se kam 8 akshar hone chahiye!")
    
    success = add_user(nickname, email, password)

    if success:
        session.permanent = True
        session['nickname'] = nickname
        return redirect('/')
    else:
        return render_template('auth.html',
            error="aapka apply kia hua nickname ya email pehle se exist karta hai!")
    
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("30 per 15 minute")
def login():
    email = request.form['email'].strip().lower()
    password = request.form['password']

    user = get_user(email, password)

    if user:
        session.permanent = True
        session['nickname'] = user[2]
        return redirect('/')
    else:
        return render_template('auth.html',
            error="Aapka apply kiya hua email exist nahi karta ya password galat hai")
    
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')
