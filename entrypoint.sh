#!/bin/sh
set -e

echo "=========================================="
echo "Starting ProMed Health Plus Backend"
echo "=========================================="

# Define DB connection details
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"
MAX_WAIT=30
WAITED=0

# Robust database wait loop (CRITICAL for collectstatic/migrate)
echo "Checking database connection..."
while ! nc -z -w5 "$DB_HOST" "$DB_PORT"; do
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "🚨 ERROR: Database connection failed after $MAX_WAIT seconds. Exiting."
        exit 1 # Exit the container if DB is unreachable after max wait
    fi
    echo "Database is unavailable - waiting 5 seconds..."
    sleep 5
    WAITED=$((WAITED+5))
done
echo "✓ Database is reachable."

# Collect static files to Azure Storage (Flag --clear removed to fix ValueError)
echo "Collecting static files to Azure..."
python manage.py collectstatic --noinput || { # <-- CORRECTED LINE
    echo "🚨 ERROR: Static file collection failed. Exiting deployment."
    exit 1 # Exit on static file failure to prevent broken admin
}
echo "✓ Static files collected."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput
echo "✓ Migrations complete."

echo "=========================================="
echo "✓ Initialization complete"
echo "Starting Gunicorn on 0.0.0.0:8000"
echo "=========================================="

# Execute gunicorn
exec "$@"