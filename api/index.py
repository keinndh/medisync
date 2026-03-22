import sys
import os

# Add parent directory to path so we can import app.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel looks for 'app' or 'handler' at module level
handler = app
