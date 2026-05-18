import io
import csv
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, send_file

from core.models import db, Medicine, MedicineCategory, manila_today, manila_now
from core.helpers import login_required, log_activity, add_notification

inventory = Blueprint('inventory', __name__, url_prefix='/api')


@inventory.route('/medicines')
@login_required
def api_medicines():
    query  = Medicine.query.filter(Medicine.status != 'Deleted')
    search = request.args.get('search', '')
    if search:
        query = query.filter(db.or_(
            Medicine.article_name.ilike(f'%{search}%'),
            Medicine.stock_number.ilike(f'%{search}%'),
            Medicine.unit_of_measurement.ilike(f'%{search}%'),
            Medicine.status.ilike(f'%{search}%'),
            Medicine.category.ilike(f'%{search}%'),
            Medicine.category_type.ilike(f'%{search}%'),
            Medicine.description_dosage.ilike(f'%{search}%'),
            Medicine.remarks.ilike(f'%{search}%'),
        ))

    status_filter = request.args.get('status', '')
    if status_filter:
        query = query.filter_by(status=status_filter)

    category_filter = request.args.get('category', '')
    if category_filter:
        query = query.filter_by(category=category_filter)

    category_type_filter = request.args.get('category_type', '')
    if category_type_filter:
        query = query.filter(Medicine.category_type.ilike(f'%{category_type_filter}%'))

    date_filter = request.args.get('date_added', '')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Medicine.date_added) == filter_date)
        except ValueError:
            pass

    restocked_filter = request.args.get('restocked_date', '')
    if restocked_filter:
        try:
            filter_date = datetime.strptime(restocked_filter, '%Y-%m-%d').date()
            query = query.filter(Medicine.is_restock == True, db.func.date(Medicine.date_added) == filter_date)
        except ValueError:
            pass

    sort_by = request.args.get('sort', 'date_added')
    if sort_by == 'quantity':
        query = query.order_by(Medicine.quantity.desc())
    elif sort_by == 'alphabetical':
        query = query.order_by(Medicine.article_name.asc())
    elif sort_by == 'stock_number':
        query = query.order_by(Medicine.stock_number.asc())
    else:
        query = query.order_by(Medicine.date_added.desc())

    return jsonify([m.to_dict() for m in query.all()])


@inventory.route('/medicines', methods=['POST'])
@login_required
def api_add_medicine():
    data     = request.get_json()
    exp_date = None
    if data.get('expiration_date'):
        try:
            exp_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid expiration date format.'}), 400

    stock_num = data.get('stock_number', '')
    existing  = Medicine.query.filter_by(stock_number=stock_num).first()
    if existing:
        if data.get('force_add'):
            import time
            stock_num = f'{stock_num}-NEW-{int(time.time())}'
        else:
            return jsonify({'error': 'Stock number already exists.'}), 400

    status = 'Active'
    if exp_date:
        if exp_date <= manila_today():
            status = 'Expired'
        elif exp_date <= manila_today() + timedelta(days=180):
            status = 'Near Expiry'

    med = Medicine(
        stock_number=stock_num,
        article_name=data.get('article_name', ''),
        description_dosage=data.get('description_dosage', ''),
        unit_of_measurement=data.get('unit_of_measurement', ''),
        quantity=int(data.get('quantity', 0)),
        category=data.get('category', ''),
        category_type=data.get('category_type', ''),
        remarks=data.get('remarks', ''),
        expiration_date=exp_date,
        is_new_batch=True,
        status=status,
    )
    db.session.add(med)
    db.session.commit()
    log_activity('Add', f'Added medicine: {med.article_name} (Stock #{med.stock_number})')
    add_notification(f'New medicine added: {med.article_name}', 'info', med.id, 'medicine')
    return jsonify(med.to_dict()), 201


@inventory.route('/medicines/<int:med_id>', methods=['PUT'])
@login_required
def api_edit_medicine(med_id):
    med  = Medicine.query.get_or_404(med_id)
    data = request.get_json()
    med.article_name        = data.get('article_name',        med.article_name)
    med.description_dosage  = data.get('description_dosage',  med.description_dosage)
    med.unit_of_measurement = data.get('unit_of_measurement', med.unit_of_measurement)
    med.quantity            = int(data.get('quantity', med.quantity))
    med.category            = data.get('category',            med.category)
    med.category_type       = data.get('category_type',       med.category_type)
    med.remarks             = data.get('remarks',             med.remarks)

    if data.get('expiration_date'):
        try:
            exp_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
            med.expiration_date = exp_date
            if med.status in ['Active', 'Near Expiry', 'Expired']:
                if exp_date <= manila_today():
                    med.status = 'Expired'
                elif exp_date <= manila_today() + timedelta(days=180):
                    med.status = 'Near Expiry'
                else:
                    med.status = 'Active'
        except ValueError:
            pass

    med.is_new_batch = False
    db.session.commit()
    log_activity('Edit', f'Edited medicine: {med.article_name} (Stock #{med.stock_number})')
    return jsonify(med.to_dict())


@inventory.route('/medicines/<int:med_id>/restock', methods=['POST'])
@login_required
def api_restock_medicine(med_id):
    old_med = Medicine.query.get_or_404(med_id)
    data    = request.get_json()
    qty     = int(data.get('quantity', 0))
    if qty <= 0:
        return jsonify({'error': 'Invalid quantity.'}), 400

    exp_date = None
    if data.get('expiration_date'):
        try:
            exp_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid expiration date format.'}), 400

    status = 'Active'
    if exp_date:
        if exp_date <= manila_today():
            status = 'Expired'
        elif exp_date <= manila_today() + timedelta(days=180):
            status = 'Near Expiry'

    restock_date_str = manila_today().strftime('%m%d%Y')
    new_stock_number = f'{old_med.stock_number}-{restock_date_str}'
    counter = 0
    while Medicine.query.filter_by(stock_number=new_stock_number).first():
        counter += 1
        new_stock_number = f'{old_med.stock_number}-{restock_date_str}-{counter}'

    new_med = Medicine(
        stock_number=new_stock_number,
        article_name=old_med.article_name,
        description_dosage=old_med.description_dosage,
        unit_of_measurement=old_med.unit_of_measurement,
        quantity=qty,
        category=old_med.category,
        category_type=old_med.category_type,
        remarks=old_med.remarks,
        expiration_date=exp_date,
        is_new_batch=False,
        is_restock=True,
        status=status,
    )
    db.session.add(new_med)
    db.session.commit()
    log_activity('Restock', f'Restocked medicine: {new_med.article_name} (New Stock #{new_med.stock_number}) with {qty} {new_med.unit_of_measurement}')
    add_notification(f'Medicine restocked: {new_med.article_name}', 'info', new_med.id, 'medicine')
    return jsonify(new_med.to_dict()), 201


@inventory.route('/medicines/<int:med_id>/discard', methods=['POST'])
@login_required
def api_discard_medicine(med_id):
    med    = Medicine.query.get_or_404(med_id)
    data   = request.get_json()
    reason = data.get('reason', '')
    med.status         = 'Discarded'
    med.discard_reason = reason
    db.session.commit()
    log_activity('Discard', f'Discarded medicine: {med.article_name}. Reason: {reason}')
    add_notification(f'Medicine discarded: {med.article_name}', 'warning', med.id, 'medicine')
    return jsonify(med.to_dict())


@inventory.route('/medicines/<int:med_id>', methods=['DELETE'])
@login_required
def api_delete_medicine(med_id):
    med    = Medicine.query.get_or_404(med_id)
    data   = request.get_json() or {}
    reason = data.get('reason', '')
    med.status        = 'Deleted'
    med.delete_reason = reason
    db.session.commit()
    log_activity('Delete', f'Deleted medicine: {med.article_name}. Reason: {reason}')
    return jsonify({'success': True})


@inventory.route('/medicines/categories')
@login_required
def api_categories():
    med_cats    = db.session.query(Medicine.category).distinct().filter(
        Medicine.category != '', Medicine.category.isnot(None)
    ).all()
    system_cats = MedicineCategory.query.all()
    all_cats    = sorted(list(set([c[0] for c in med_cats] + [c.name for c in system_cats])))
    return jsonify(all_cats)


@inventory.route('/medicines/category-types')
@login_required
def api_category_types():
    cats = db.session.query(Medicine.category_type).distinct().filter(
        Medicine.category_type != '', Medicine.category_type.isnot(None)
    ).all()
    return jsonify(sorted([c[0] for c in cats]))


@inventory.route('/medicines/categories', methods=['POST'])
@login_required
def api_add_category():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Category name is required.'}), 400
    existing = MedicineCategory.query.filter(db.func.lower(MedicineCategory.name) == name.lower()).first()
    if not existing:
        cat = MedicineCategory(name=name)
        db.session.add(cat)
        db.session.commit()
        return jsonify(cat.to_dict()), 201
    return jsonify(existing.to_dict()), 200


@inventory.route('/medicines/search')
@login_required
def api_medicines_search():
    q = request.args.get('q', '')
    if not q:
        return jsonify([])
    meds = Medicine.query.filter(
        Medicine.status.in_(['Active', 'Near Expiry']),
        Medicine.article_name.ilike(f'%{q}%')
    ).with_entities(Medicine.article_name).distinct().limit(10).all()
    return jsonify([m[0] for m in meds])


@inventory.route('/inventory/export/csv')
@login_required
def api_export_csv():
    medicines = Medicine.query.filter(Medicine.status != 'Deleted').order_by(Medicine.date_added.desc()).all()
    output    = io.StringIO()
    writer    = csv.writer(output)
    writer.writerow(['Stock Number', 'Article/Name', 'Description/Dosage', 'Unit of Measurement',
                     'Quantity', 'Category', 'Expiration Date', 'Days To Expire', 'Status', 'Remarks', 'Date Added'])
    for m in medicines:
        d = m.to_dict()
        writer.writerow([
            m.stock_number, m.article_name, m.description_dosage, m.unit_of_measurement,
            m.quantity, m.category,
            m.expiration_date.isoformat() if m.expiration_date else '',
            d.get('days_remaining') if d.get('days_remaining') is not None else '-',
            m.status, m.remarks,
            m.date_added.strftime('%Y-%m-%d %H:%M') if m.date_added else '',
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv', as_attachment=True,
        download_name=f'medisync_inventory_{manila_today().isoformat()}.csv'
    )


@inventory.route('/inventory/export/pdf')
@login_required
def api_export_pdf():
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from flask import current_app
    import os

    medicines   = Medicine.query.filter(Medicine.status != 'Deleted').order_by(Medicine.date_added.desc()).all()
    buffer      = io.BytesIO()
    doc         = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles      = getSampleStyleSheet()
    title_style = ParagraphStyle('StockTitle', parent=styles['Normal'],
                                 fontName='Helvetica-Bold', fontSize=14,
                                 alignment=TA_CENTER, spaceAfter=6)
    sub_style   = ParagraphStyle('StockSubtitle', parent=styles['Normal'],
                                 fontName='Helvetica-Bold', fontSize=12,
                                 alignment=TA_CENTER, spaceAfter=24)
    elements = []

    img_path = os.path.join(current_app.static_folder, 'images', 'print_header.png')
    if os.path.exists(img_path):
        elements.append(Image(img_path, width=10*inch, height=0.975*inch))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(Paragraph('MEDICAL SUPPLIES STOCK ASSESSMENT REPORT', title_style))
    elements.append(Paragraph(f'AS OF: {manila_today().strftime("%B %d, %Y")}', sub_style))

    headers = ['Stock Number', 'Article', 'Dosage', 'Unit', 'Qty.', 'Category', 'Expiration Date', 'Days Left', 'Status']
    data    = [headers]
    for m in medicines:
        d = m.to_dict()
        data.append([
            m.stock_number, m.article_name, m.description_dosage or '',
            m.unit_of_measurement, str(m.quantity), m.category or '',
            m.expiration_date.strftime('%Y-%m-%d') if m.expiration_date else '',
            str(d.get('days_remaining')) if d.get('days_remaining') is not None else '-',
            m.status,
        ])

    col_widths = [1*inch, 1.8*inch, 1.2*inch, 0.8*inch, 0.6*inch, 1.2*inch, 1*inch, 0.7*inch, 0.9*inch]
    table      = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0),  colors.HexColor('#0284c7')),
        ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0),  9),
        ('FONTSIZE',    (0, 1), (-1, -1), 8),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('GRID',        (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.6*inch))

    sig_data = [
        ['Approved By:', '', 'Certified Correct By:'],
        ['\n\n\n', '', '\n\n\n'],
        ['Signature Over Printed Name of Head of Agency/Entity\nof Authorized Representative', '',
         'Signature Over Printed Name of Inventor Committee\nChair and Members'],
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 2*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME',  (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 10),
        ('ALIGN',     (0, 0), (0, -1),  'LEFT'),
        ('ALIGN',     (2, 0), (2, -1),  'LEFT'),
        ('VALIGN',    (0, 0), (-1, -1), 'BOTTOM'),
        ('LINEBELOW', (0, 1), (0, 1),   1, colors.black),
        ('LINEBELOW', (2, 1), (2, 1),   1, colors.black),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                     download_name=f'medisync_inventory_{manila_today().isoformat()}.pdf')
