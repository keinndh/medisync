import io
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file

from core.models import db, Medicine, Dispensing, RequestQueue, Recipient, Center, manila_today, manila_now
from core.helpers import login_required, log_activity, add_notification, generate_serial_number

dispensing = Blueprint('dispensing', __name__, url_prefix='/api')


@dispensing.route('/dispense', methods=['POST'])
@login_required
def api_dispense():
    data         = request.get_json()
    article_name = data.get('article_name')
    if not article_name:
        return jsonify({'error': 'Article name is required.'}), 400

    batches = Medicine.query.filter(
        Medicine.article_name == article_name,
        Medicine.status.in_(['Active', 'Near Expiry'])
    ).order_by(Medicine.expiration_date.asc().nulls_last(), Medicine.date_added.asc()).all()

    if not batches:
        return jsonify({'error': 'Medicine not found or out of stock.'}), 404

    total_stock      = sum(b.quantity for b in batches)
    selected_batches = data.get('selected_batches', [])
    is_manual        = len(selected_batches) > 0
    requested_qty    = sum(b.get('qty', 0) for b in selected_batches) if is_manual else int(data.get('quantity', 0))

    if requested_qty <= 0:
        return jsonify({'error': 'Invalid quantity.'}), 400

    confirm_action = data.get('confirm_action')
    if not confirm_action:
        if requested_qty > total_stock or requested_qty >= (total_stock // 2):
            half_qty  = max(0, total_stock // 2)
            queue_qty = requested_qty - half_qty
            return jsonify({
                'requires_confirmation': True,
                'message': f'Requested {requested_qty}, but stock is low ({total_stock} total). Dispense half ({half_qty}) and queue the remaining {queue_qty}?'
            }), 200

    dispense_limit = requested_qty
    queue_qty      = 0

    if confirm_action == 'queue_all':
        dispense_limit = 0
        queue_qty      = requested_qty
    elif confirm_action == 'dispense_all':
        dispense_limit = min(requested_qty, total_stock)
    elif confirm_action == 'queue_remaining':
        dispense_limit = min(requested_qty, total_stock // 2)
        queue_qty      = requested_qty - dispense_limit
    elif confirm_action == 'cancel_remaining':
        dispense_limit = min(requested_qty, total_stock // 2)

    remaining_to_deduct = dispense_limit
    last_disp_id        = None
    source_items        = selected_batches if is_manual else batches

    for item in source_items:
        if remaining_to_deduct <= 0:
            break
        b = Medicine.query.get(item['id']) if is_manual else item
        if not b or b.quantity <= 0:
            continue
        available_in_batch = item['qty'] if is_manual else b.quantity
        deduct             = min(remaining_to_deduct, available_in_batch)
        if deduct > 0:
            b.quantity          -= deduct
            remaining_to_deduct -= deduct
            disp = Dispensing(
                dispenser_name=data.get('dispenser_name', ''),
                medicine_id=b.id,
                recipient_name=data.get('recipient_name', ''),
                recipient_contact=data.get('recipient_contact', ''),
                center_id=data.get('center_id'),
                quantity_dispensed=deduct,
                remarks=f"{data.get('remarks', '')} ({confirm_action or 'Full'})".strip(),
                serial_number=generate_serial_number(),
            )
            db.session.add(disp)
            db.session.flush()
            last_disp_id = disp.id

    if queue_qty > 0:
        primary_med = batches[0]
        q = RequestQueue(
            dispenser_name=data.get('dispenser_name', ''),
            medicine_id=primary_med.id,
            recipient_name=data.get('recipient_name', ''),
            recipient_contact=data.get('recipient_contact', ''),
            center_id=data.get('center_id'),
            quantity_requested=queue_qty,
            status='Pending',
        )
        db.session.add(q)

    db.session.commit()
    log_activity('Dispense', f'Processed {article_name} (Dispensed: {dispense_limit}, Queued: {queue_qty})')

    final_total = sum(bb.quantity for bb in Medicine.query.filter(
        Medicine.article_name == article_name, Medicine.status.in_(['Active', 'Near Expiry'])
    ).all())
    if final_total < 100:
        add_notification(f'Low stock alert: {article_name} has only {final_total} units left.', 'warning')

    return jsonify({'success': True, 'queued': queue_qty > 0,
                    'message': f'Successfully processed request for {article_name}.'}), 201


@dispensing.route('/dispense/today')
@login_required
def api_dispense_today():
    today_start = datetime.combine(manila_today(), datetime.min.time())
    items       = Dispensing.query.filter(Dispensing.date_time >= today_start).order_by(Dispensing.date_time.desc()).all()
    return jsonify([d.to_dict() for d in items])


@dispensing.route('/dispense/history')
@login_required
def api_dispense_history():
    query  = Dispensing.query
    search = request.args.get('search', '')
    if search:
        query = query.join(Medicine).outerjoin(Center).filter(db.or_(
            Dispensing.recipient_name.ilike(f'%{search}%'),
            Medicine.article_name.ilike(f'%{search}%'),
            Center.name.ilike(f'%{search}%'),
        ))
    date_filter = request.args.get('date', '')
    if date_filter:
        try:
            d     = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Dispensing.date_time) == d)
        except ValueError:
            pass
    return jsonify([d.to_dict() for d in query.order_by(Dispensing.date_time.desc()).all()])


@dispensing.route('/dispense/<int:disp_id>/receipt')
@login_required
def api_dispense_receipt(disp_id):
    from reportlab.lib.pagesizes import A6
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    disp       = Dispensing.query.get_or_404(disp_id)
    buffer     = io.BytesIO()
    doc        = SimpleDocTemplate(buffer, pagesize=A6,
                                   topMargin=10*mm, bottomMargin=10*mm,
                                   leftMargin=8*mm, rightMargin=8*mm)
    styles     = getSampleStyleSheet()
    center_s   = ParagraphStyle('center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)
    title_s    = ParagraphStyle('title_c', parent=styles['Title'],  alignment=TA_CENTER, fontSize=12)
    small      = ParagraphStyle('small',  parent=styles['Normal'], fontSize=7)
    elements   = []

    elements.append(Paragraph('MediSync', title_s))
    elements.append(Paragraph('Medicine Dispensing Receipt', center_s))
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 2*mm))

    info = [
        ['Receipt #:',  str(disp.id)],
        ['Serial #:',   disp.serial_number or 'N/A'],
        ['Date/Time:',  disp.date_time.strftime('%Y-%m-%d %H:%M') if disp.date_time else ''],
        ['Dispenser:',  disp.dispenser_name],
        ['Medicine:',   disp.medicine.article_name if disp.medicine else ''],
        ['Stock #:',    disp.medicine.stock_number if disp.medicine else ''],
        ['Quantity:',   str(disp.quantity_dispensed)],
        ['Recipient:',  disp.recipient_name],
        ['Contact:',    disp.recipient_contact or ''],
        ['Center:',     disp.center.name if disp.center else 'N/A'],
    ]
    t = Table(info, colWidths=[25*mm, 45*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE',  (0, 0), (-1, -1), 7),
        ('FONTNAME',  (0, 0), (0, -1),  'Helvetica-Bold'),
        ('VALIGN',    (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(f'Remarks: {disp.remarks or "N/A"}', small))

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                     download_name=f'receipt_{disp.id}.pdf')


@dispensing.route('/queue')
@login_required
def api_queue():
    items = RequestQueue.query.filter_by(status='Pending').order_by(
        RequestQueue.priority.desc(), RequestQueue.created_at.asc()
    ).all()
    return jsonify([q.to_dict() for q in items])


@dispensing.route('/queue/<int:q_id>/prioritize', methods=['PUT'])
@login_required
def api_queue_prioritize(q_id):
    item  = RequestQueue.query.get_or_404(q_id)
    max_p = db.session.query(db.func.max(RequestQueue.priority)).scalar() or 0
    item.priority = max_p + 1
    db.session.commit()
    log_activity('Edit', f'Prioritized queue item #{q_id} for {item.recipient_name}')
    return jsonify(item.to_dict())


@dispensing.route('/queue/<int:q_id>/unprioritize', methods=['PUT'])
@login_required
def api_queue_unprioritize(q_id):
    item          = RequestQueue.query.get_or_404(q_id)
    item.priority = 0
    db.session.commit()
    log_activity('Edit', f'Removed priority for queue item #{q_id} for {item.recipient_name}')
    return jsonify(item.to_dict())


@dispensing.route('/queue/<int:q_id>', methods=['DELETE'])
@login_required
def api_queue_delete(q_id):
    item      = RequestQueue.query.get_or_404(q_id)
    recipient = item.recipient_name
    medicine  = item.medicine.article_name if item.medicine else 'Unknown'
    db.session.delete(item)
    db.session.commit()
    log_activity('Delete', f'Removed queue request #{q_id} for {recipient} ({medicine})')
    return jsonify({'success': True})


@dispensing.route('/queue/<int:q_id>/fulfill', methods=['PUT'])
@login_required
def api_queue_fulfill(q_id):
    item         = RequestQueue.query.get_or_404(q_id)
    original_med = Medicine.query.get(item.medicine_id)
    if not original_med:
        return jsonify({'error': 'Original medicine not found.'}), 404

    batches     = Medicine.query.filter(
        Medicine.article_name == original_med.article_name,
        Medicine.status.in_(['Active', 'Near Expiry'])
    ).order_by(Medicine.expiration_date.asc().nulls_last(), Medicine.date_added.asc()).all()
    total_stock = sum(b.quantity for b in batches)
    limit       = total_stock / 2

    if item.quantity_requested > limit:
        return jsonify({'error': f'Cannot fulfill: queued quantity ({item.quantity_requested}) must be half or less of total available stock ({total_stock}). Current limit: {int(limit)}. Please restock first.'}), 400

    if total_stock >= item.quantity_requested:
        remaining_qty = item.quantity_requested
        first_disp_id = None
        for b in batches:
            if remaining_qty <= 0:
                break
            if b.quantity <= 0:
                continue
            deduct        = min(remaining_qty, b.quantity)
            b.quantity   -= deduct
            remaining_qty -= deduct
            disp = Dispensing(
                dispenser_name=item.dispenser_name,
                medicine_id=b.id,
                recipient_name=item.recipient_name,
                recipient_contact=item.recipient_contact,
                center_id=item.center_id,
                quantity_dispensed=deduct,
                remarks='Fulfilled from queue',
            )
            db.session.add(disp)
            db.session.flush()
            if not first_disp_id:
                first_disp_id = disp.id

        item.status       = 'Fulfilled'
        item.fulfilled_at = manila_now()
        db.session.commit()
        log_activity('Dispense', f'Fulfilled queue request #{q_id}: {item.quantity_requested}x {original_med.article_name} to {item.recipient_name}')
        return jsonify({'success': True, 'message': 'Queue request fulfilled.', 'dispense_id': first_disp_id})

    return jsonify({'error': f'Still insufficient stock. Total available: {total_stock}'}), 400


@dispensing.route('/recipients')
@login_required
def api_recipients():
    query     = Recipient.query
    search    = request.args.get('q', '')
    center_id = request.args.get('center_id', '')
    if search:
        query = query.filter(Recipient.name.ilike(f'%{search}%'))
    if center_id:
        query = query.filter_by(center_id=int(center_id))
    return jsonify([r.to_dict() for r in query.order_by(Recipient.name.asc()).all()])


@dispensing.route('/recipients', methods=['POST'])
@login_required
def api_add_recipient():
    data      = request.get_json()
    name      = data.get('name', '').strip()
    contact   = data.get('contact', '').strip()
    center_id = data.get('center_id')
    if not name or not center_id:
        return jsonify({'error': 'Name and center are required.'}), 400
    existing = Recipient.query.filter_by(name=name, center_id=center_id).first()
    if existing:
        return jsonify({'error': f'Recipient "{name}" already exists in this center.'}), 400
    r = Recipient(name=name, contact=contact, center_id=center_id)
    db.session.add(r)
    db.session.commit()
    log_activity('Add', f'Saved recipient profile: {name}')
    return jsonify(r.to_dict()), 201


@dispensing.route('/recipients/<int:r_id>', methods=['DELETE'])
@login_required
def api_delete_recipient(r_id):
    r    = Recipient.query.get_or_404(r_id)
    name = r.name
    db.session.delete(r)
    db.session.commit()
    log_activity('Delete', f'Deleted recipient profile: {name}')
    return jsonify({'success': True})


@dispensing.route('/recipients/search')
@login_required
def api_recipients_search():
    q = request.args.get('q', '')
    if not q:
        return jsonify([])
    recipients = Recipient.query.filter(Recipient.name.ilike(f'%{q}%')).limit(15).all()
    return jsonify([{
        'id':           r.id,
        'name':         r.name,
        'contact':      r.contact,
        'center_id':    r.center_id,
        'center_name':  r.center.name if r.center else '',
        'full_display': f'{r.name} ({r.center.name if r.center else "No Center"})',
    } for r in recipients])
