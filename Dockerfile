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

# Configure SSH for Azure App Service
RUN mkdir -p /var/run/sshd && \
    echo "root:Docker!" | chpasswd && \
    sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' /etc/pam.d/sshd

# Expose ports: 8000 for Django, 2222 for SSH
EXPOSE 8000 2222

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

# Copy and set executable permissions for scripts
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/startup.sh

# Use startup script that launches SSH and the application
CMD ["/usr/local/bin/startup.sh"]