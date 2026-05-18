from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.models import db

limiter = Limiter(key_func=get_remote_address, default_limits=[])
