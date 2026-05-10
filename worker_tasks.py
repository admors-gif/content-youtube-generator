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
        sentry_sdk.set_context(
            "content_factory_task",
            {
                "task_name": self.name,
                "task_id": self.request.id,
                "retry_count": self.request.retries,
            },
        )
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


@celery_app.task(
    bind=True,
    name="content_factory.publish_tiktok_inbox",
    acks_late=False,
    reject_on_worker_lost=False,
)
def publish_tiktok_inbox(self, uid: str, job_id: str):
    """
    Envía un TikTok terminado al Inbox de TikTok.

    A diferencia de producción de video, esta tarea NO se re-encola
    automáticamente si el worker muere: una repetición ciega podría duplicar
    un inbox share externo. La idempotencia real vive en Firestore y en
    api_module._run_tiktok_publish_job.
    """
    try:
        import sentry_sdk
        sentry_sdk.set_tag("tiktok_job_id", job_id)
        sentry_sdk.set_tag("uid", uid)
        sentry_sdk.set_tag("celery_task_id", self.request.id)
        sentry_sdk.set_context(
            "tiktok_publish_task",
            {
                "task_name": self.name,
                "task_id": self.request.id,
                "job_id": job_id,
            },
        )
    except Exception:
        pass

    print(f"[WORKER] publish_tiktok_inbox starting | job_id={job_id} | task_id={self.request.id}", flush=True)
    api_module._run_tiktok_publish_job(uid, job_id)
    print(f"[WORKER] publish_tiktok_inbox finished | job_id={job_id}", flush=True)
    return {"job_id": job_id, "status": "handled"}


@celery_app.task(
    bind=True,
    name="content_factory.ingest_knowledge_pdf",
    autoretry_for=(ConnectionError, TimeoutError),
    max_retries=1,
    retry_backoff=60,
    retry_jitter=True,
)
def ingest_knowledge_pdf(self, job_id: str):
    """Extract, chunk, embed and upsert a PDF into the Knowledge Hub collection."""
    try:
        import sentry_sdk
        sentry_sdk.set_tag("knowledge_job_id", job_id)
        sentry_sdk.set_tag("celery_task_id", self.request.id)
        sentry_sdk.set_context(
            "knowledge_ingest_task",
            {
                "task_name": self.name,
                "task_id": self.request.id,
                "job_id": job_id,
                "retry_count": self.request.retries,
            },
        )
    except Exception:
        pass

    print(f"[WORKER] ingest_knowledge_pdf starting | job_id={job_id} | task_id={self.request.id}", flush=True)
    result = api_module._run_knowledge_ingest_job(job_id)
    print(f"[WORKER] ingest_knowledge_pdf finished | job_id={job_id}", flush=True)
    return result
