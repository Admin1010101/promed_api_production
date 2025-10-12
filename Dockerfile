# Start with the official Python slim image (Debian base for apt-get commands)
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory for the application
WORKDIR /app

# Install necessary system dependencies and OpenSSH server
# This single RUN command installs:
# 1. Build tools (build-essential, pkg-config, etc.) for compiling Python packages
# 2. Database client headers (default-libmysqlclient-dev, libpq-dev)
# 3. Network tool (netcat-openbsd) for the DB check in startup.sh
# 4. SSH components (openssh-server) for Azure App Service diagnostics
# 5. SSL libraries (libssl-dev) for secure connections
# 6. curl for health checks
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libcairo2-dev \
        default-libmysqlclient-dev \
        libpq-dev \
        libssl-dev \
        netcat-openbsd \
        openssh-server \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# === AZURE SSH CONFIGURATION (MANDATORY FOR KUDU ACCESS) ===
# 1. Create the necessary runtime directory for the SSH daemon
RUN mkdir -p /run/sshd

# 2. Generate SSH host keys (required for sshd to start)
RUN ssh-keygen -A

# 3. Configure SSH to listen on port 2222 (Azure App Service requirement)
RUN echo "Port 2222" >> /etc/ssh/sshd_config \
    && echo "PermitRootLogin yes" >> /etc/ssh/sshd_config \
    && echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# 4. Set the root password to 'Docker!' (required by Azure for SSH access)
RUN echo "root:Docker!" | chpasswd

# Expose the application port (8000) AND the Azure SSH port (2222)
EXPOSE 8000 2222

# Copy Python requirements and install them
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the startup script and ensure it is executable
# This path (/app/startup.sh) is critical and must match the CMD instruction
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Copy the rest of the application code
COPY . /app/

# Health check to verify the application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Define the command to run the startup script
# The script will start SSH, run migrations, and launch Gunicorn
CMD ["/app/startup.sh"]