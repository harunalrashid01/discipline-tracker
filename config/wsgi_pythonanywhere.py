"""
WSGI configuration for PythonAnywhere deployment.

PythonAnywhere will point to this file.
Make sure to update the path below to match YOUR username.
"""

import os
import sys

# ── Add your project directory to the Python path ──────────────────
# CHANGE 'yourusername' to your actual PythonAnywhere username
path = '/home/yourusername/discipline_tracker'
if path not in sys.path:
    sys.path.insert(0, path)

# ── Set the Django settings module ────────────────────────────────
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# ── Load the .env file ────────────────────────────────────────────
# This reads your SECRET_KEY and other settings from the .env file
import environ
env = environ.Env()
environ.Env.read_env(os.path.join(path, '.env'))

# ── Start the Django application ──────────────────────────────────
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
