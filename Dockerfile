# Use official Python 3.11 image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=promed_backend_api.settings

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libcairo2-dev \
    pkg-config \
    netcat-openbsd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files and certificates
COPY . .
COPY ./certs /app/certs

# DEBUG: Check if WhiteNoise is installed
RUN echo "=== Checking WhiteNoise installation ===" && \
    python -c "import whitenoise; print(f'WhiteNoise version: {whitenoise.__version__}')" && \
    echo "WhiteNoise is installed!"

# DEBUG: Check Django settings
RUN echo "=== Checking Django STORAGES configuration ===" && \
    python manage.py diffsettings | grep -i storage || echo "Could not read storage settings"

# Run collectstatic with full traceback to see the actual error
RUN echo "=== Running collectstatic with full error output ===" && \
    python manage.py collectstatic --noinput --clear --traceback

# Copy and set executable permissions for the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose port
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "promed_backend_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]