#!/bin/sh
set -e  # Exit on error

echo "=========================================="
echo "Starting ProMed Health Plus Backend"
echo "=========================================="

# Wait for database
echo "Waiting for database to be ready..."
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"
timeout=60
counter=0

while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -ge $timeout ]; then
        echo "ERROR: Database connection timeout after ${timeout} seconds"
        exit 1
    fi
    if [ $((counter % 10)) -eq 0 ]; then
        echo "Still waiting for database... (${counter}s elapsed)"
    fi
done

echo "✓ Database is available"

# Run database migrations FIRST
echo "Running database migrations..."
python manage.py migrate --noinput || {
    echo "ERROR: Database migrations failed"
    exit 1
}
echo "✓ Database migrations complete"

# Collect static files AFTER migrations
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || {
    echo "WARNING: collectstatic failed, but continuing..."
    # Don't exit - static files not critical for API
}
echo "✓ Static files collected (or skipped)"

echo "=========================================="
echo "Starting Gunicorn server on port 8000..."
echo "=========================================="

# Execute the CMD from Dockerfile (gunicorn command)
exec "$@"