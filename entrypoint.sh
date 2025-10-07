# Delete the old file to remove symbols
rm entrypoint.sh

# Create new file (copy this entire block)
cat > entrypoint.sh << 'EOF'
#!/bin/sh

echo "Starting entrypoint script..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
DB_HOST="${MYSQL_DB_HOST:-mysql-promedhealthplue-dev.mysql.database.azure.com}"
DB_PORT="${MYSQL_DB_PORT:-3306}"

# Wait for database connection
timeout=60
counter=0
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
  counter=$((counter + 1))
  if [ $counter -ge $timeout ]; then
    echo "Database connection timeout after ${timeout} seconds"
    break
  fi
done

echo "Database connection available, running migrations..."

# Apply database migrations
python manage.py migrate --noinput

echo "Starting Gunicorn server..."

# Execute the main command (Note: $@ should be the Gunicorn command)
exec gunicorn --workers 4 --bind 0.0.0.0:8000 promed_backend_api.wsgi:application
EOF

# Make it executable
chmod +x entrypoint.sh

# Verify it was created
ls -la entrypoint.sh

# Check the file type (This should confirm 'ASCII text' or similar, not 'with CRLF line terminators')
file entrypoint.sh