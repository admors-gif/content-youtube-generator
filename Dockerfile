FROM python:3.11-slim

WORKDIR /app

# Forzar que Python no bufferee stdout — los prints se ven en Docker logs en tiempo real
ENV PYTHONUNBUFFERED=1

# Instalar FFmpeg, libass (subtítulos ASS), fonts y dependencias
RUN apt-get update && \
    apt-get install -y ffmpeg libass-dev fonts-montserrat fontconfig && \
    fc-cache -f -v && \
    rm -rf /var/lib/apt/lists/*

# Instalar librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto (CACHE_BUST fuerza rebuild)
ARG CACHE_BUST=unknown
COPY . .

EXPOSE 8000

# Arrancar el servidor FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
