# Use official Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=promed_backend_api.settings \
    NOTVISIBLE=in-users-profile

# Set working directory
WORKDIR /app

# Install system dependencies and OpenSSH server
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    libcairo2-dev \
    pkg-config \
    netcat-openbsd \
    curl \
    openssh-server \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Setup SSH server config
RUN echo "root:YourSecureRootPassword" | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' /etc/pam.d/sshd

# Expose SSH port (optional, typically 22)
EXPOSE 22

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip --root-user-action=ignore && \
    pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

# Copy project files
COPY . .

# Copy SSL certs for MySQL
COPY ./certs /app/certs

# Create static and media folders
RUN mkdir -p /app/staticfiles /app/media

# Copy and set executable permissions for the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose Django app port
EXPOSE 8000

# Run sshd in the background and start your app via entrypoint
CMD service ssh start && /usr/local/bin/entrypoint.sh gunicorn promed_backend_api.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --access-logfile - --error-logfile -
