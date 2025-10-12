# Start with the official Python slim image (Debian base for apt-get commands)
FROM python:3.11-slim

# Set the working directory for the application
WORKDIR /app

# Install necessary system dependencies and OpenSSH server
# This single RUN command installs:
# 1. Build tools (build-essential, pkg-config, etc.) for compiling Python packages (like mysqlclient)
# 2. Database client headers (default-libmysqlclient-dev)
# 3. Network tool (netcat-openbsd) for the DB check in startup.sh
# 4. SSH components (openssh-server, dialog) for Azure diagnostics
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    pkg-config \
    libcairo2-dev \
    default-libmysqlclient-dev \
    netcat-openbsd \
    openssh-server \
    dialog \
    # Clean up the cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# === AZURE SSH CONFIGURATION (MANDATORY FOR KUDU ACCESS) ===
# 1. Set the root password to 'Docker!' (required by Azure for SSH access)
RUN echo "root:Docker!" | chpasswd
# 2. Create the necessary runtime directory for the SSH daemon to start
RUN mkdir -p /run/sshd

# Copy Python requirements and install them
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the startup script and ensure it is executable
# This path (/app/startup.sh) is critical and must match the Azure App Service setting
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Copy the rest of the application code
COPY . /app/

# Expose the application port (e.g., 8000) AND the Azure SSH port (2222)
EXPOSE 8000 2222

# Define the entrypoint to run the custom startup script
# The script will start SSH, run migrations, and then launch Gunicorn (all as root to satisfy sshd)
ENTRYPOINT ["/app/startup.sh"]