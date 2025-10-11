# Stage 1: Build the image with dependencies
# Use a Python base image suitable for production
FROM python:3.11-slim

# Set environment variables for better Python and container performance
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Set the working directory for the application
WORKDIR /app

# Install system dependencies required for typical Python libraries (like 'psycopg2' or 'mysqlclient')
# Update and install necessary packages, then clean up the cache
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        netcat-openbsd \
        build-essential \
        libpq-dev \
        libmysqlclient-dev \
        libssl-dev \
        openssh-server \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create a non-root user and SSH directory
# Creating the user 'appuser' for better security
RUN useradd -m appuser
RUN mkdir -p /home/appuser/.ssh && chown -R appuser:appuser /home/appuser

# Configure SSH for Azure App Service
# The default user is expected to be 'appuser' for security
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# Add this line to ensure SSH works correctly over port 2222
RUN sed -i 's/AllowUsers root/AllowUsers root appuser/' /etc/ssh/sshd_config
EXPOSE 2222

# Copy the rest of the application code
COPY . /app/

# Ensure the app is owned by the non-root user
RUN chown -R appuser:appuser /app

# Make the consolidated startup script executable and copy it
# This script handles SSH, DB check, Migrations, Static files, and Gunicorn launch
COPY startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

# Use the non-root user for running the application
USER appuser

# Final command to execute the single startup script
CMD ["/usr/local/bin/startup.sh"]