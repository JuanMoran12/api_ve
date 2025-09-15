# Use Python 3.13 slim image
#FROM python:3.13-slim
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies for MariaDB and Playwright
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y mariadb-client

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
#RUN playwright install chromium
#RUN playwright install-deps chromium

# Instala dependencias de navegadores
RUN playwright install-deps

# Instala todos los navegadores por defecto (chromium, firefox, webkit)
RUN playwright install

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# No health check needed

# Run the application
CMD ["uvicorn", "fastappi:appi", "--host", "0.0.0.0", "--port", "8000"]
