from flask import Blueprint, render_template, redirect, url_for, session, request
from core.helpers import login_required, check_expirations

pages = Blueprint('pages', __name__)


@pages.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('pages.dashboard_page'))
    return redirect(url_for('pages.login_page'))


@pages.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('pages.dashboard_page'))
    return render_template('login.html')


@pages.route('/dashboard')
@login_required
def dashboard_page():
    check_expirations()
    return render_template('dashboard.html')


@pages.route('/inventory')
@login_required
def inventory_page():
    return render_template('inventory.html')


@pages.route('/inventory/print')
@login_required
def inventory_print():
    from core.models import Medicine, manila_today
    medicines = Medicine.query.filter(Medicine.status != 'Deleted').order_by(Medicine.date_added.desc()).all()
    return render_template('inventory_print.html', medicines=medicines, current_date=manila_today().strftime('%B %d, %Y'))


@pages.route('/dispensing')
@login_required
def dispensing_page():
    return render_template('dispensing.html')


@pages.route('/centers')
@login_required
def centers_page():
    return render_template('centers.html')


@pages.route('/logs')
@login_required
def logs_page():
    return render_template('logs.html')


@pages.route('/account')
@login_required
def account_page():
    return render_template('account.html')


@pages.route('/settings')
@login_required
def settings_page():
    return redirect(url_for('pages.account_page'))
