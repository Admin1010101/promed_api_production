# Stage 1: Build the image with dependencies
# Use a Python base image suitable for production
FROM python:3.11-slim

# Fix ENV warnings and set environment variables for performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory for the application
WORKDIR /app

# Install system dependencies
# Corrected 'default-libmysqlclient-dev' resolves the exit code 100 build error.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        netcat-openbsd \
        build-essential \
        libpq-dev \
        default-libmysqlclient-dev \
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
RUN useradd -m appuser
RUN mkdir -p /home/appuser/.ssh && chown -R appuser:appuser /home/appuser

# Configure SSH for Azure App Service
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# The following line is often required to allow SSH connections
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