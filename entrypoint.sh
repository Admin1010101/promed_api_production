#!/bin/sh
set -e

echo "=========================================="
echo "🚀 Starting ProMed Health Plus Backend"
echo "=========================================="

# Database connection wait loop
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
    echo "⏳ Database not ready - waiting 5 seconds..."
    sleep 5
    WAITED=$((WAITED+5))
done

echo "✅ Database is reachable."

# Run collectstatic
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "❌ Static file collection failed. Exiting."
    exit 1
}
echo "✅ Static files collected."

# Run database migrations
echo "📂 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migrations failed. Exiting."
    exit 1
}
echo "✅ Migrations complete."

echo "✅ Initialization complete"
echo "🔥 Launching Gunicorn..."

# Execute the final CMD (from Dockerfile or override)
exec "$@"
