from datetime import timedelta
from flask import Blueprint, jsonify
from core.models import Medicine, Dispensing, manila_today
from core.helpers import login_required

dashboard = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard.route('/stats')
@login_required
def api_dashboard_stats():
    today                 = manila_today()
    near_expiry_threshold = today + timedelta(days=180)
    total         = Medicine.query.filter(Medicine.status.in_(['Active', 'Near Expiry', 'Expired'])).count()
    expired       = Medicine.query.filter_by(status='Expired').count()
    about_to_expire = Medicine.query.filter(
        Medicine.status.in_(['Active', 'Near Expiry']),
        Medicine.expiration_date.isnot(None),
        Medicine.expiration_date <= near_expiry_threshold,
        Medicine.expiration_date > today
    ).count()
    dispensed = Dispensing.query.count()
    discarded = Medicine.query.filter_by(status='Discarded').count()
    return jsonify({
        'total_items':      total,
        'about_to_expire':  about_to_expire,
        'expired':          expired,
        'dispensed':        dispensed,
        'discarded':        discarded,
    })


@dashboard.route('/block/<block_type>')
@login_required
def api_dashboard_block(block_type):
    today                 = manila_today()
    near_expiry_threshold = today + timedelta(days=180)
    items = []
    if block_type == 'total':
        items = [m.to_dict() for m in Medicine.query.filter(Medicine.status.in_(['Active', 'Near Expiry', 'Expired'])).all()]
    elif block_type == 'about_to_expire':
        items = [m.to_dict() for m in Medicine.query.filter(
            Medicine.status.in_(['Active', 'Near Expiry']),
            Medicine.expiration_date.isnot(None),
            Medicine.expiration_date <= near_expiry_threshold,
            Medicine.expiration_date > today,
        ).all()]
    elif block_type == 'expired':
        items = [m.to_dict() for m in Medicine.query.filter_by(status='Expired').all()]
    elif block_type == 'dispensed':
        items = [d.to_dict() for d in Dispensing.query.order_by(Dispensing.date_time.desc()).all()]
    elif block_type == 'discarded':
        items = [m.to_dict() for m in Medicine.query.filter_by(status='Discarded').all()]
    return jsonify(items)


@dashboard.route('/recent')
@login_required
def api_dashboard_recent():
    medicines = Medicine.query.order_by(Medicine.date_added.desc()).limit(20).all()
    return jsonify([m.to_dict() for m in medicines])
