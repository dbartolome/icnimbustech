FROM python:3.13-slim

WORKDIR /app

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY app/ app/
COPY db/ db/
COPY entrypoint.sh entrypoint.sh

# Usuario sin privilegios
RUN useradd -m -u 1001 sgsuser && chown -R sgsuser:sgsuser /app
USER sgsuser

EXPOSE 8000

CMD ["bash", "/app/entrypoint.sh"]
