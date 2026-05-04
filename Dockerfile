FROM python:3.11-slim-bookworm

# Variables de entorno para Python y Playwright
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Instalación de dependencias de sistema (Consolidadas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalación de dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalación de Playwright (Solo Chromium para ahorrar espacio)
RUN playwright install chromium --with-deps && \
    rm -rf /var/lib/apt/lists/*

# Copia de la aplicación
COPY . .

# Usuario de seguridad
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "fastappi:appi", "--host", "0.0.0.0", "--port", "8000"]
