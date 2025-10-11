# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=promed_backend_api.settings

# Set working directory
WORKDIR /app

# Install dependencies + SSH
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libcairo2-dev \
    pkg-config \
    netcat-openbsd \
    curl \
    openssh-server \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir /var/run/sshd && \
    echo "root:YourSecureRootPassword" | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' /etc/pam.d/sshd

# Avoid login warnings
ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip --root-user-action=ignore && \
    pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

# Copy project files
COPY . .

# Copy SSL certificates if needed
COPY ./certs /app/certs

# Create required dirs
RUN mkdir -p /app/staticfiles /app/media

# Copy and set permissions for entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose app and SSH ports
EXPOSE 8000 2222

# Entrypoint script (starts everything)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
