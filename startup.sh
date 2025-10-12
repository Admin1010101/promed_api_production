#!/bin/bash
set -e  # Exit on any error
set -x  # Print every command (THIS IS KEY FOR DEBUGGING)

echo "=========================================="
echo "🚀 Starting ProMed Health Plus Backend"
echo "=========================================="
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Python location: $(which python)"
echo "Gunicorn location: $(which gunicorn)"

# Test if gunicorn is actually installed
if ! command -v gunicorn &> /dev/null; then
    echo "❌ CRITICAL: Gunicorn is NOT installed!"
    exit 1
fi

echo "✅ Gunicorn found at: $(which gunicorn)"

# Start SSH
echo "🔑 Starting SSH service..."
if /usr/sbin/sshd -D -p 2222 & then
    echo "✅ SSH started with PID: $!"
else
    echo "⚠️ SSH failed to start, continuing anyway..."
fi

sleep 2

# Database check
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"
MAX_WAIT=30
WAITED=0

echo "🔍 Checking database connection to $DB_HOST:$DB_PORT..."

while ! nc -z -w5 "$DB_HOST" "$DB_PORT"; do
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "❌ Database connection failed after $MAX_WAIT seconds."
        echo "⚠️ Continuing anyway to see if Gunicorn starts..."
        break
    fi
    echo "⏳ Waiting 5 seconds for database..."
    sleep 5
    WAITED=$((WAITED+5))
done

echo "✅ Database check complete."

# Static files - don't let this fail
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 || {
    echo "⚠️ Static collection failed, continuing..."
}

# Migrations - don't let this stop Gunicorn
echo "📂 Applying database migrations..."
python manage.py migrate --noinput 2>&1 || {
    echo "⚠️ Migration failed, continuing to start server anyway..."
}

echo "✅ Pre-flight checks complete."
echo "=========================================="
echo "🔥 ATTEMPTING TO START GUNICORN NOW"
echo "=========================================="
echo "Command: gunicorn promed_backend_api.wsgi:application --bind 0.0.0.0:8000"

# Try running without exec first to see error output
gunicorn promed_backend_api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug