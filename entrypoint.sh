#!/bin/sh
echo "Starting entrypoint script..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"

timeout=60
counter=0
while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -ge $timeout ]; then
        echo "Database connection timeout after ${timeout} seconds"
        exit 1
    fi
done

echo "Database is available. Running migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn server..."
exec gunicorn promed_backend_api.wsgi:application --workers 4 --bind 0.0.0.0:8000 --timeout 120