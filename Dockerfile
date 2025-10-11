# Stage 1: Build the image with dependencies
FROM python:3.11-slim

# Set environment variables for better Python performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory for the application
WORKDIR /app

# Install system dependencies
# Includes build tools (build-essential, pkg-config) and libraries 
# for database drivers (mysqlclient, psycopg2, cairo) and SSH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        netcat-openbsd \
        build-essential \
        libpq-dev \
        default-libmysqlclient-dev \
        libssl-dev \
        openssh-server \
        pkg-config \
        libcairo2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL SSH FIX: Create the necessary runtime directory for sshd
RUN mkdir -p /run/sshd 

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create a non-root user and set permissions
RUN useradd -m appuser
RUN mkdir -p /home/appuser/.ssh && chown -R appuser:appuser /home/appuser

# Configure SSH for Azure App Service
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN echo "AllowUsers root appuser" >> /etc/ssh/sshd_config
EXPOSE 2222

# Copy the rest of the application code
COPY . /app/

# Ensure the app is owned by the non-root user
RUN chown -R appuser:appuser /app

# Make the consolidated startup script executable and copy it
COPY startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

# Use the non-root user for running the application
USER appuser

# Final command to execute the single startup script
CMD ["/usr/local/bin/startup.sh"]