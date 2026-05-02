"""
Celery application instance for the Content Factory worker.

Usa `content-redis`, instancia DEDICADA del proyecto (definida en docker-compose).
NO reusamos calcom-redis para evitar acoplar a otro proyecto del VPS — si
calcom-redis tiene problemas (lo cual ha pasado), nuestra cola sigue.

Para arrancar workers:
  celery -A worker_app worker --loglevel=info --concurrency=1

`--concurrency=1` porque cada job es CPU+IO heavy (FFmpeg + APIs externas)
y queremos paralelismo entre CONTAINERS, no threads dentro de uno solo.
"""
import os

from celery import Celery

# Broker URL: hostname `content-redis` resoluble dentro del network `default`
# del proyecto (ambos servicios viven en docker-compose.yaml).
# Override via env si en el futuro se mueve a otra ubicacion.
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL", "redis://content-redis:6379/0"
)
# Backend (resultados de tareas) en db separada para aislar
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://content-redis:6379/1"
)

celery_app = Celery(
    "content_factory",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["worker_tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Tracking
    task_track_started=True,           # exposes 'STARTED' state, no solo 'PENDING'
    result_expires=3600 * 24 * 7,      # 7 dias de retencion de resultados

    # Reliability: si un worker muere mid-task, otro lo retoma
    task_acks_late=True,               # ack solo despues de exito
    task_reject_on_worker_lost=True,   # requeue si worker desaparece

    # Concurrency: 1 task por proceso worker (cada produccion es pesada)
    worker_prefetch_multiplier=1,      # no pre-fetch (jobs de 45+ min)
    worker_max_tasks_per_child=10,     # restart worker tras 10 tasks (evita memory leaks)

    # Time limits — producir un video toma ~50 min, hard limit a 90 min por seguridad
    task_time_limit=5400,              # 90 min hard kill
    task_soft_time_limit=5100,         # 85 min soft (raise SoftTimeLimitExceeded)
)
