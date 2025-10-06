# Use official Python 3.11 image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
# ----------------------------------------------------------------------
# IMPORTANT CHANGE: Replaced libpq-dev (PostgreSQL) with
# default-libmysqlclient-dev (MySQL/MariaDB client libraries)
# ----------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    # MySQL/MariaDB development libraries
    default-libmysqlclient-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Pre-collect static files (optional)
RUN python manage.py collectstatic --noinput || true

# Expose port for Render or local development
EXPOSE 8000

# Start the Django app with Gunicorn, binding to the port specified by the Azure 'PORT' environment variable
CMD gunicorn promed_backend_api.wsgi:application --bind 0.0.0.0:$PORT --workers 3

COPY ./certs /usr/src/app/certs 