#!/bin/bash
set -e

# Start SSH
echo "Starting SSH..."
service ssh start

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Running collectstatic..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn promed_backend_api.wsgi:application --bind 0.0.0.0:8000 --workers 3