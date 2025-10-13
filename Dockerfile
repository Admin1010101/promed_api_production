# Use Python 3.12 with Debian Bookworm base
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libssl-dev \
        libffi-dev \
        default-libmysqlclient-dev \
        libpq-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libxml2-dev \
        libxslt1-dev \
        libsm6 \
        libxext6 \
        libraqm-dev \
        libharfbuzz-dev \
        libfreetype6-dev \
        netcat-openbsd \
        openssh-server \
        curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# SSH for Kudu
RUN mkdir -p /run/sshd && \
    ssh-keygen -A && \
    echo "Port 2222" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "root:Docker!" | chpasswd

EXPOSE 8000 2222

# Copy Python requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ❗ Copy the rest of the code (including potentially broken startup.sh)
COPY . /app/

# ❗ Overwrite startup.sh and fix line endings + permissions LAST
COPY startup.sh /app/startup.sh
RUN sed -i 's/\r$//' /app/startup.sh && \
    chmod +x /app/startup.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the startup script
CMD ["/app/startup.sh"]
