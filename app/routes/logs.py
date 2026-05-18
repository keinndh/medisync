import io
import csv
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, send_file

from core.models import db, Medicine, Dispensing, ActivityLog, manila_today, manila_now
from core.helpers import login_required, log_activity

logs = Blueprint('logs', __name__, url_prefix='/api')


@logs.route('/logs')
@login_required
def api_logs():
    query         = ActivityLog.query
    action_filter = request.args.get('action', '')
    if action_filter:
        query = query.filter_by(action=action_filter)

    search = request.args.get('search', '')
    if search:
        query = query.filter(db.or_(
            ActivityLog.details.ilike(f'%{search}%'),
            ActivityLog.performed_by.ilike(f'%{search}%'),
        ))

    for field in ('recipient', 'center', 'medicine'):
        val = request.args.get(field, '')
        if val:
            query = query.filter(ActivityLog.details.ilike(f'%{val}%'))

    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    if date_from:
        try:
            df    = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(db.func.date(ActivityLog.timestamp) >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt    = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(db.func.date(ActivityLog.timestamp) <= dt)
        except ValueError:
            pass

    return jsonify([l.to_dict() for l in query.order_by(ActivityLog.timestamp.desc()).limit(500).all()])


@logs.route('/logs/export/csv')
@login_required
def api_logs_export_csv():
    all_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    output   = io.StringIO()
    writer   = csv.writer(output)
    writer.writerow(['ID', 'Timestamp', 'Action', 'Performed By', 'Details'])
    for l in all_logs:
        writer.writerow([
            l.id,
            l.timestamp.strftime('%Y-%m-%d %H:%M') if l.timestamp else '',
            l.action, l.performed_by, l.details,
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv', as_attachment=True,
        download_name=f'medisync_logs_{manila_today().isoformat()}.csv'
    )


@logs.route('/logs/export/pdf')
@login_required
def api_logs_export_pdf():
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    all_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(1000).all()
    buffer   = io.BytesIO()
    doc      = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles   = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph('MediSync - Activity Logs Report', styles['Title']))
    elements.append(Paragraph(f'Generated: {manila_now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))

    headers = ['ID', 'Timestamp', 'Action', 'Performed By', 'Details']
    data    = [headers]
    for l in all_logs:
        data.append([
            str(l.id),
            l.timestamp.strftime('%Y-%m-%d %H:%M') if l.timestamp else '',
            l.action, l.performed_by, l.details,
        ])

    table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1.5*inch, 5.5*inch], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#5CB9A4')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  9),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                     download_name=f'medisync_logs_{manila_today().isoformat()}.pdf')


@logs.route('/logs/archive', methods=['POST'])
@login_required
def api_logs_archive():
    six_months_ago = manila_now() - timedelta(days=180)
    old_logs       = ActivityLog.query.filter(ActivityLog.timestamp <= six_months_ago).order_by(ActivityLog.timestamp.asc()).all()
    if not old_logs:
        return jsonify({'error': 'No logs older than 6 months found.'}), 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Timestamp', 'Action', 'Performed By', 'Details'])
    for l in old_logs:
        writer.writerow([
            l.id,
            l.timestamp.strftime('%Y-%m-%d %H:%M') if l.timestamp else '',
            l.action, l.performed_by, l.details,
        ])
        db.session.delete(l)
    db.session.commit()
    log_activity('System', f'Archived and deleted {len(old_logs)} logs older than 6 months.')

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv', as_attachment=True,
        download_name=f'medisync_archived_logs_{manila_today().isoformat()}.csv'
    )


@logs.route('/analytics/expired')
@login_required
def api_analytics_expired():
    medicines = Medicine.query.filter(
        Medicine.expiration_date.isnot(None),
        Medicine.expiration_date <= manila_today(),
        Medicine.status.in_(['Expired', 'Discarded', 'Active', 'Near Expiry'])
    ).all()
    return jsonify([m.to_dict() for m in medicines])


@logs.route('/analytics/expiring')
@login_required
def api_analytics_expiring():
    from datetime import timedelta
    today     = manila_today()
    threshold = today + timedelta(days=30)
    medicines = Medicine.query.filter(
        Medicine.status.in_(['Active', 'Near Expiry']),
        Medicine.expiration_date.isnot(None),
        Medicine.expiration_date > today,
        Medicine.expiration_date <= threshold,
    ).all()
    return jsonify([m.to_dict() for m in medicines])


@logs.route('/analytics/status-chart')
@login_required
def api_analytics_status_chart():
    return jsonify({
        'labels': ['Active', 'Near Expiry', 'Expired', 'Discarded', 'Dispensed'],
        'values': [
            Medicine.query.filter_by(status='Active').count(),
            Medicine.query.filter_by(status='Near Expiry').count(),
            Medicine.query.filter_by(status='Expired').count(),
            Medicine.query.filter_by(status='Discarded').count(),
            Dispensing.query.count(),
        ],
        'colors': ['#5CB9A4', '#F4B938', '#FC6F5D', '#9e9e9e', '#2B2B43'],
    })
