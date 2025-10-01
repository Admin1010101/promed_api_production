#!/bin/bash

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn promed_backend_api.wsgi:application --bind 0.0.0.0:8000 --workers 3
