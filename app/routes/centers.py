from flask import Blueprint, request, jsonify
from core.models import db, Center, Dispensing, RequestQueue, Recipient
from core.helpers import login_required, log_activity

centers = Blueprint('centers', __name__, url_prefix='/api/centers')


@centers.route('')
@login_required
def api_centers():
    return jsonify([c.to_dict() for c in Center.query.order_by(Center.name.asc()).all()])


@centers.route('', methods=['POST'])
@login_required
def api_add_center():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Center name is required.'}), 400
    if Center.query.filter_by(name=name).first():
        return jsonify({'error': 'Center already exists.'}), 400
    c = Center(name=name)
    db.session.add(c)
    db.session.commit()
    log_activity('Add', f'Added center: {name}')
    return jsonify(c.to_dict()), 201


@centers.route('/<int:center_id>', methods=['PUT'])
@login_required
def api_edit_center(center_id):
    c        = Center.query.get_or_404(center_id)
    data     = request.get_json()
    new_name = data.get('name', '').strip()
    if not new_name:
        return jsonify({'error': 'Center name is required.'}), 400
    if Center.query.filter(Center.name == new_name, Center.id != center_id).first():
        return jsonify({'error': 'Center name already exists.'}), 400
    old_name = c.name
    c.name   = new_name
    db.session.commit()
    log_activity('Edit', f'Renamed center "{old_name}" to "{new_name}"')
    return jsonify(c.to_dict())


@centers.route('/<int:center_id>', methods=['DELETE'])
@login_required
def api_delete_center(center_id):
    c           = Center.query.get_or_404(center_id)
    center_name = c.name
    for disp in c.dispensings:
        disp.center_id = None
    for q in c.queue_items:
        q.center_id = None
    db.session.delete(c)
    db.session.commit()
    log_activity('Delete', f'Deleted center: {center_name}')
    return jsonify({'success': True})


@centers.route('/<int:center_id>/transactions')
@login_required
def api_center_transactions(center_id):
    dispensings = Dispensing.query.filter_by(center_id=center_id).order_by(Dispensing.date_time.desc()).all()
    queued      = RequestQueue.query.filter_by(center_id=center_id).order_by(RequestQueue.created_at.desc()).all()
    return jsonify({'dispensings': [d.to_dict() for d in dispensings], 'queued': [q.to_dict() for q in queued]})


@centers.route('/<int:center_id>/recipients')
@login_required
def api_center_recipients(center_id):
    recipients = Recipient.query.filter_by(center_id=center_id).order_by(Recipient.name.asc()).all()
    return jsonify([r.to_dict() for r in recipients])
