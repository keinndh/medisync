from flask import Blueprint, request, jsonify, session
from core.models import db, User
from core.helpers import login_required, log_activity, issue_token, revoke_token
from core.extensions import limiter

auth = Blueprint('auth', __name__, url_prefix='/api')


@auth.route('/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    data     = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    user     = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session.permanent = True
        session['user_id'] = user.id
        token = issue_token(user.id)
        log_activity('Login', f'User {user.username} logged in.')
        return jsonify({'success': True, 'user': user.to_dict(), 'token': token})
    return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401


@auth.route('/logout', methods=['POST'])
@login_required
def api_logout():
    log_activity('Logout', 'User logged out.')
    session.clear()
    revoke_token(request.headers.get('X-Auth-Token'))
    return jsonify({'success': True})


@auth.route('/me')
@login_required
def api_me():
    user = User.query.get(getattr(request, 'current_user_id', session.get('user_id')))
    return jsonify(user.to_dict())
