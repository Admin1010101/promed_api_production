#!/bin/sh
set -e  # Exit on error

echo "=========================================="
echo "Starting ProMed Health Plus Backend"
echo "=========================================="

# Simple database wait with timeout
echo "Checking database connection..."
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"

# Try to connect, but don't block startup if it fails
if nc -z -w5 "$DB_HOST" "$DB_PORT"; then
    echo "✓ Database is reachable"
else
    echo "⚠ Warning: Could not reach database at $DB_HOST:$DB_PORT"
    echo "  Continuing anyway - Django will handle connection errors"
fi

# Run migrations (will fail gracefully if DB is unreachable)
echo "Running database migrations..."
python manage.py migrate --noinput 2>&1 || {
    echo "⚠ Warning: Migrations failed or skipped"
    echo "  Application will start but may not function correctly"
}

# Collect static files to Azure Storage
echo "Collecting static files to Azure..."
python manage.py collectstatic --noinput 2>&1 || {
    echo "⚠ Warning: Static file collection failed"
    echo "  This may affect admin panel styling"
}

echo "=========================================="
echo "✓ Initialization complete"
echo "Starting Gunicorn on 0.0.0.0:8000"
echo "=========================================="

# Execute gunicorn
exec "$@"