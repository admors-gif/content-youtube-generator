"""
Celery tasks for the Content Factory production pipeline.

Cada task encapsula un paso de produccion. La principal es `produce_video`
que reusa `run_production` de api.py — asi mantenemos la logica de la
pipeline en un solo lugar; el worker solo aporta queue + retry + paralelismo.
"""
import os

from celery.exceptions import SoftTimeLimitExceeded

from worker_app import celery_app

# Importar api.py ejecuta su modulo a nivel top (Sentry init, structlog, etc.)
# Eso es OK: las inicializaciones son idempotentes y necesarias en el worker
# tambien (queremos errors del worker capturados por Sentry, logs estructurados).
import api as api_module


@celery_app.task(
    bind=True,
    name="content_factory.produce_video",
    autoretry_for=(ConnectionError, TimeoutError),
    max_retries=2,
    retry_backoff=60,           # 60s, 120s, 240s
    retry_backoff_max=600,
    retry_jitter=True,
)
def produce_video(self, project_id: str):
    """
    Ejecuta la pipeline cinematica completa para un proyecto.
    Reusa la logica de `api_module.run_production` para no duplicar.
    """
    try:
        import sentry_sdk
        sentry_sdk.set_tag("project_id", project_id)
        sentry_sdk.set_tag("celery_task_id", self.request.id)
        sentry_sdk.set_tag("retry_count", self.request.retries)
    except Exception:
        pass

    print(f"[WORKER] produce_video starting | project_id={project_id} | task_id={self.request.id} | retry={self.request.retries}", flush=True)

    try:
        api_module.run_production(project_id)
        print(f"[WORKER] produce_video finished OK | project_id={project_id}", flush=True)
        return {"project_id": project_id, "status": "completed"}
    except SoftTimeLimitExceeded:
        # 85 min sin terminar — Celery va a hard-kill en 5 min mas
        print(f"[WORKER] SOFT TIME LIMIT exceeded for {project_id}; will be killed soon", flush=True)
        # No re-raise: dejamos que Celery termine sin retry (algo esta muy mal)
        raise
    except Exception as e:
        print(f"[WORKER] produce_video FAILED | project_id={project_id} | error={e}", flush=True)
        # Re-raise para que Celery decida retry segun autoretry_for
        raise
