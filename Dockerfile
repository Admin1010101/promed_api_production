# Use official Python 3.11 image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Pre-collect static files (optional, only if you want to do it during build)
RUN python manage.py collectstatic --noinput || true

# Expose port for Render
EXPOSE 8000

# Start the Django app with Gunicorn
CMD ["gunicorn", "promed_backend_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
