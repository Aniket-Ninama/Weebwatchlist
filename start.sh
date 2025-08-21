#!/bin/bash
# Run migrations
python manage.py makemigrations --noinput
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create or update superuser
python - <<END
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Weebwatchlist.settings')
import django
django.setup()

from django.contrib.auth.models import User

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "defaultpassword")

user, created = User.objects.get_or_create(username=username, defaults={"email": email})
user.email = email
user.is_superuser = True
user.is_staff = True
user.set_password(password)  # always reset to env password
user.save()

print(f"Superuser '{username}' ensured (created={created})")
END

# Start Gunicorn
gunicorn Weebwatchlist.wsgi:application --bind 0.0.0.0:8000 --workers 3