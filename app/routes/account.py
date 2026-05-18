from flask import Blueprint, request, jsonify, session
from core.models import db, User, AuthToken, ActivityLog, Notification
from core.helpers import login_required, log_activity

account = Blueprint('account', __name__, url_prefix='/api')


@account.route('/notifications')
@login_required
def api_notifications():
    notifs = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([n.to_dict() for n in notifs])


@account.route('/notifications/<int:n_id>/read', methods=['PUT'])
@login_required
def api_mark_notification_read(n_id):
    n       = Notification.query.get_or_404(n_id)
    n.is_read = True
    db.session.commit()
    return jsonify(n.to_dict())


@account.route('/notifications/read-all', methods=['PUT'])
@login_required
def api_mark_all_read():
    Notification.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@account.route('/settings/profile', methods=['PUT'])
@login_required
def api_update_profile():
    uid  = getattr(request, 'current_user_id', session.get('user_id'))
    user = User.query.get(uid)
    data = request.get_json()
    if data.get('full_name'):
        user.full_name = data['full_name']
    if data.get('username'):
        existing = User.query.filter(User.username == data['username'], User.id != user.id).first()
        if existing:
            return jsonify({'error': 'Username already taken.'}), 400
        user.username = data['username']
    if data.get('password'):
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters.'}), 400
        user.set_password(data['password'])
    db.session.commit()
    log_activity('Edit', f'Updated profile for {user.username}')
    return jsonify(user.to_dict())


@account.route('/settings/picture', methods=['POST'])
@login_required
def api_upload_picture():
    if 'picture' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400
    file = request.files['picture']
    if file.filename == '':
        return jsonify({'error': 'Empty filename.'}), 400

    uid  = getattr(request, 'current_user_id', session.get('user_id'))
    user = User.query.get(uid)

    import base64
    file_bytes = file.read()
    if len(file_bytes) > 2 * 1024 * 1024:
        return jsonify({'error': 'Image too large. Max 2MB.'}), 400
    mime    = file.content_type or 'image/jpeg'
    b64     = base64.b64encode(file_bytes).decode('utf-8')
    user.profile_picture = f'data:{mime};base64,{b64}'
    db.session.commit()
    log_activity('Edit', 'Updated profile picture')
    return jsonify(user.to_dict())


@account.route('/accounts/sub', methods=['GET'])
@login_required
def api_list_sub_accounts():
    uid          = getattr(request, 'current_user_id', session.get('user_id'))
    current_user = User.query.get(uid)
    parent_id    = uid if (current_user.role == 'admin' or not current_user.parent_id) else current_user.parent_id
    subs         = User.query.filter_by(parent_id=parent_id).order_by(User.created_at.desc()).all()
    return jsonify([s.to_dict() for s in subs])


@account.route('/accounts/sub', methods=['POST'])
@login_required
def api_create_sub_account():
    uid          = getattr(request, 'current_user_id', session.get('user_id'))
    current_user = User.query.get(uid)
    if current_user.role == 'sub':
        return jsonify({'error': 'Sub-accounts cannot create other accounts.'}), 403
    if User.query.filter_by(parent_id=uid).count() >= 5:
        return jsonify({'error': 'Maximum of 5 sub-accounts reached.'}), 400

    data      = request.get_json()
    username  = data.get('username', '').strip()
    password  = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()

    if not username or not password or not full_name:
        return jsonify({'error': 'Username, password, and full name are required.'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken.'}), 400

    sub = User(username=username, full_name=full_name, role='sub', parent_id=uid)
    sub.set_password(password)
    db.session.add(sub)
    db.session.commit()
    log_activity('Add', f'Created sub-account: {full_name} ({username})')
    return jsonify(sub.to_dict()), 201


@account.route('/accounts/sub/<int:sub_id>', methods=['DELETE'])
@login_required
def api_delete_sub_account(sub_id):
    uid = getattr(request, 'current_user_id', session.get('user_id'))
    sub = User.query.get_or_404(sub_id)
    if sub.parent_id != uid:
        return jsonify({'error': 'Not authorized to delete this account.'}), 403
    username = sub.username
    AuthToken.query.filter_by(user_id=sub_id).delete()
    db.session.delete(sub)
    db.session.commit()
    log_activity('Delete', f'Deleted sub-account: {username}')
    return jsonify({'success': True})


@account.route('/accounts/sub/<int:sub_id>/activity')
@login_required
def api_sub_account_activity(sub_id):
    uid = getattr(request, 'current_user_id', session.get('user_id'))
    sub = User.query.get_or_404(sub_id)
    if sub.parent_id != uid:
        return jsonify({'error': 'Not authorized.'}), 403
    logs = ActivityLog.query.filter(
        ActivityLog.performed_by.ilike(f'%{sub.full_name}%')
    ).order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return jsonify([l.to_dict() for l in logs])


@account.route('/accounts/sub/<int:sub_id>/reset-password', methods=['PUT'])
@login_required
def api_reset_sub_password(sub_id):
    uid    = getattr(request, 'current_user_id', session.get('user_id'))
    sub    = User.query.get_or_404(sub_id)
    if sub.parent_id != uid:
        return jsonify({'error': 'Not authorized.'}), 403
    data   = request.get_json()
    new_pw = data.get('password', '').strip()
    if not new_pw or len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400
    sub.set_password(new_pw)
    db.session.commit()
    log_activity('Edit', f'Reset password for sub-account: {sub.username}')
    return jsonify({'success': True})
