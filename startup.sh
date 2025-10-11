#!/bin/sh
set -e

echo "=========================================="
echo "🚀 Starting ProMed Health Plus Backend"
echo "=========================================="

# 🔑 1. Start SSH daemon in background for Azure App Service
echo "🔑 Starting SSH service with /usr/sbin/sshd -D &..."
/usr/sbin/sshd -D &

# Give SSH a moment to initialize
sleep 2

# Database connection wait loop (from your old entrypoint.sh)
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"
MAX_WAIT=30
WAITED=0

echo "🔍 Checking database connection to $DB_HOST:$DB_PORT..."

while ! nc -z -w5 "$DB_HOST" "$DB_PORT"; do
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "❌ Database connection failed after $MAX_WAIT seconds. Exiting."
        exit 1
    fi
    echo "⏳ Waiting 5 seconds for database..."
    sleep 5
    WAITED=$((WAITED+5))
done

echo "✅ Database is reachable."

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "❌ Static file collection failed."
    # Allowing startup even if static fails, but you can change this
}
echo "✅ Static files collected."

# Run migrations
echo "📂 Applying database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed."
    exit 1
}
echo "✅ Migrations complete."

# 🔥 2. Start Gunicorn (The final command must use 'exec')
echo "🔥 Launching Gunicorn app server..."
exec gunicorn promed_backend_api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -