#!/bin/bash

# Stop execution immediately if any command fails
set -e

# =======================================================
# 1. SSH DAEMON STARTUP (MUST RUN AS ROOT)
# Required for Azure Portal SSH (Kudu)
# =======================================================
echo "🔒 Starting SSH Daemon on Port 2222..."
/usr/sbin/sshd

# =======================================================
# 2. WAIT FOR DATABASE CONNECTION
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
    echo "❌ Database connection failed after $TIMEOUT seconds. Exiting."
    exit 1
fi

echo "✅ Database is available. Continuing startup."

# =======================================================
# 3. DJANGO SETUP: MIGRATIONS AND STATIC FILES
# =======================================================
export PYTHONPATH=$PYTHONPATH:/app

echo "📂 Applying database migrations..."
python manage.py migrate --noinput

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# =======================================================
# 4. DJANGO SUPERUSER CREATION (Custom User Model)
# Uses environment variables to securely define credentials
# =======================================================
echo "👤 Creating Django superuser if it doesn't exist..."

python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SU_USERNAME', 'wchandler2025')
email = os.environ.get('DJANGO_SU_EMAIL', 'vastyle2010@gmail.com')
password = os.environ.get('DJANGO_SU_PASSWORD', 'devine11')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("✅ Superuser created: \${username}")
else:
    print("ℹ️ Superuser '\${username}' already exists.")
EOF

# =======================================================
# 5. START GUNICORN (The main container process)
# =======================================================
PORT=${WEBSITES_PORT:-8000}

echo "🚀 Starting Gunicorn (Django) on 0.0.0.0:$PORT..."

exec gunicorn promed_backend_api.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers 4 \
    --log-level info \
    --timeout 120
