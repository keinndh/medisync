import os
from flask import Flask
from flask_cors import CORS
from core.models import db
from core.extensions import limiter


def create_app():
    _root = os.path.dirname(os.path.abspath(__file__))
    root  = os.path.dirname(_root)

    app = Flask(
        __name__,
        static_folder=os.path.join(root, 'static'),
        template_folder=os.path.join(root, 'templates'),
    )

    app.config['SECRET_KEY']                  = os.getenv('SECRET_KEY', 'medisync-dev-key-change-in-prod')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_SAMESITE']     = 'None'
    app.config['SESSION_COOKIE_SECURE']       = True
    app.config['SESSION_COOKIE_HTTPONLY']     = True
    app.config['SESSION_COOKIE_NAME']         = 'ms_session'
    app.config['PERMANENT_SESSION_LIFETIME']  = 3600

    database_url = os.getenv('DATABASE_URL', '')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    if not database_url:
        database_url = 'sqlite:///fallback.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    upload_folder = '/tmp/uploads' if os.getenv('VERCEL') else os.path.join(root, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = upload_folder
    os.makedirs(upload_folder, exist_ok=True)

    db.init_app(app)
    limiter.init_app(app)

    CORS(app,
         supports_credentials=True,
         origins=[
             os.getenv('FRONTEND_URL', ''),
             'http://127.0.0.1:5000',
             'http://localhost:5000',
             'http://localhost:3000',
         ],
         allow_headers=['Content-Type', 'Authorization', 'X-Auth-Token'],
         expose_headers=['X-Auth-Token'])

    from app.routes.pages      import pages
    from app.routes.auth       import auth
    from app.routes.dashboard  import dashboard
    from app.routes.inventory  import inventory
    from app.routes.dispensing import dispensing
    from app.routes.centers    import centers
    from app.routes.logs       import logs
    from app.routes.account    import account

    for bp in (pages, auth, dashboard, inventory, dispensing, centers, logs, account):
        app.register_blueprint(bp)

    with app.app_context():
        _init_db(app)

    return app


def _init_db(app):
    from sqlalchemy import inspect, text
    from core.models import User

    try:
        db.create_all()

        insp      = inspect(db.engine)
        med_cols  = [c['name'] for c in insp.get_columns('medicines')]
        user_cols = [c['name'] for c in insp.get_columns('users')]

        migrations = [
            ('medicines', 'category_type',  "ALTER TABLE medicines ADD COLUMN category_type VARCHAR(200) DEFAULT ''"),
            ('users',     'role',            "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"),
            ('users',     'parent_id',       "ALTER TABLE users ADD COLUMN parent_id INTEGER REFERENCES users(id)"),
            ('users',     'profile_picture', "ALTER TABLE users ADD COLUMN profile_picture TEXT DEFAULT ''"),
        ]
        col_map = {'medicines': med_cols, 'users': user_cols}
        for table, col, sql in migrations:
            if col not in col_map.get(table, []):
                db.session.execute(text(sql))
                db.session.commit()

        _add_auth_tokens_expires_at(insp)

        if not User.query.filter_by(username='admin').first():
            u = User(username='admin', full_name='System Admin', role='admin')
            u.set_password(os.getenv('ADMIN_PASSWORD', 'ChangeMe@1234'))
            db.session.add(u)
            db.session.commit()

    except Exception as e:
        import traceback
        print(f'DB init error: {e}')
        print(traceback.format_exc())
        db.session.rollback()


def _add_auth_tokens_expires_at(insp):
    from sqlalchemy import text
    try:
        token_cols = [c['name'] for c in insp.get_columns('auth_tokens')]
        if 'expires_at' not in token_cols:
            db.session.execute(text(
                "ALTER TABLE auth_tokens ADD COLUMN expires_at TIMESTAMP"
            ))
            db.session.execute(text(
                "UPDATE auth_tokens SET expires_at = created_at + INTERVAL '7 days' WHERE expires_at IS NULL"
            ))
            db.session.commit()
    except Exception:
        db.session.rollback()
