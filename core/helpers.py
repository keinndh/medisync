import random
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import request, session, jsonify, redirect, url_for

from core.models import db, User, AuthToken, ActivityLog, Notification, Medicine
from core.models import manila_now, manila_today

TOKEN_TTL_DAYS = 7


def generate_serial_number():
    from core.models import Dispensing
    while True:
        sn = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        if not Dispensing.query.filter_by(serial_number=sn).first():
            return sn


def issue_token(user_id):
    token = secrets.token_hex(32)
    auth_token = AuthToken(
        token=token,
        user_id=user_id,
        expires_at=manila_now() + timedelta(days=TOKEN_TTL_DAYS),
    )
    db.session.add(auth_token)
    db.session.commit()
    return token


def revoke_token(token_str):
    if token_str:
        AuthToken.query.filter_by(token=token_str).delete()
        db.session.commit()


def purge_expired_tokens():
    AuthToken.query.filter(AuthToken.expires_at < manila_now()).delete()
    db.session.commit()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Auth-Token') or request.args.get('auth_token')
        if token:
            auth = AuthToken.query.filter_by(token=token).first()
            if auth and auth.expires_at > manila_now():
                request.current_user_id = auth.user_id
                return f(*args, **kwargs)

        if 'user_id' in session:
            request.current_user_id = session['user_id']
            return f(*args, **kwargs)

        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('pages.login_page'))
    return decorated


def log_activity(action, details=''):
    uid = getattr(request, 'current_user_id', None) or session.get('user_id')
    user = User.query.get(uid)
    performed_by = user.full_name if user else 'System'
    if user and user.role == 'sub' and user.parent:
        performed_by = f'{user.full_name} (sub of {user.parent.full_name})'
    entry = ActivityLog(action=action, performed_by=performed_by, details=details)
    db.session.add(entry)
    db.session.commit()


def add_notification(message, notif_type='info', reference_id=None, reference_type=''):
    n = Notification(
        message=message, type=notif_type,
        reference_id=reference_id, reference_type=reference_type,
    )
    db.session.add(n)
    db.session.commit()


def check_expirations():
    today = manila_today()
    near_expiry_threshold = today + timedelta(days=180)
    medicines = Medicine.query.filter(
        Medicine.status.in_(['Active', 'Near Expiry']),
        Medicine.expiration_date.isnot(None)
    ).all()
    for med in medicines:
        if med.expiration_date <= today and med.status in ['Active', 'Near Expiry']:
            med.status = 'Expired'
            add_notification(
                f'{med.article_name} (Stock #{med.stock_number}) has expired.',
                'alert', med.id, 'medicine'
            )
        elif med.expiration_date <= near_expiry_threshold and med.status == 'Active':
            med.status = 'Near Expiry'
            existing = Notification.query.filter_by(
                reference_id=med.id, reference_type='medicine_expiring'
            ).first()
            if not existing:
                days = (med.expiration_date - today).days
                add_notification(
                    f'{med.article_name} (Stock #{med.stock_number}) expires in {days} days.',
                    'warning', med.id, 'medicine_expiring'
                )
    db.session.commit()
