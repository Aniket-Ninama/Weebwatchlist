#!/bin/bash
# Run migrations
python manage.py migrate

# Create superuser if it doesn't exist
python - <<END
from django.contrib.auth.models import User
import os

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "defaultpassword")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
END

# Start Gunicorn
gunicorn Weebwatchlist.wsgi:application --bind 0.0.0.0:8000 --workers 3

