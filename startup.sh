#!/bin/bash

# Stop execution immediately if any command fails (set -e)
set -e

# =======================================================
# 1. SSH DAEMON STARTUP (MUST RUN AS ROOT)
# This is required for the Azure Portal's SSH console (Kudu).
# =======================================================
echo "🔒 Starting SSH Daemon on Port 2222..."
/usr/sbin/sshd

# =======================================================
# 2. WAIT FOR DATABASE CONNECTION
# Uses environment variables set in Azure App Service.
# =======================================================
DB_HOST=${MYSQL_DB_HOST:-database-host}
DB_PORT=${MYSQL_DB_PORT:-3306}
TIMEOUT=30
ELAPSED=0

echo "⏳ Waiting for database connection at $DB_HOST:$DB_PORT..."

while ! nc -z -w 5 "$DB_HOST" "$DB_PORT" && [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    echo "   Database not yet available. Waiting 5 seconds..."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "❌ Database connection failed after 30 seconds. Exiting."
    exit 1
fi

echo "✅ Database is available. Continuing startup."


# =======================================================
# 3. DJANGO SETUP: MIGRATIONS AND STATIC FILES
# 
# ❗ Setting the PYTHONPATH to ensure 'promed_backend_api' is findable.
# =======================================================
# Standard way to add the current application directory to the path:
export PYTHONPATH=$PYTHONPATH:/app

echo "📂 Applying database migrations..."
python manage.py migrate --noinput

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput


# =======================================================
# 4. START GUNICORN (The main container process)
#
# ❗ FIXED: Removed the incorrect PYTHONPATH syntax. The export above 
#    should be inherited by the exec command.
# =======================================================

PORT=${WEBSITES_PORT:-8000} 

echo "🚀 Starting Gunicorn (Django) on 0.0.0.0:$PORT..."

# Reverting to the simpler, correct command structure:
exec gunicorn promed_backend_api.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers 4 \
    --log-level info \
    --timeout 120