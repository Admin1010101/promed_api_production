#!/bin/bash
set -e

# Start SSH daemon in background for Azure App Service
echo "Initializing SSH daemon..."
/usr/sbin/sshd -D &

# Give SSH a moment to initialize
sleep 2

# Call entrypoint script with gunicorn arguments
echo "Calling entrypoint script..."
exec /usr/local/bin/entrypoint.sh gunicorn promed_backend_api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -