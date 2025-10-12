# Start with the official Python image
FROM python:3.11-slim

# Set the working directory for the application
WORKDIR /app

# Install necessary system dependencies for Python packages (mysqlclient, netcat, etc.)
# AND the OpenSSH Server for Azure debugging.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    libcairo2-dev \
    netcat \
    openssh-server \
    dialog \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# === AZURE SSH CONFIGURATION (MANDATORY FIXES) ===
# 1. Set the root password to 'Docker!' (required by Azure for SSH access)
RUN echo "root:Docker!" | chpasswd

# 2. Create the necessary runtime directory for the SSH daemon to start without crashing
RUN mkdir -p /run/sshd

# 3. Use a custom SSH configuration file (assuming you create one named sshd_config in project root)
# If you don't have one, Azure uses a default, but it's safer to provide one that enforces Port 2222
# COPY sshd_config /etc/ssh/

# Copy the required startup script and ensure it is executable
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# === SECURITY AND USER SETUP ===
# Create a non-root user to run the main application processes
RUN useradd -m appuser

# Expose the application port (e.g., 8000) AND the Azure SSH port (2222)
EXPOSE 8000 2222

# Switch to the non-root user *before* the application runs
# NOTE: The startup.sh script MUST contain the SSH startup before any user switch if used.
# Since our script handles multiple commands, we will leave the USER switch out and 
# handle non-root execution inside the startup.sh, or just run as root for simplicity.
# Leaving as root for now simplifies startup.sh, as root is required for sshd start.

# Define the entrypoint to run the custom startup script
ENTRYPOINT ["/app/startup.sh"]
# CMD ["/app/startup.sh"] # Using ENTRYPOINT here is common for custom startup scripts