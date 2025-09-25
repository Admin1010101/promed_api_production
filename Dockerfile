# Stage 1: Builder
FROM python:3.11 as builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libmysqlclient21 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu

WORKDIR /app
COPY . .

# Set permissions
RUN chmod +x manage.py

# Collect static files (optional: can be run manually in CI/CD)
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD gunicorn promed_backend_api.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
