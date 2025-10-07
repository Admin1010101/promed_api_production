# Use official Python 3.11 image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
    
# Set working directory
WORKDIR /app

# Install system dependencies
# Include libraries necessary for psycopg2-binary (PostgreSQL) if needed, 
# although default-libmysqlclient-dev is correct for MySQL/MariaDB.
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libcairo2-dev \
    pkg-config \
    # Clean up APT caches to reduce image size
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files and certificates
COPY . .
COPY ./certs /app/certs

# Pre-collect static files during the build process
# This prevents it from being a slow step during container runtime
# The || true ensures the build doesn't fail if no static files are present
RUN python manage.py collectstatic --noinput || true

# Install netcat (or add to your existing RUN apt-get line)
RUN apt-get update && apt-get install -y netcat-openbsd

# Copy and set executable permissions for the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose port
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["gunicorn", "promed_backend_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]