FROM python:3.11-slim

WORKDIR /app

# Forzar que Python no bufferee stdout
ENV PYTHONUNBUFFERED=1

# Cache bust ANTES de apt-get para forzar rebuild completo cuando sea necesario
ARG CACHE_BUST=unknown

# Instalar FFmpeg, libass (subtítulos ASS), fonts y dependencias
RUN apt-get update && \
    apt-get install -y ffmpeg libass-dev fonts-montserrat fontconfig && \
    fc-cache -f -v && \
    rm -rf /var/lib/apt/lists/*

# Instalar librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

EXPOSE 8000

# Arrancar el servidor FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
