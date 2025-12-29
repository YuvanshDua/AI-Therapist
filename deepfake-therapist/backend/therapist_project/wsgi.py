"""
WSGI config for therapist_project.

Standard WSGI configuration (used when WebSocket is not needed).
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'therapist_project.settings')

application = get_wsgi_application()
