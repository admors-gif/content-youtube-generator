from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import subprocess
import os
import sys
import json
import logging
import base64
import hashlib
import hmac
import secrets
import time
import urllib.request
import urllib.parse
import re
from datetime import timedelta, datetime, timezone
from pathlib import Path
from scripts.media_validation import (
    pick_valid_final_video as _pick_valid_final_video_impl,
    validate_media_file as _validate_media_file,
)
from scripts.sentry_observability import (
    sanitize_sentry_event as _sanitize_sentry_event,
    tag_sentry_project as _tag_sentry_project,
)
from scripts.brand_profiles import DEFAULT_BRAND_PROFILE_ID, brand_profile_snapshot
from scripts.radar import (
    DEFAULT_CATEGORY as RADAR_DEFAULT_CATEGORY,
    DEFAULT_INTENT as RADAR_DEFAULT_INTENT,
    DEFAULT_LANGUAGE as RADAR_DEFAULT_LANGUAGE,
    DEFAULT_MARKET as RADAR_DEFAULT_MARKET,
    DEFAULT_WINDOW as RADAR_DEFAULT_WINDOW,
    MAX_AGENT_LIMIT as RADAR_MAX_AGENT_LIMIT,
    MAX_MANUAL_LIMIT as RADAR_MAX_MANUAL_LIMIT,
    NEWS_AGENT_ID as RADAR_NEWS_AGENT_ID,
    RADAR_CACHE_TTL_SECONDS,
    apply_llm_ranking as _radar_apply_llm_ranking,
    build_agent_queries as _radar_build_agent_queries,
    build_ranking_prompt as _radar_build_ranking_prompt,
    cache_key as _radar_cache_key,
    canonical_title_key as _radar_canonical_title_key,
    compact_text as _radar_compact_text,
    dedupe_candidates as _radar_dedupe_candidates,
    fallback_candidates_for_agent as _radar_fallback_candidates_for_agent,
    parse_ranking_response as _radar_parse_ranking_response,
    tavily_results_to_candidates as _radar_tavily_results_to_candidates,
)
from scripts.knowledge import (
    DEFAULT_COLLECTION as KNOWLEDGE_DEFAULT_COLLECTION,
    MAX_SEARCH_LIMIT as KNOWLEDGE_MAX_SEARCH_LIMIT,
    KnowledgeConfig,
    KnowledgeError,
    QdrantKnowledgeClient,
    book_filter as _knowledge_book_filter,
    build_points as _knowledge_build_points,
    chunk_text as _knowledge_chunk_text,
    document_blob_type as _knowledge_document_blob_type,
    embed_texts as _knowledge_embed_texts,
    extract_document_text as _knowledge_extract_document_text,
    payload_category as _knowledge_payload_category,
    payload_blob_type as _knowledge_payload_blob_type,
    payload_content as _knowledge_payload_content,
    payload_book_title as _knowledge_payload_book_title,
    scan_book_index as _knowledge_scan_book_index,
    search_filter as _knowledge_search_filter,
    stable_book_id as _knowledge_book_id,
)

FIREBASE_STORAGE_BUCKET = os.environ.get(
    "FIREBASE_STORAGE_BUCKET",
    "content-factory-5cbcb.firebasestorage.app",
)
BASE_DIR = Path(__file__).resolve().parent

# ── Observabilidad ────────────────────────────────────────────────────────────
# 1) Sentry: captura errores no-handleados con stack trace.
#    Se activa solo si SENTRY_DSN está en .env, así dev local no envía nada.
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        sentry_integrations = [
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ]
        try:
            from sentry_sdk.integrations.celery import CeleryIntegration
            sentry_integrations.append(CeleryIntegration())
        except Exception:
            pass

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=sentry_integrations,
            traces_sample_rate=0.1,    # 10% de requests trackean performance
            profiles_sample_rate=0.0,   # Profiling desactivado (caro)
            environment=os.environ.get("ENV", "production"),
            release=os.environ.get("GIT_SHA", "unknown"),
            send_default_pii=False,     # No enviar IPs ni headers sensibles
            before_send=_sanitize_sentry_event,
        )
        print(f"Sentry initialized (env={os.environ.get('ENV','production')})", flush=True)
    except Exception as e:
        print(f"Sentry init failed: {e}", flush=True)
# 2) structlog: logs estructurados (JSON en prod, pretty en dev).
#    Reemplaza print() con logger.info(event, **kwargs).
try:
    import structlog
    _is_tty = sys.stderr.isatty()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (structlog.dev.ConsoleRenderer(colors=True) if _is_tty
             else structlog.processors.JSONRenderer()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    log = structlog.get_logger("content-factory")
    log.info("logger_initialized", env=os.environ.get("ENV", "production"))
except Exception as _log_err:
    # Fallback a logging stdlib si structlog no está
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("content-factory")
    log.warning(f"structlog init failed, using stdlib logging: {_log_err}")

# ── Escribir firebase-admin.json desde variable de entorno (si existe) ──
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS", "")
if firebase_creds:
    cred_path = "/app/firebase-admin.json"
    try:
        import base64
        try:
            decoded = base64.b64decode(firebase_creds).decode("utf-8")
            json.loads(decoded)
            firebase_creds = decoded
        except Exception:
            pass  # Ya es JSON raw

        # Normalización defensiva: des-escapar \\n en private_key si viene
        # doble-escapado (problema común con creds pegados desde JSON anidado).
        try:
            data = json.loads(firebase_creds)
            pk = data.get("private_key", "")
            if "\\n" in pk and "BEGIN" in pk:
                data["private_key"] = pk.replace("\\n", "\n")
                firebase_creds = json.dumps(data)
                print("Firebase credentials: private_key un-escaped \\n", flush=True)
        except Exception as norm_err:
            print(f"Firebase credentials: could not normalize: {norm_err}", flush=True)

        with open(cred_path, "w") as f:
            f.write(firebase_creds)
        print(f"Firebase credentials written to {cred_path}", flush=True)
    except Exception as e:
        print(f"Could not write Firebase credentials: {e}", flush=True)

app = FastAPI(title="Content Factory API")

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://content-youtube-generator.vercel.app",
]
_CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "CONTENT_FACTORY_CORS_ORIGINS",
        ",".join(_DEFAULT_CORS_ORIGINS),
    ).split(",")
    if origin.strip()
]
_CORS_ORIGIN_REGEX = os.environ.get(
    "CONTENT_FACTORY_CORS_ORIGIN_REGEX",
    r"https://.*\.vercel\.app",
).strip() or None

# CORS restringido: los endpoints sensibles validan Firebase ID token.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
    allow_credentials=False,
)


def _ensure_firebase_initialized():
    """Inicializa firebase_admin con storageBucket si no está activo. Idempotente."""
    import json
    import firebase_admin
    from firebase_admin import credentials
    try:
        firebase_admin.get_app()
    except ValueError:
        inline_credentials = os.environ.get("FIREBASE_ADMIN_CREDENTIALS", "").strip()
        if inline_credentials:
            cred = credentials.Certificate(json.loads(inline_credentials))
            firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
            return

        credential_candidates = [
            os.environ.get("FIREBASE_ADMIN_CREDENTIALS_PATH", "").strip(),
            "/app/firebase-admin.json",
            str(BASE_DIR / "firebase-admin.json"),
        ]
        cred_path = next((path for path in credential_candidates if path and os.path.exists(path)), "")
        if not cred_path:
            raise RuntimeError("firebase-admin.json no encontrado")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})


_ADMIN_TOKEN = os.environ.get("CONTENT_FACTORY_ADMIN_TOKEN", "").strip()
_ADMIN_UIDS = {
    uid.strip()
    for uid in os.environ.get("CONTENT_FACTORY_ADMIN_UIDS", "").split(",")
    if uid.strip()
}
_DEFAULT_ADMIN_EMAILS = {"admors@gmail.com"}
_ADMIN_EMAILS = _DEFAULT_ADMIN_EMAILS | {
    email.strip().lower()
    for email in os.environ.get("CONTENT_FACTORY_ADMIN_EMAILS", "").split(",")
    if email.strip()
}
_LOCAL_CLIENTS = {"127.0.0.1", "::1", "localhost"}


def _is_local_request(request: Request) -> bool:
    client_host = getattr(getattr(request, "client", None), "host", "") or ""
    return client_host in _LOCAL_CLIENTS


def _require_principal(
    request: Request,
    *,
    allow_admin: bool = False,
    allow_local: bool = False,
) -> dict:
    """Verifica Firebase ID token o, para tareas internas, un admin/local gate."""
    if allow_local and _is_local_request(request):
        return {"admin": True, "uid": "local"}

    admin_token = request.headers.get("x-admin-token", "").strip()
    if allow_admin and _ADMIN_TOKEN and admin_token and admin_token == _ADMIN_TOKEN:
        return {"admin": True, "uid": "admin"}

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication required")

    id_token = auth_header.split(" ", 1)[1].strip()
    if not id_token:
        raise HTTPException(status_code=401, detail="empty auth token")

    try:
        _ensure_firebase_initialized()
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        uid = decoded.get("uid")
        if not uid:
            raise ValueError("missing uid")
        return {"admin": False, "uid": uid, "token": decoded}
    except HTTPException:
        raise
    except Exception as exc:
        try:
            log.warning(
                "firebase_auth_verify_failed",
                error_type=type(exc).__name__,
                error=str(exc)[:300],
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="invalid auth token")


def _require_project_access(
    request: Request,
    project_id: str,
    *,
    allow_admin: bool = False,
    allow_local: bool = False,
) -> dict:
    principal = _require_principal(request, allow_admin=allow_admin, allow_local=allow_local)
    if principal.get("admin"):
        return principal

    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="project not found")
        data = doc.to_dict() or {}
        if data.get("userId") != principal["uid"]:
            raise HTTPException(status_code=403, detail="project access denied")
        return {**principal, "project": data}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="project access check failed")


def _require_admin(request: Request, *, allow_local: bool = False) -> dict:
    principal = _require_principal(request, allow_admin=True, allow_local=allow_local)
    if principal.get("admin"):
        return principal

    token = principal.get("token") or {}
    uid = principal.get("uid")
    email = (token.get("email") or "").strip().lower()
    is_admin_claim = bool(token.get("admin"))
    is_admin_uid = bool(uid and uid in _ADMIN_UIDS)
    is_admin_email = bool(email and email in _ADMIN_EMAILS)
    if is_admin_claim or is_admin_uid or is_admin_email:
        return {**principal, "admin": True}

    raise HTTPException(status_code=403, detail="admin access required")


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _credits_remaining(profile: dict) -> dict:
    credits = profile.get("credits") or {}
    raw_included = max(0, _safe_int(credits.get("included"), 0))
    extra = max(0, _safe_int(credits.get("extra"), 0))
    used = max(0, _safe_int(credits.get("used"), 0))
    plan = str(profile.get("plan") or "free").strip().lower()
    email = str(profile.get("email") or "").strip().lower()
    if plan == "free" and email not in _ADMIN_EMAILS:
        free_cap = max(
            0,
            _safe_int(os.environ.get("CONTENT_FACTORY_FREE_INCLUDED_CREDITS"), 0),
        )
        included = min(raw_included, free_cap)
    else:
        included = raw_included
    total = included + extra
    remaining = max(0, total - used)
    return {
        "included": included,
        "extra": extra,
        "used": used,
        "total": total,
        "remaining": remaining,
    }


def _serialize_firestore_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_firestore_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_firestore_value(v) for v in value]
    return str(value)


def _credit_ledger_payload(
    *,
    uid: str,
    entry_type: str,
    amount: int,
    reason: str,
    actor: str,
    firestore,
    project_id: str | None = None,
    balance_before: dict | None = None,
    balance_after: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    payload = {
        "uid": uid,
        "type": entry_type,
        "amount": amount,
        "reason": reason,
        "actor": actor,
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    if project_id:
        payload["projectId"] = project_id
    if balance_before is not None:
        payload["balanceBefore"] = balance_before
    if balance_after is not None:
        payload["balanceAfter"] = balance_after
    if metadata:
        payload["metadata"] = metadata
    return payload


def _write_credit_ledger(
    db,
    firestore,
    *,
    uid: str,
    entry_type: str,
    amount: int,
    reason: str,
    actor: str,
    project_id: str | None = None,
    balance_before: dict | None = None,
    balance_after: dict | None = None,
    metadata: dict | None = None,
    transaction=None,
) -> str:
    ref = db.collection("creditLedger").document()
    payload = _credit_ledger_payload(
        uid=uid,
        entry_type=entry_type,
        amount=amount,
        reason=reason,
        actor=actor,
        project_id=project_id,
        balance_before=balance_before,
        balance_after=balance_after,
        metadata=metadata,
        firestore=firestore,
    )
    if transaction is not None:
        transaction.set(ref, payload)
    else:
        ref.set(payload)
    return ref.id


def _balance_after_delta(counts: dict, *, used_delta: int = 0, extra_delta: int = 0) -> dict:
    after = dict(counts or {})
    after["used"] = max(0, _safe_int(after.get("used"), 0) + used_delta)
    after["extra"] = max(0, _safe_int(after.get("extra"), 0) + extra_delta)
    total = max(0, _safe_int(after.get("included"), 0)) + after["extra"]
    after["total"] = total
    after["remaining"] = max(0, total - after["used"])
    return after


def _extra_increment_for_grant(counts: dict, amount: int) -> int:
    debt = max(0, _safe_int(counts.get("used"), 0) - _safe_int(counts.get("total"), 0))
    return max(0, amount) + debt


def _get_production_limits() -> dict:
    return {
        "paused": os.environ.get("CONTENT_FACTORY_PRODUCTION_PAUSED", "").strip().lower()
        in {"1", "true", "yes", "on"},
        "max_active": max(0, _safe_int(os.environ.get("CONTENT_FACTORY_MAX_ACTIVE_PRODUCTIONS"), 3)),
        "max_24h": max(0, _safe_int(os.environ.get("CONTENT_FACTORY_MAX_PRODUCTIONS_24H"), 25)),
    }


def _production_capacity_snapshot(db) -> dict:
    limits = _get_production_limits()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    active = 0
    started_24h = 0

    for project in db.collection("projects").stream():
        data = project.to_dict() or {}
        if data.get("status") == "producing":
            active += 1

        started_at = data.get("productionStartedAt")
        if started_at and hasattr(started_at, "timestamp"):
            if datetime.fromtimestamp(started_at.timestamp(), tz=timezone.utc) >= cutoff:
                started_24h += 1

    return {
        **limits,
        "active": active,
        "started_24h": started_24h,
        "active_available": limits["max_active"] <= 0 or active < limits["max_active"],
        "daily_available": limits["max_24h"] <= 0 or started_24h < limits["max_24h"],
    }


def _assert_production_capacity(db):
    capacity = _production_capacity_snapshot(db)
    if capacity["paused"]:
        raise HTTPException(status_code=503, detail="production paused by operator")
    if not capacity["active_available"]:
        raise HTTPException(status_code=429, detail="production capacity reached")
    if not capacity["daily_available"]:
        raise HTTPException(status_code=429, detail="daily production limit reached")
    return capacity


_TIKTOK_AGENT_IDS = {
    "agent_tiktok_documentary",
    "agent_tiktok_podcast",
    "agent_tiktok_autohipnosis",
    "agent_tiktok_meditation",
}
_TIKTOK_FORMAT_BY_AGENT = {
    "agent_tiktok_documentary": "tiktok_documentary",
    "agent_tiktok_podcast": "tiktok_podcast",
    "agent_tiktok_autohipnosis": "tiktok_autohypnosis",
    "agent_tiktok_meditation": "tiktok_meditation",
}
_TIKTOK_DURATION_ALIASES = {
    "60": "60s",
    "60s": "60s",
    "1m": "60s",
    "90": "90s",
    "90s": "90s",
    "3": "3m",
    "3m": "3m",
    "180": "3m",
    "180s": "3m",
    "5": "5m",
    "5m": "5m",
    "300": "5m",
    "300s": "5m",
    "10": "10m",
    "10m": "10m",
    "600": "10m",
    "600s": "10m",
}
_TIKTOK_DURATION_SECONDS = {
    "60s": 60,
    "90s": 90,
    "3m": 180,
    "5m": 300,
    "10m": 600,
}
_TIKTOK_SOURCE_GENRES = {
    "science",
    "mystery",
    "true_crime",
    "history",
    "finance",
    "psychology",
    "business",
    "culture",
}
_WELLNESS_AGENT_IDS = {
    "agent_autohipnosis",
    "agent_meditacion_larga",
    "agent_tiktok_autohipnosis",
    "agent_tiktok_meditation",
}
_PERSONALIZATION_LIMITS = {
    "preferred_name": 40,
    "purpose": 500,
    "anchor_phrase": 180,
}


def _flag_enabled(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _clean_personalization_text(value, *, max_chars: int, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"invalid personalization.{field_name}")
    clean = "".join(ch if (ch >= " " or ch in "\n\t") else " " for ch in value)
    clean = " ".join(clean.split()).strip()
    if len(clean) > max_chars:
        raise HTTPException(status_code=400, detail=f"personalization.{field_name} too long")
    return clean


def _validate_personalization_payload(data: dict, *, agent_id: str) -> dict:
    if agent_id not in _WELLNESS_AGENT_IDS:
        return {}
    raw = data.get("personalization") or data.get("wellnessPersonalization") or {}
    if raw in (None, ""):
        raw = {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="invalid personalization")

    preferred_name = _clean_personalization_text(
        raw.get("preferredName") or raw.get("preferred_name"),
        max_chars=_PERSONALIZATION_LIMITS["preferred_name"],
        field_name="preferredName",
    )
    purpose = _clean_personalization_text(
        raw.get("purpose") or raw.get("personalPurpose") or raw.get("personal_purpose"),
        max_chars=_PERSONALIZATION_LIMITS["purpose"],
        field_name="purpose",
    )
    anchor_phrase = _clean_personalization_text(
        raw.get("anchorPhrase") or raw.get("anchor_phrase"),
        max_chars=_PERSONALIZATION_LIMITS["anchor_phrase"],
        field_name="anchorPhrase",
    )

    payload = {
        "preferred_name": preferred_name,
        "purpose": purpose,
        "anchor_phrase": anchor_phrase,
    }
    if not any(payload.values()):
        return {}
    return {**payload, "enabled": True}


def _clean_radar_context_payload(raw) -> dict:
    if not isinstance(raw, dict):
        return {}

    def _clean(value, limit):
        text = " ".join(str(value or "").split()).strip()
        return text[:limit]

    sources = []
    for source in raw.get("sources") or []:
        if not isinstance(source, dict):
            continue
        url = _clean(source.get("url"), 500)
        title = _clean(source.get("title"), 180)
        domain = _clean(source.get("domain"), 120)
        if url or title or domain:
            sources.append({"title": title, "url": url, "domain": domain})
        if len(sources) >= 5:
            break

    context = {
        "candidateHash": _clean(raw.get("candidateHash") or raw.get("candidate_hash"), 80),
        "intent": _clean(raw.get("intent") or raw.get("radarIntent") or raw.get("radar_intent"), 40),
        "title": _clean(raw.get("title") or raw.get("headline"), 180),
        "angle": _clean(raw.get("angle"), 260),
        "summary": _clean(raw.get("summary"), 900),
        "whyNow": _clean(raw.get("whyNow") or raw.get("why_now"), 520),
        "riskLevel": _clean(raw.get("riskLevel") or raw.get("risk_level"), 20),
        "riskReason": _clean(raw.get("riskReason") or raw.get("risk_reason"), 360),
        "recommendedFormat": _clean(raw.get("recommendedFormat") or raw.get("recommended_format"), 40),
        "sources": sources,
    }
    return {k: v for k, v in context.items() if v not in ("", [], None)}


def _brand_profile_for_project(agent_id: str, data: dict) -> tuple[str, dict]:
    """Return the internal brand profile id and immutable creation snapshot.

    V1 only exposes the locked Esto No Es Amor profile for the podcast lines.
    Other agents can opt into a future profile later without changing legacy
    YouTube/documentary behavior.
    """
    requested = str(data.get("brandProfileId") or data.get("brand_profile_id") or "").strip()
    should_use_default = agent_id in {"agent_podcast_general", "agent_tiktok_podcast"}
    if not requested and not should_use_default:
        return "", {}
    profile_id = requested or DEFAULT_BRAND_PROFILE_ID
    snapshot = brand_profile_snapshot(profile_id)
    return snapshot.get("id") or profile_id, snapshot


def _validate_project_payload(data: dict) -> dict:
    title = (data.get("title") or data.get("topic") or "").strip()
    agent_id = (data.get("agentId") or "").strip()
    agent_file = (data.get("agentFile") or "").strip()

    if not title:
        raise HTTPException(status_code=400, detail="title required")
    if len(title) > 180:
        raise HTTPException(status_code=400, detail="title too long")
    if not agent_id.startswith("agent_"):
        raise HTTPException(status_code=400, detail="invalid agentId")
    if (
        not agent_file.endswith(".md")
        or "/" in agent_file
        or "\\" in agent_file
        or ".." in agent_file
    ):
        raise HTTPException(status_code=400, detail="invalid agentFile")
    prompt_path = Path("prompts") / agent_file
    if not prompt_path.is_file():
        raise HTTPException(status_code=400, detail="agent prompt not found")
    if agent_file[:-3] != agent_id:
        raise HTTPException(status_code=400, detail="agent mismatch")

    requested_platform = (data.get("platform") or "").strip().lower()
    inferred_platform = "tiktok" if agent_id in _TIKTOK_AGENT_IDS else "youtube"
    platform = requested_platform or inferred_platform
    if platform not in {"youtube", "tiktok"}:
        raise HTTPException(status_code=400, detail="invalid platform")
    if platform == "tiktok":
        if not _flag_enabled("CONTENT_FACTORY_TIKTOK_GENERATION_ENABLED", default=True):
            raise HTTPException(status_code=403, detail="tiktok generation disabled")
        if agent_id not in _TIKTOK_AGENT_IDS:
            raise HTTPException(status_code=400, detail="invalid TikTok agent")
    elif agent_id in _TIKTOK_AGENT_IDS:
        raise HTTPException(status_code=400, detail="TikTok agent requires TikTok platform")

    duration_profile = (data.get("durationProfile") or data.get("duration_profile") or "").strip().lower()
    allowed_duration_profiles = {"30m", "60m", "180m"}
    generation_options = {}
    personalization = _validate_personalization_payload(data, agent_id=agent_id)
    if personalization:
        generation_options["personalization"] = personalization
    radar_context = _clean_radar_context_payload(data.get("radarContext") or data.get("radar_context"))
    if radar_context:
        generation_options["radar_context"] = radar_context
    brand_profile_id, brand_profile = _brand_profile_for_project(agent_id, data)
    if brand_profile_id:
        generation_options["brand_profile_id"] = brand_profile_id
        generation_options["brand_profile_snapshot"] = brand_profile
    project_format = _TIKTOK_FORMAT_BY_AGENT.get(agent_id, "")
    tiktok_payload = {}
    if platform == "tiktok":
        duration_key = duration_profile.replace(" ", "") or "90s"
        duration_profile = _TIKTOK_DURATION_ALIASES.get(duration_key, duration_key)
        if duration_profile not in _TIKTOK_DURATION_SECONDS:
            raise HTTPException(status_code=400, detail="invalid TikTok durationProfile")
        source_genre = (
            data.get("sourceGenre")
            or data.get("source_genre")
            or data.get("genre")
            or "psychology"
        )
        source_genre = str(source_genre).strip().lower().replace("-", "_")
        if source_genre not in _TIKTOK_SOURCE_GENRES:
            source_genre = "psychology"
        tiktok_payload = {
            "format": project_format,
            "durationProfile": duration_profile,
            "targetSeconds": _TIKTOK_DURATION_SECONDS[duration_profile],
            "sourceGenre": source_genre,
        }
        generation_options.update({
            "platform": "tiktok",
            "format": project_format,
            "duration_profile": duration_profile,
            "source_genre": source_genre,
            "target_seconds": _TIKTOK_DURATION_SECONDS[duration_profile],
        })
    elif agent_id == "agent_meditacion_larga":
        aliases = {
            "30": "30m",
            "30m": "30m",
            "30min": "30m",
            "60": "60m",
            "60m": "60m",
            "1h": "60m",
            "180": "180m",
            "180m": "180m",
            "3h": "180m",
        }
        duration_profile = aliases.get(duration_profile.replace(" ", ""), duration_profile or "60m")
        if duration_profile not in allowed_duration_profiles:
            raise HTTPException(status_code=400, detail="invalid durationProfile")
        generation_options["duration_profile"] = duration_profile

    return {
        "title": title,
        "agent_id": agent_id,
        "agent_file": agent_file,
        "platform": platform,
        "format": project_format,
        "tiktok": tiktok_payload,
        "personalization": personalization,
        "brand_profile_id": brand_profile_id,
        "brand_profile_snapshot": brand_profile,
        "generation_options": generation_options,
    }


def _upload_video_to_storage(local_path: Path, project_id: str, content_type: str = None) -> dict | None:
    """
    Sube un archivo a Firebase Storage en 'videos/{project_id}/{filename}'.

    content_type se infiere de la extensión si no se pasa explícito:
      .mp4 → video/mp4, .jpg/.jpeg → image/jpeg, .png → image/png

    Retorna {"gs_path": "gs://bucket/videos/...", "signed_url": "https://..."}
    o None si falla. La signed URL dura 7 días (máximo permitido por v4 signing).
    """
    try:
        _ensure_firebase_initialized()
        from firebase_admin import storage
        # Pasar bucket name explícito: si firebase_admin fue inicializado en otra
        # parte del código sin storageBucket, storage.bucket() sin argumento falla
        bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
        blob_name = f"videos/{project_id}/{local_path.name}"
        blob = bucket.blob(blob_name)
        size_mb = local_path.stat().st_size / (1024 * 1024)
        if content_type is None:
            ext = local_path.suffix.lower()
            content_type = {
                ".mp4": "video/mp4", ".webm": "video/webm",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp",
            }.get(ext, "application/octet-stream")
        print(f"   ☁️ Subiendo a Storage: {blob_name} ({size_mb:.1f} MB, {content_type})")
        blob.upload_from_filename(str(local_path), content_type=content_type)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),
            method="GET",
        )
        print(f"   ✅ Storage upload OK ({size_mb:.1f} MB)")
        return {
            "gs_path": f"gs://{bucket.name}/{blob_name}",
            "signed_url": signed_url,
        }
    except Exception as e:
        print(f"   ❌ Storage upload failed: {e}")
        return None


def _run_factory_subprocess(args, monitor_thread, stop_event, timeout=7200, log_label="factory"):
    """
    Ejecuta factory.py como subprocess en su propio process group, garantizando:

    1. Si el padre (worker) muere o es interrumpido (SoftTimeLimit, SIGTERM), el
       SUBPROCESS y todos sus hijos (ffmpeg, python helpers) se matan en cascada
       via os.killpg sobre el process group. Sin esto, ffmpeg quedaría huérfano
       generando Ken Burns durante 30+ min después del timeout.

    2. El thread monitor (que escribe `update_progress` a Firestore en bucle)
       SIEMPRE se detiene al final, incluso ante excepción. Antes vivía en una
       sucesión `subprocess.run() ; stop_event.set()` donde la excepción
       impedía llegar al stop, dejando un thread zombie escribiendo a Firestore
       indefinidamente y rompiendo la UX (proyecto regresaba de "completed" a
       "producing 85%").

    Retorna (returncode, stderr_tail). Loguea timeout y kills explícitamente.
    """
    import subprocess
    import signal
    proc = None
    try:
        # start_new_session=True crea un nuevo process group con PID == proc.pid.
        # Hace que `os.killpg(proc.pid, SIGTERM)` mate al subprocess Y a todos
        # sus descendientes (ffmpeg, python -c, etc.) — no solo al subprocess.
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return (proc.returncode, (stderr or "")[-500:])
        except subprocess.TimeoutExpired:
            print(f"   ⏱️ [{log_label}] Subprocess excedió timeout={timeout}s. Matando process group {proc.pid}...")
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                stdout, stderr = proc.communicate(timeout=10)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
                stdout, stderr = ("", "killed by timeout")
            return (-1, f"TIMEOUT_{timeout}s: {(stderr or '')[-400:]}")
    finally:
        # Detener thread monitor SIEMPRE — pase lo que pase con el subprocess.
        # Si la excepción es SoftTimeLimitExceeded de Celery, también pasamos
        # por aquí porque Python ejecuta finally antes de re-raise.
        try:
            if stop_event is not None:
                stop_event.set()
            if monitor_thread is not None and monitor_thread.is_alive():
                monitor_thread.join(timeout=10)
        except Exception:
            pass
        # Y matar el process group por seguridad si el subprocess sigue vivo
        # (ej. si llegamos al finally por una excepción del padre, no por
        # timeout del subprocess).
        if proc is not None and proc.poll() is None:
            try:
                print(f"   🔪 [{log_label}] Padre interrumpido, matando subprocess huérfano (pid={proc.pid})")
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass


def _scene_number_from_payload(scene: dict) -> int:
    try:
        return int(scene.get("scene_number", scene.get("sceneNumber", 0)))
    except Exception:
        return 0


def _valid_scene_image_numbers(images_dir: Path, min_bytes: int = 5000) -> set[int]:
    ready = set()
    for img in images_dir.glob("scene_*.png"):
        match = re.fullmatch(r"scene_(\d{4})\.png", img.name)
        if match and img.stat().st_size >= min_bytes:
            ready.add(int(match.group(1)))
    return ready


def _legacy_title_slug(title: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(title or "video_sin_titulo").replace(" ", "_"))
    return slug.strip("_-") or "video_sin_titulo"


def _project_output_slug(title: str, project_id: str | None = None) -> str:
    """
    Disk output identity.

    Legacy projects used title-only folders. New productions include project_id
    so two videos with the same title cannot silently reuse the same images,
    audio, motion files, or final video.
    """
    title_slug = _legacy_title_slug(title)
    if not project_id:
        return title_slug

    project_slug = _legacy_title_slug(project_id)
    compact_title = title_slug[:90].rstrip("_-") or "video_sin_titulo"
    return f"{compact_title}__{project_slug}"


def _candidate_video_folders(title: str, project_id: str, stored_folder: str | None = None) -> list[str]:
    candidates = []
    for folder in (
        stored_folder,
        _project_output_slug(title, project_id),
        _legacy_title_slug(title),
    ):
        if folder and folder not in candidates:
            candidates.append(folder)
    return candidates


def _sync_scene_image_urls(doc_ref, scenes: list, safe_title: str, images_dir: Path) -> dict:
    """
    Final source-of-truth sync after visual generation.

    The live monitor can miss a late file if the subprocess exits between
    polling ticks. This pass reconciles disk -> Firestore by exact scene number
    before the pipeline is allowed to move into voice/montage.
    """
    from firebase_admin import firestore

    vps_base = os.environ.get("VPS_PUBLIC_URL", "http://100.99.207.113:8085").rstrip("/")
    ready_numbers = _valid_scene_image_numbers(images_dir)

    latest = doc_ref.get().to_dict() or {}
    updated_scenes = latest.get("scenes") or scenes or []
    expected_numbers = []
    missing = []
    ready = 0

    for scene in updated_scenes:
        num = _scene_number_from_payload(scene)
        if not num:
            continue
        expected_numbers.append(num)
        if num in ready_numbers:
            scene["imageUrl"] = f"{vps_base}/images/{safe_title}/scene_{num:04d}.png"
            scene["status"] = "ready"
            ready += 1
        else:
            scene.pop("imageUrl", None)
            scene["status"] = "missing_image"
            missing.append(num)

    doc_ref.update({
        "scenes": updated_scenes,
        "visuals.ready": ready,
        "visuals.total": len(expected_numbers),
        "visuals.missing": missing,
        "visuals.updatedAt": firestore.SERVER_TIMESTAMP,
    })

    return {
        "ready": ready,
        "total": len(expected_numbers),
        "missing": missing,
    }


# ── Idempotency lock para /produce y /retry ──────────────────────────────
# Compare-and-swap atómico via Firestore transaction. Bloquea encolado
# duplicado de jobs costosos para el mismo project_id (doble click rápido,
# race UI, retry browser). El lock expira tras LOCK_MAX_AGE_SEC para no
# bloquear retries legítimos cuando un job realmente murió sin limpiar.
PRODUCTION_LOCK_MAX_AGE_SEC = int(os.environ.get("PRODUCTION_LOCK_MAX_AGE_SEC", "14400"))  # 4 horas


def _try_acquire_production_lock(project_id: str) -> dict:
    """
    Intenta adquirir lock de producción para el project_id usando Firestore
    transaction (atómico, sin race entre múltiples workers/requests).

    Returns:
      - {"acquired": True, "lock_id": "<uuid>"} si el lock se adquirió.
      - {"acquired": False, "existing_lock_id": "<uuid>", "age_sec": N}
        si ya hay un lock vigente (otro job ya está corriendo).
      - {"acquired": False, "error": str} si Firestore falló.
    """
    import uuid
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)

        new_lock_id = str(uuid.uuid4())

        @firestore.transactional
        def _txn(transaction):
            snap = doc_ref.get(transaction=transaction)
            data = snap.to_dict() or {}

            existing_lock = data.get("productionLockId")
            locked_at = data.get("productionLockedAt")

            # Si hay lock vigente, NO reencolar
            if existing_lock and locked_at and hasattr(locked_at, "timestamp"):
                age = datetime.now(timezone.utc).timestamp() - locked_at.timestamp()
                if age < PRODUCTION_LOCK_MAX_AGE_SEC:
                    return {
                        "acquired": False,
                        "existing_lock_id": existing_lock,
                        "age_sec": int(age),
                    }
                # Lock expirado: alguien lo dejó colgando, lo robamos
                print(f"[LOCK] Stale lock {existing_lock[:8]}... ({int(age)}s), reclaiming for {project_id}")

            transaction.update(doc_ref, {
                "productionLockId": new_lock_id,
                "productionLockedAt": firestore.SERVER_TIMESTAMP,
            })
            return {"acquired": True, "lock_id": new_lock_id}

        return _txn(db.transaction())
    except Exception as e:
        print(f"[LOCK] Acquire failed for {project_id}: {e}")
        return {"acquired": False, "error": str(e)[:200]}


def _release_production_lock(project_id: str, lock_id: str | None = None):
    """
    Libera el lock al terminar producción (éxito, error, timeout). Si
    lock_id se provee, solo borra si coincide (evita borrar el lock de
    OTRO job que ya tomó el slot). Si no, borra incondicional.
    """
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)

        if lock_id is None:
            doc_ref.update({
                "productionLockId": firestore.DELETE_FIELD,
                "productionLockedAt": firestore.DELETE_FIELD,
            })
            return

        @firestore.transactional
        def _txn(transaction):
            snap = doc_ref.get(transaction=transaction)
            data = snap.to_dict() or {}
            current = data.get("productionLockId")
            if current == lock_id:
                transaction.update(doc_ref, {
                    "productionLockId": firestore.DELETE_FIELD,
                    "productionLockedAt": firestore.DELETE_FIELD,
                })

        _txn(db.transaction())
    except Exception as e:
        print(f"[LOCK] Release failed for {project_id}: {e}")  # no fatal


# ── Moderación de contenido ───────────────────────────────────────────────
# Umbrales tuneados para canales tipo true-crime / horror / documental:
# violence/graphic alto (>0.85) es esperado en estos contenidos, no se bloquea
# salvo extremo. Sexual/minors, self-harm/instructions y hate/threatening son
# CRITICOS — cero tolerancia, demonetizacion + posible ban en YouTube.
MODERATION_THRESHOLDS_CRITICAL = {
    "sexual/minors": 0.05,
    "self-harm/instructions": 0.10,
    "hate/threatening": 0.30,
}
MODERATION_THRESHOLDS_WARN = {
    "violence": 0.92,
    "violence/graphic": 0.85,
    "harassment": 0.70,
    "sexual": 0.50,
    "self-harm": 0.60,
    "hate": 0.50,
    "harassment/threatening": 0.50,
    "self-harm/intent": 0.50,
}


def check_content_moderation(text: str) -> dict:
    """
    Pasa el texto por OpenAI Moderation API (gratis, sin consumo de creditos
    de generacion) y categoriza en 3 niveles:

      - critical_blocks: violaciones graves que requieren override explicito
      - warnings: contenido sensible esperado para el nicho, mostrar advertencia
      - safe: todo dentro de umbrales

    Retorna dict con shape:
      {
        "ran_at": iso8601,
        "model": "...",
        "flagged_by_openai": bool,
        "scores": {category: score},
        "critical_blocks": [{"category": str, "score": float, "threshold": float}],
        "warnings": [{"category": str, "score": float, "threshold": float}],
        "verdict": "block" | "warn" | "ok",
        "error": str | None,
      }
    """
    result = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "model": None,
        "flagged_by_openai": False,
        "scores": {},
        "critical_blocks": [],
        "warnings": [],
        "verdict": "ok",
        "error": None,
    }
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        # Cap input a 32k chars (Moderation API max ~32k tokens, sobra)
        snippet = (text or "")[:32000]
        if not snippet.strip():
            result["error"] = "empty text"
            return result

        resp = client.moderations.create(model="omni-moderation-latest", input=snippet)
        result["model"] = resp.model
        if not resp.results:
            result["error"] = "no results"
            return result

        r0 = resp.results[0]
        result["flagged_by_openai"] = bool(r0.flagged)
        # category_scores es un BaseModel pydantic; .model_dump() lo da como dict
        try:
            result["scores"] = r0.category_scores.model_dump()
        except Exception:
            result["scores"] = dict(r0.category_scores) if hasattr(r0.category_scores, "__iter__") else {}

        for cat, threshold in MODERATION_THRESHOLDS_CRITICAL.items():
            score = result["scores"].get(cat, 0.0) or 0.0
            if score >= threshold:
                result["critical_blocks"].append({
                    "category": cat, "score": round(score, 4), "threshold": threshold,
                })
        for cat, threshold in MODERATION_THRESHOLDS_WARN.items():
            score = result["scores"].get(cat, 0.0) or 0.0
            if score >= threshold:
                result["warnings"].append({
                    "category": cat, "score": round(score, 4), "threshold": threshold,
                })

        if result["critical_blocks"]:
            result["verdict"] = "block"
        elif result["warnings"]:
            result["verdict"] = "warn"
        else:
            result["verdict"] = "ok"

        return result
    except Exception as e:
        result["error"] = str(e)[:200]
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
        return result


# ── Fact-checking del guion ─────────────────────────────────────────────────
def fact_check_script(text: str, topic_hint: str = "") -> dict:
    """
    Verifica claims factuales del guion en 3 pasadas:
      1. Claude extrae los 10 claims mas verificables (numeros, fechas, nombres)
      2. Tavily busca evidencia para cada uno
      3. Claude evalua cada claim contra evidencia → confidence alta/media/baja

    Retorna:
      {
        "ran_at": iso8601,
        "claims": [
          {"claim": str, "confidence": "alta"|"media"|"baja",
           "evidence": str, "source_url": str, "verdict": str}
        ],
        "summary": {"total": int, "high": int, "medium": int, "low": int},
        "error": str | None,
      }
    """
    out = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "claims": [],
        "summary": {"total": 0, "high": 0, "medium": 0, "low": 0},
        "error": None,
    }
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        snippet = (text or "")[:30000]
        if not snippet.strip():
            out["error"] = "empty text"
            return out

        # Pasada 1: extraccion de claims
        extract_prompt = (
            "Eres un fact-checker riguroso. Lee el siguiente guion documental y "
            "extrae HASTA 10 claims factuales especificos y verificables (cifras, "
            "fechas, cantidades, nombres asociados a eventos especificos).\n\n"
            "Ignora opiniones, descripciones generales, o frases narrativas vagas.\n"
            "Prefiere claims donde una fuente publica podria confirmar o refutar.\n\n"
            f"Tema del video: {topic_hint or '(no especificado)'}\n\n"
            f"GUION:\n{snippet}\n\n"
            "Responde EXCLUSIVAMENTE con JSON array (sin markdown, sin texto extra):\n"
            "[\"claim 1 corto y especifico\", \"claim 2\", ...]\n"
            "Cada claim maximo 25 palabras."
        )
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": extract_prompt}],
        )
        raw = r.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        claims_list = json.loads(raw)
        if not isinstance(claims_list, list):
            raise ValueError("claims response not a list")
        claims_list = [c for c in claims_list if isinstance(c, str) and c.strip()][:10]

        # Pasada 2: Tavily search por cada claim
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        except Exception as tav_init_err:
            out["error"] = f"Tavily init failed: {tav_init_err}"
            out["claims"] = [{"claim": c, "confidence": "media", "evidence": "(no se pudo verificar)", "source_url": "", "verdict": "sin verificar"} for c in claims_list]
            return out

        evidence_pack = []
        for claim in claims_list:
            try:
                tav_res = tavily.search(query=claim, search_depth="basic", max_results=2, include_answer=True)
                ans = (tav_res.get("answer") or "")[:400]
                top = tav_res.get("results", [{}])[0] if tav_res.get("results") else {}
                evidence_pack.append({
                    "claim": claim,
                    "answer": ans,
                    "top_url": top.get("url", ""),
                    "top_snippet": (top.get("content") or "")[:300],
                })
            except Exception as tav_err:
                evidence_pack.append({"claim": claim, "answer": "", "top_url": "", "top_snippet": f"(error: {tav_err})"})

        # Pasada 3: evaluacion de claims con la evidencia
        eval_prompt = (
            "Eres un fact-checker. Para cada claim, decide su confidence basado en "
            "la evidencia provista (Tavily search). Responde EXCLUSIVAMENTE con un "
            "JSON array con esta estructura exacta:\n"
            "[{\"claim\": \"...\", \"confidence\": \"alta|media|baja\", \"verdict\": \"frase corta explicando\", \"source_url\": \"...\"}]\n\n"
            "Reglas:\n"
            "- 'alta': evidencia clara y especifica respalda el claim\n"
            "- 'media': evidencia parcial o aproximada\n"
            "- 'baja': sin evidencia, contradicho, o numero/fecha imposible de verificar\n"
            "- verdict: maximo 20 palabras\n"
            "- source_url: la URL de top_url de la evidencia (cadena vacia si no hay)\n\n"
            f"EVIDENCIA:\n{json.dumps(evidence_pack, ensure_ascii=False)}\n"
        )
        r2 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": eval_prompt}],
        )
        raw2 = r2.content[0].text.strip()
        if raw2.startswith("```"):
            raw2 = raw2.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        evaluated = json.loads(raw2)
        if not isinstance(evaluated, list):
            raise ValueError("eval response not a list")

        # Enriquecer con evidence summary
        evidence_by_claim = {e["claim"]: e for e in evidence_pack}
        for item in evaluated:
            ev = evidence_by_claim.get(item.get("claim", ""), {})
            item["evidence"] = (ev.get("answer") or ev.get("top_snippet") or "")[:300]

        out["claims"] = evaluated
        for item in evaluated:
            conf = (item.get("confidence") or "").lower()
            if conf == "alta":
                out["summary"]["high"] += 1
            elif conf == "media":
                out["summary"]["medium"] += 1
            else:
                out["summary"]["low"] += 1
        out["summary"]["total"] = len(evaluated)
        return out
    except Exception as e:
        out["error"] = str(e)[:200]
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
        return out


# ── Shorts pipeline (vertical 9:16 derivados del long-form) ────────────────
def _video_duration_seconds(video_path: Path) -> float:
    """Devuelve duración del video con ffprobe. 0 si falla."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, timeout=20,
        )
        return float(out.stdout.strip() or 0)
    except Exception:
        return 0.0


def _is_valid_media_file(path: Path, min_duration_seconds: float = 1.0) -> tuple[bool, float, str]:
    """Valida un media file con ffprobe y retorna (ok, duration, error)."""
    return _validate_media_file(path, min_duration_seconds=min_duration_seconds)


def _pick_valid_final_video(
    video_dir: Path,
    prefer_subtitles: bool = True,
    min_duration_seconds: float = 30.0,
) -> tuple[Path | None, bool, list[dict]]:
    """
    Elige el FINAL_*.mp4 mas reciente y reproducible.

    El bug del podcast corrupto nacio de tomar `glob()[0]`: un archivo MP4 puede
    tener bytes y aun asi no tener moov atom. Esta funcion fuerza ffprobe antes
    de que descarga, shorts o upload usen el archivo.
    """
    return _pick_valid_final_video_impl(
        video_dir,
        prefer_subtitles=prefer_subtitles,
        min_duration_seconds=min_duration_seconds,
    )


def _completed_project_has_valid_delivery(project: dict, min_duration_seconds: float = 30.0) -> bool:
    """
    Idempotency guard para retries: solo saltamos un job si el proyecto ya tiene
    URL de entrega y una duracion final plausible. Un `completed` con 0:00 no
    debe bloquear una reparacion futura.
    """
    if project.get("status") != "completed" or not project.get("videoUrl"):
        return False
    return _safe_float(project.get("videoDurationSeconds"), 0.0) >= min_duration_seconds


def _remux_recovered_final(video_dir: Path, safe_title: str) -> tuple[Path | None, dict]:
    """
    Repara un proyecto que tiene master_visual/master_audio validos pero FINAL corrupto.
    No llama APIs externas: solo FFmpeg local dentro del contenedor.
    """
    master_visual = video_dir / "master_visual.mp4"
    master_audio = video_dir / "master_audio.mp3"
    info = {"used": False, "reason": "", "video_duration": 0.0, "audio_duration": 0.0}

    video_ok, video_dur, video_err = _is_valid_media_file(master_visual, min_duration_seconds=5)
    audio_ok, audio_dur, audio_err = _is_valid_media_file(master_audio, min_duration_seconds=5)
    info.update({
        "video_duration": round(video_dur, 3),
        "audio_duration": round(audio_dur, 3),
    })
    if not video_ok or not audio_ok:
        info["reason"] = f"invalid masters: video={video_err or video_dur}, audio={audio_err or audio_dur}"
        return None, info

    output = video_dir / f"FINAL_RECOVERED_{safe_title}.mp4"
    audio_deficit = audio_dur - video_dur
    needs_pad = audio_deficit > 0.05

    if needs_pad:
        pad_seconds = audio_deficit + 0.5
        cmd = [
            "ffmpeg", "-y",
            "-i", str(master_visual),
            "-i", str(master_audio),
            "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={pad_seconds:.3f}[v]",
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(output),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(master_visual),
            "-i", str(master_audio),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(output),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        info["reason"] = f"ffmpeg remux failed: {(result.stderr or '')[-300:]}"
        return None, info

    final_ok, final_dur, final_err = _is_valid_media_file(output, min_duration_seconds=30)
    if not final_ok:
        info["reason"] = f"recovered final invalid: {final_err or final_dur}"
        return None, info

    info.update({
        "used": True,
        "final_duration": round(final_dur, 3),
        "final_size_mb": round(output.stat().st_size / (1024 * 1024), 1),
    })
    return output, info


def _render_short_vertical(input_video: Path, start_sec: float, end_sec: float, output_path: Path) -> bool:
    """
    Re-renderiza un segmento del video horizontal 16:9 a vertical 9:16
    con fondo blureado del mismo frame (estilo Shorts/TikTok).

    Filter graph:
      - bg: scale a 1080x1920 force-fit + crop + blur (queda como fondo)
      - fg: scale a 1080xN manteniendo aspect (queda centrado encima)
      - overlay: composita fg sobre bg
    """
    duration = max(1, end_sec - start_sec)
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=30:3[bg];"
        "[0:v]scale=1080:-1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-t", str(duration),
        "-i", str(input_video),
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return True
        print(f"   ❌ ffmpeg short render failed (rc={result.returncode}): {result.stderr[-300:]}")
        return False
    except subprocess.TimeoutExpired:
        print(f"   ❌ ffmpeg short render timeout after 5 min")
        return False
    except Exception as e:
        print(f"   ❌ ffmpeg short render exception: {e}")
        return False


def build_shorts_for_project(video_dir: Path, project_id: str) -> list:
    """
    Genera hasta 3 shorts vertical 9:16 a timestamps estratégicos del video final.
    Sube cada uno a Firebase Storage en videos/{project_id}/shorts/.

    Estrategia v1 (MVP): timestamps fijos según duración del video:
      1. HOOK: primeros 60s (capturas la apertura más impactante del guion)
      2. MID:  60s alrededor del 50% (sección densa)
      3. END:  60s antes del cierre (clímax narrativo)

    Mejora futura (Sprint 2.1.5): NLP scoring de intensidad emocional
    sobre el transcript para elegir momentos más virales.

    Retorna lista de dicts: [{"index": 1, "start": 0, "end": 60,
                              "gs_path": "...", "signed_url": "..."}]
    """
    src, _has_subs, invalid_candidates = _pick_valid_final_video(video_dir)
    if not src:
        print(f"   ⚠️ No se encontró FINAL video en {video_dir} para generar shorts")
        if invalid_candidates:
            print(f"   ⚠️ FINAL inválidos: {invalid_candidates[:3]}")
        return []

    duration = _video_duration_seconds(src)
    if duration < 90:
        print(f"   ⚠️ Video {duration:.0f}s muy corto para 3 shorts; salteando")
        return []

    # Timestamps de los 3 shorts. Cada uno entre 45-60s.
    short_len = 55
    plans = [
        ("hook", 0, min(short_len, 60)),
        ("mid", max(0, duration * 0.5 - short_len / 2), min(duration, duration * 0.5 + short_len / 2)),
        ("end", max(0, duration - short_len - 10), max(short_len, duration - 10)),
    ]

    shorts_dir = video_dir / "shorts"
    shorts_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, (label, start, end) in enumerate(plans, 1):
        if end - start < 30:
            continue
        out_path = shorts_dir / f"SHORT_{i:02d}_{label}.mp4"
        print(f"   ✂️ Renderizando short {i}/3 ({label}, {start:.0f}-{end:.0f}s)")
        if not _render_short_vertical(src, start, end, out_path):
            continue
        # Upload a Storage
        upload = _upload_video_to_storage(out_path, f"{project_id}/shorts")
        if upload:
            results.append({
                "index": i,
                "label": label,
                "start": round(start, 1),
                "end": round(end, 1),
                "duration": round(end - start, 1),
                "size_mb": round(out_path.stat().st_size / 1024 / 1024, 1),
                "gs_path": upload["gs_path"],
                "signed_url": upload["signed_url"],
            })
            print(f"   ✅ Short {i} subido ({results[-1]['size_mb']} MB)")
    return results


# ── Thumbnails (3 variantes por video) ─────────────────────────────────────
# Ruta principal: GPT Image genera un fondo premium sin texto; el backend
# compone el titulo exacto encima para evitar letras inventadas.
# Rollback: CONTENT_FACTORY_THUMBNAIL_EXACT_TITLE_OVERLAY=false vuelve al
# comportamiento anterior de texto integrado por el modelo.
# Mas adelante (Phase 3.2 multi-channel) se podra parametrizar por canal.
THUMBNAIL_DEFAULT_THEME = {
    "font_path_primary": "/usr/share/fonts/truetype/montserrat/Montserrat-Black.ttf",
    "font_path_fallback": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "text_color": (255, 255, 255),       # blanco
    "stroke_color": (0, 0, 0),            # negro
    "accent_color": (220, 38, 38),        # rojo intenso (DC2626)
    "stroke_width": 8,
    "gradient_alpha_top": 0,              # transparente arriba
    "gradient_alpha_bottom": 200,         # casi opaco abajo (texto legible)
}


def _pick_thumbnail_keywords(title: str, max_words: int = 4) -> str:
    """
    Extrae las palabras clave del título para overlay del thumbnail.
    Quita stopwords cortas y prioriza sustantivos/nombres con mayúsculas.
    Ej: "El caso del Zodiac Killer" → "Zodiac Killer"
        "Las torturas de la Santa Inquisición" → "Torturas Inquisición"
    """
    if not title:
        return ""
    stopwords = {"el", "la", "los", "las", "un", "una", "de", "del", "y", "o",
                 "que", "en", "con", "por", "para", "sin", "se", "al", "su",
                 "es", "lo", "le", "the", "and", "of", "in", "on"}
    words = [w for w in title.split() if w.lower() not in stopwords and len(w) >= 3]
    return " ".join(words[:max_words]).upper() if words else title.upper()[:50]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _premium_thumbnails_enabled() -> bool:
    return _env_bool("CONTENT_FACTORY_PREMIUM_THUMBNAILS", True)


def _thumbnail_exact_title_overlay_enabled() -> bool:
    return _env_bool("CONTENT_FACTORY_THUMBNAIL_EXACT_TITLE_OVERLAY", True)


def _thumbnail_model() -> str:
    model = os.environ.get("CONTENT_FACTORY_PREMIUM_THUMBNAIL_MODEL", "gpt-image-1.5").strip() or "gpt-image-1.5"
    normalized = model.lower()
    if normalized in {"gpt-image-2", "image-2"} or normalized.startswith("sora-"):
        print(f"   ⚠️ Modelo de thumbnail '{model}' no es un generador de imagen fija soportado; usando gpt-image-1.5")
        return "gpt-image-1.5"
    return model


def _thumbnail_quality() -> str:
    return os.environ.get("CONTENT_FACTORY_PREMIUM_THUMBNAIL_QUALITY", "high").strip() or "high"


def _thumbnail_generation_size(model: str) -> str:
    # GPT Image models expose landscape generation as 1536x1024. We center-crop
    # to 1280x720 after generation, so prompts reserve a central 16:9 safe area.
    if model.startswith("gpt-image") or model == "chatgpt-image-latest":
        return "1536x1024"
    if model.startswith("dall-e-3"):
        return "1792x1024"
    return "auto"


def _thumbnail_font_paths() -> list[str]:
    return [
        "/usr/share/fonts/truetype/montserrat/Montserrat-Black.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/impact.ttf",
    ]


def _thumbnail_safe_filename(value: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower()).strip("_")
    return slug[:48] or "thumbnail"


def _thumbnail_hook_lines(hook: str) -> list[str]:
    lines = [line.strip().upper() for line in (hook or "").splitlines() if line.strip()]
    return lines[:3] or ["MIRA ESTO"]


def _thumbnail_format_badge(agent_id: str | None = None) -> str | None:
    if agent_id in {"agent_autohipnosis", "agent_meditacion_larga"}:
        return "MEDITACIÓN GUIADA"
    if agent_id == "agent_podcast_general":
        return "PODCAST"
    return None


def _title_has_any(lower_title: str, terms: list[str]) -> bool:
    return any(term in lower_title for term in terms)


def _wellness_thumbnail_hook_plans(clean_title: str, agent_id: str | None = None) -> list[dict]:
    lower = clean_title.lower()
    is_long = agent_id == "agent_meditacion_larga"
    is_sleep = _title_has_any(lower, ["dormir", "duerme", "sueño", "sueno", "noche", "descanso", "descansar"])
    is_confidence = _title_has_any(lower, ["confianza", "autoconfianza", "seguridad", "autoestima"])
    is_anxiety = _title_has_any(lower, ["ansiedad", "estres", "estrés", "preocupacion", "preocupación", "calma"])
    is_abundance = _title_has_any(lower, ["abundancia", "dinero", "prosperidad", "riqueza"])
    is_discipline = _title_has_any(lower, ["disciplina", "enfoque", "habito", "hábito", "constancia"])

    session_context = (
        f"long-form sleep meditation poster for {clean_title}"
        if is_long
        else f"guided self-hypnosis poster for {clean_title}"
    )

    if is_sleep and is_confidence:
        hooks = [
            ("early", "confianza_sueno", "CONFÍA\nEN TI", "restful close portrait with eyes closed, safe nighttime glow, visual metaphor of inner confidence becoming calm before sleep"),
            ("mid", "descanso_seguro", "DUERME\nSEGURO", "peaceful bedroom and moonlight, soft protective aura, deep rest without fear or tension"),
            ("closing", "mente_en_calma", "CALMA\nTU MENTE", "serene night sky with warm gold particles, quiet transformation and self-trust while resting"),
        ]
    elif is_sleep:
        hooks = [
            ("early", "sueno_profundo", "DUERME\nPROFUNDO", "premium night bedroom or moonlit landscape, heavy peaceful rest, warm lamp glow and soft blue shadows"),
            ("mid", "apaga_mente", "APAGA\nTU MENTE", "calm silhouette under stars, thought patterns dissolving into soft golden light, sleep-ready atmosphere"),
            ("closing", "descanso_total", "DESCANSA\nAHORA", "minimal serene bed or lake scene, gentle breathing light, emotional relief and stillness"),
        ]
    elif is_confidence:
        hooks = [
            ("early", "confia_en_ti", "CONFÍA\nEN TI", "cinematic peaceful portrait from shoulders up, relaxed confidence, warm sunrise aura and premium personal growth energy"),
            ("mid", "seguridad_interior", "SEGURIDAD\nINTERIOR", "symbolic inner light expanding from the chest area without medical imagery, elegant violet and gold atmosphere"),
            ("closing", "vuelve_a_ti", "VUELVE\nA TI", "quiet mirror or dawn landscape, self-acceptance and grounded identity transformation"),
        ]
    elif is_anxiety:
        hooks = [
            ("early", "suelta_tension", "SUELTA\nTENSIÓN", "calm person breathing with eyes closed, stress represented as fading mist, safe and non-clinical wellness mood"),
            ("mid", "calma_profunda", "CALMA\nPROFUNDA", "soft blue night ambience, nervous energy transforming into slow gold particles, peaceful breathing rhythm"),
            ("closing", "respira_descansa", "RESPIRA\nY DESCANSA", "minimal meditation space, warm lamp, quiet body relaxation and relief"),
        ]
    elif is_abundance:
        hooks = [
            ("early", "mente_abierta", "MENTE\nABIERTA", "premium symbolic abundance visual with warm sunrise, clean path of light, calm opportunity and grounded clarity"),
            ("mid", "abundancia_serena", "ABUNDANCIA\nSERENA", "elegant golden particles flowing through a peaceful landscape, no money pile, no luxury flex, grounded prosperity"),
            ("closing", "recibe_con_calma", "RECIBE\nCON CALMA", "quiet open doorway with warm light, emotional openness and mature self-worth"),
        ]
    elif is_discipline:
        hooks = [
            ("early", "disciplina_serena", "DISCIPLINA\nSERENA", "calm focus visual, dawn desk or quiet path, disciplined identity without harsh motivation"),
            ("mid", "enfoque_profundo", "ENFOQUE\nPROFUNDO", "minimal dark-blue concentration field with warm light center, steady attention and inner order"),
            ("closing", "un_paso_mas", "UN PASO\nMÁS", "cinematic path at sunrise, grounded progress and calm determination"),
        ]
    else:
        hooks = [
            ("early", "calma_profunda", "CALMA\nPROFUNDA", "premium calm meditation poster, soft violet and gold light, safe inner transformation"),
            ("mid", "respira_suelta", "RESPIRA\nY SUELTA", "slow breathing visual field, gentle particles and peaceful body relaxation"),
            ("closing", "vuelve_a_ti", "VUELVE\nA TI", "quiet dawn landscape, grounded self-connection and emotional clarity"),
        ]

    return [
        {
            "label": label,
            "variant": variant,
            "hook": hook,
            "concept": f"{session_context}: {concept}",
        }
        for label, variant, hook, concept in hooks
    ]


def _is_esto_no_es_amor_topic(clean_title: str) -> bool:
    lower = (clean_title or "").lower()
    return any(
        token in lower
        for token in [
            "esto no es amor",
            "apego",
            "dependencia",
            "obsesion",
            "obsesión",
            "contacto cero",
            "ruptura",
            "dejar ir",
            "amor propio",
            "autoestima",
            "herida",
            "abandono",
            "relacion toxica",
            "relación tóxica",
            "no soy suficiente",
        ]
    )


def _esto_no_es_amor_thumbnail_hook_plans(clean_title: str) -> list[dict]:
    return [
        {
            "label": "early",
            "variant": "apego",
            "hook": "NO ES AMOR\nES APEGO",
            "concept": (
                "object-led emotional relationship thumbnail: phone face down with a blank black screen, "
                "a wilted flower, and two coffee cups separated by empty space on a dark bedside table; "
                "warm amber light on one side and restrained teal shadow on the other"
            ),
            "avoid_people": True,
        },
        {
            "label": "mid",
            "variant": "patron",
            "hook": "DEJA DE\nPERSEGUIR",
            "concept": (
                "empty room relationship metaphor: two chairs facing different directions, a loose red thread "
                "resting between them, one warm lamp, clean negative space, intimate cinematic tension"
            ),
            "avoid_people": True,
        },
        {
            "label": "closing",
            "variant": "paz",
            "hook": "ELIGE\nTU PAZ",
            "concept": (
                "quiet recovery still life: closed journal, single key, cup of tea near a morning window, "
                "mirror reflecting only an empty room, calm warm light with cool shadows receding"
            ),
            "avoid_people": True,
        },
    ]


def _thumbnail_hook_plans(title: str, agent_id: str | None = None) -> list[dict]:
    """
    Three deterministic YouTube-thumbnail concepts. Hooks stay short because
    the image model now renders the final Spanish text inside the thumbnail.
    """
    clean_title = " ".join((title or "").split()) or "este documental"
    lower = clean_title.lower()
    is_attraction = any(word in lower for word in ["atraccion", "atracción", "amor", "enamor", "pareja"])
    is_science = any(word in lower for word in ["ciencia", "cerebro", "psicologia", "psicología", "neuro"])
    keywords = _pick_thumbnail_keywords(clean_title, max_words=3)

    if agent_id in {"agent_autohipnosis", "agent_meditacion_larga"}:
        return _wellness_thumbnail_hook_plans(clean_title, agent_id=agent_id)

    if agent_id == "agent_podcast_general" and _is_esto_no_es_amor_topic(clean_title):
        return _esto_no_es_amor_thumbnail_hook_plans(clean_title)

    if is_attraction or is_science:
        return [
            {
                "label": "early",
                "variant": "impacto",
                "hook": "TU CEREBRO\nYA ELIGIÓ",
                "concept": "two attractive adults in dramatic side profile facing each other, separated by a glowing neural brain and electric heart signal, blue scientific light on the left and red emotional light on the right",
            },
            {
                "label": "mid",
                "variant": "secreto",
                "hook": "CIENCIA\nDE LA ATRACCIÓN",
                "concept": "a glowing human brain, dopamine and oxytocin inspired molecular diagrams, magnetic energy between two people at the edges of frame, intelligent viral science thumbnail",
            },
            {
                "label": "closing",
                "variant": "revelacion",
                "hook": "NO ES AMOR\nES QUÍMICA",
                "concept": "cinematic podcast set with a microphone, a glowing brain and heart connection in the background, romantic tension without physical contact, premium documentary atmosphere",
            },
        ]

    return [
        {
            "label": "early",
            "variant": "impacto",
            "hook": keywords or "LA VERDAD",
            "concept": f"high-stakes cinematic documentary poster background about {clean_title}, a single expressive main subject on one side, bold contrast, mystery and curiosity",
        },
        {
            "label": "mid",
            "variant": "secreto",
            "hook": "NADIE\nTE LO CONTÓ",
            "concept": f"hidden evidence, dramatic light, symbolic objects and investigative mood connected to {clean_title}, premium viral YouTube documentary style",
        },
        {
            "label": "closing",
            "variant": "revelacion",
            "hook": "LA PARTE\nOCULTA",
            "concept": f"cinematic reveal moment for a documentary about {clean_title}, intense contrast, clean dark space for headline, sophisticated editorial look",
        },
    ]


def _build_premium_thumbnail_prompt(
    title: str,
    plan: dict,
    agent_id: str | None = None,
    *,
    render_headline: bool = True,
) -> str:
    clean_title = " ".join((title or "").split()) or "este documental"
    headline_lines = _thumbnail_hook_lines(plan.get("hook", ""))
    headline_instructions = "\n".join(
        f"  Line {idx}: \"{line}\""
        for idx, line in enumerate(headline_lines, 1)
    )
    format_badge = _thumbnail_format_badge(agent_id)
    badge_instruction = (
        f"Do not render the format badge text \"{format_badge}\"; it will be added later as a separate overlay.\n"
        if format_badge
        else ""
    )
    format_hint = (
        "podcast thumbnail"
        if agent_id == "agent_podcast_general"
        else "guided meditation thumbnail"
        if agent_id in {"agent_autohipnosis", "agent_meditacion_larga"}
        else "documentary thumbnail"
    )
    safety_hint = (
        "This is wellness and personal growth content, not medical treatment. "
        "Avoid clinical, hospital, doctor, pill, or therapy imagery. "
        if agent_id in {"agent_autohipnosis", "agent_meditacion_larga"}
        else ""
    )
    avoid_people = bool(plan.get("avoid_people"))
    if avoid_people:
        safety_hint += (
            "For this relationship-healing podcast channel, use object-led emotional metaphors only. "
            "No people, no faces, no silhouettes, no bodies, no hands, no fingers, no microphones, "
            "no speakers, no headphones, no audio gear, no podcast studio equipment. "
            "Avoid generic brain-science or romance-stock imagery unless the title explicitly asks for it. "
        )
    people_rules = (
        "- No people, no visible faces, no hands or fingers, no silhouettes, no bodies.\n"
        if avoid_people
        else (
            "- No visible hands or fingers; crop people at face/shoulders or keep hands fully outside the frame.\n"
            "- Faces must be realistic, expressive, premium, not uncanny.\n"
        )
    )
    if render_headline:
        headline_block = (
            "Main headline text to render exactly, large and crisp, on separate lines:\n"
            f"{headline_instructions}\n"
            "Do not render the words 'Line', line numbers, slashes, pipes, quotes, or separators.\n"
        )
        text_composition_rules = (
            "- The thumbnail must already include the headline text as part of the generated image.\n"
            "- Spell the Spanish headline exactly; no extra words, subtitles, quotes, pseudo-text, logos, or watermarks.\n"
            "- Make the headline huge, bold, high-contrast, and readable on a phone screen.\n"
        )
    else:
        headline_block = (
            f"Create a text-free thumbnail background for the exact video title: \"{clean_title}\".\n"
            "Do not render any letters, words, captions, subtitles, labels, signs, pseudo-text, logos, or watermarks anywhere.\n"
        )
        text_composition_rules = (
            "- Leave generous negative space for a later backend overlay of the exact title text.\n"
            "- Keep the most important visual subject outside the title-safe area; prefer emotional objects on the right or lower third.\n"
            "- The final title will be added by code, so the generated image itself must be completely text-free.\n"
        )
    return (
        "Create a finished, high-conversion YouTube "
        f"{format_hint}, 16:9 landscape, topic: \"{clean_title}\".\n"
        f"{headline_block}"
        f"{badge_instruction}"
        f"Core concept: {plan['concept']}.\n"
        f"Variant direction: {plan.get('variant', 'primary')}. Make this concept visually specific to the topic; avoid generic wellness stock-image layouts.\n"
        f"{safety_hint}"
        "Composition requirements:\n"
        f"{text_composition_rules}"
        "- Keep the final title area and main subject fully inside the central 16:9 safe area; the image may be center-cropped from 1536x1024 to 1280x720.\n"
        "- Reserve the top-right corner for a later format badge overlay; do not place the main title area or face there.\n"
        f"{people_rules}"
        "- Strong contrast, sharp focus, punchy but tasteful color accents, mobile-readable composition.\n"
        "- Clickbait must be safe and truthful: curiosity, transformation, mystery, or emotional payoff without deception.\n"
        "- Avoid horror, gore, distorted bodies, extra limbs, malformed anatomy, medical claims, and controversial shock imagery.\n"
        "Style: hyper-realistic cinematic poster, premium viral YouTube thumbnail, "
        "Netflix documentary meets intelligent clickbait, crisp details, polished creator-grade design."
    )


def _write_openai_image_data(image_data, output_path: Path) -> bool:
    b64_value = getattr(image_data, "b64_json", None)
    if b64_value is None and isinstance(image_data, dict):
        b64_value = image_data.get("b64_json")
    if b64_value:
        output_path.write_bytes(base64.b64decode(b64_value))
        return output_path.exists() and output_path.stat().st_size > 0

    image_url = getattr(image_data, "url", None)
    if image_url is None and isinstance(image_data, dict):
        image_url = image_data.get("url")
    if image_url:
        with urllib.request.urlopen(image_url, timeout=90) as resp:
            output_path.write_bytes(resp.read())
        return output_path.exists() and output_path.stat().st_size > 0
    return False


def _generate_premium_thumbnail_image(prompt: str, output_path: Path) -> bool:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("   ⚠️ OPENAI_API_KEY no configurada; usando miniaturas de escenas")
        return False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = _thumbnail_model()
        params = {
            "model": model,
            "prompt": prompt,
            "size": _thumbnail_generation_size(model),
            "quality": _thumbnail_quality(),
            "n": 1,
        }
        if model.startswith("gpt-image") or model == "chatgpt-image-latest":
            params["output_format"] = "jpeg"
            params["output_compression"] = 92
        response = client.images.generate(**params)
        data = getattr(response, "data", None) or []
        if not data:
            print("   ⚠️ Image API no devolvió datos para thumbnail premium")
            return False
        return _write_openai_image_data(data[0], output_path)
    except Exception as e:
        print(f"   ⚠️ Premium thumbnail generation failed: {e}")
        return False


def _generate_premium_thumbnail_background(prompt: str, output_path: Path) -> bool:
    # Backward-compatible alias for older tests/scripts. New thumbnails are
    # complete generated images, not blank backgrounds for local text overlay.
    return _generate_premium_thumbnail_image(prompt, output_path)


def _cover_resize_image(img, target_w: int = 1280, target_h: int = 720):
    from PIL import Image
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h
    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _fit_generated_thumbnail_canvas(img, target_w: int = 1280, target_h: int = 720):
    from PIL import Image

    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    scale = max(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    x = (target_w - new_w) // 2
    if src_ratio < target_ratio:
        # GPT Image often places thumbnail headlines near the top on 3:2 renders.
        # Preserve that copy and crop the quieter lower area instead of letterboxing.
        y = 0
    else:
        y = (target_h - new_h) // 2
    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    canvas.paste(resized, (x, y))
    return canvas.crop((0, 0, target_w, target_h))


def _draw_thumbnail_badge(draw, badge: str, target_w: int, theme: dict | None = None):
    if not badge:
        return
    from PIL import ImageFont

    th = {**THUMBNAIL_DEFAULT_THEME, **(theme or {})}
    badge_text = badge.strip().upper()[:22]
    badge_font = None
    for fp in [th["font_path_fallback"], th["font_path_primary"]]:
        try:
            if os.path.exists(fp):
                badge_font = ImageFont.truetype(fp, 34)
                break
        except Exception:
            continue
    if badge_font is None:
        badge_font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), badge_text, font=badge_font, stroke_width=2)
    bw = bbox[2] - bbox[0] + 34
    bh = bbox[3] - bbox[1] + 22
    x0, y0 = target_w - bw - 36, 32
    draw.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=12, fill=(0, 0, 0, 205))
    draw.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=12, outline=(255, 214, 10, 230), width=3)
    draw.text(
        (x0 + 17, y0 + 9),
        badge_text,
        font=badge_font,
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )


def _thumbnail_display_title(title: str) -> str:
    clean = " ".join((title or "").split()).strip()
    return (clean or "Contenido completo").upper()


def _measure_text_width(draw, text: str, font, stroke_width: int = 0) -> int:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return bbox[2] - bbox[0]


def _wrap_thumbnail_title(draw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or _measure_text_width(draw, candidate, font, stroke_width=7) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def _fit_exact_title_layout(draw, title_text: str, max_width: int, max_height: int):
    display = _thumbnail_display_title(title_text)
    max_lines = 5 if len(display) > 58 else 4
    for size in range(106, 35, -3):
        font = _load_thumbnail_font(size)
        spacing = max(5, size // 11)
        lines = _wrap_thumbnail_title(draw, display, font, max_width)
        if len(lines) > max_lines:
            continue
        widths, heights = [], []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=7)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])
        total_height = sum(heights) + spacing * (len(lines) - 1)
        if max(widths or [0]) <= max_width and total_height <= max_height:
            return font, lines, spacing, widths, heights

    font = _load_thumbnail_font(36)
    spacing = 5
    lines = _wrap_thumbnail_title(draw, display, font, max_width)
    widths, heights = [], []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=6)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    return font, lines, spacing, widths, heights


def _exact_title_overlay_box(variant: str | None) -> tuple[int, int, int, int, str]:
    normalized = (variant or "").lower()
    if normalized in {"patron", "secreto", "mid"}:
        return 92, 110, 835, 486, "center"
    if normalized in {"paz", "revelacion", "closing"}:
        return 70, 116, 790, 500, "left"
    return 70, 105, 820, 500, "left"


def _draw_exact_title_overlay(img, title_text: str, variant: str | None = None):
    from PIL import Image, ImageDraw, ImageFilter

    img = img.convert("RGBA")
    target_w, target_h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(overlay)

    for x in range(0, min(target_w, 910), 3):
        alpha = max(0, int(220 * (1 - (x / 910))))
        gd.rectangle((x, 0, x + 2, target_h), fill=(0, 0, 0, alpha))
    for y in range(target_h // 2, target_h, 3):
        alpha = int(((y - target_h // 2) / (target_h // 2)) * 105)
        gd.rectangle((0, y, target_w, y + 2), fill=(0, 0, 0, alpha))

    x0, y0, max_w, max_h, align = _exact_title_overlay_box(variant)
    gd.rounded_rectangle((x0 - 24, y0 - 20, x0 + max_w + 34, y0 + max_h + 24), radius=22, fill=(0, 0, 0, 78))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img, "RGBA")
    font, lines, spacing, widths, heights = _fit_exact_title_layout(draw, title_text, max_w, max_h)
    total_height = sum(heights) + spacing * (len(lines) - 1)
    y = y0 + max(0, (max_h - total_height) // 2)

    for idx, line in enumerate(lines):
        width = widths[idx]
        x = x0 + (max_w - width) // 2 if align == "center" else x0
        fill = (255, 255, 255)
        if idx == len(lines) - 1 and len(lines) > 1:
            fill = (255, 214, 10)

        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.text((x + 8, y + 9), line, font=font, fill=(0, 0, 0, 210), stroke_width=11, stroke_fill=(0, 0, 0, 230))
        shadow = shadow.filter(ImageFilter.GaussianBlur(1.2))
        img = Image.alpha_composite(img, shadow)
        draw = ImageDraw.Draw(img, "RGBA")
        draw.text((x, y), line, font=font, fill=fill, stroke_width=7, stroke_fill=(0, 0, 0))
        y += heights[idx] + spacing

    return img


def _finalize_generated_thumbnail(raw_image: Path, output_path: Path, badge: str | None = None,
                                  title_text: str | None = None,
                                  variant: str | None = None) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageEnhance
    except ImportError:
        print("   ❌ Pillow no disponible para finalizar thumbnails")
        return False

    try:
        img = Image.open(raw_image).convert("RGB")
        img = _fit_generated_thumbnail_canvas(img, 1280, 720)
        img = ImageEnhance.Contrast(img).enhance(1.04)
        img = ImageEnhance.Sharpness(img).enhance(1.05)
        if title_text:
            img = _draw_exact_title_overlay(img, title_text, variant=variant)
        if badge:
            draw = ImageDraw.Draw(img, "RGBA")
            _draw_thumbnail_badge(draw, badge, 1280)
        img.convert("RGB").save(str(output_path), "JPEG", quality=94, optimize=True)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"   ❌ Generated thumbnail finalize failed: {e}")
        return False


def _load_thumbnail_font(size: int):
    from PIL import ImageFont
    for font_path in _thumbnail_font_paths():
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _fit_thumbnail_font(draw, lines: list[str], max_width: int, max_height: int):
    for size in range(136, 54, -4):
        font = _load_thumbnail_font(size)
        spacing = max(6, size // 12)
        widths = []
        heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=8)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])
        total_height = sum(heights) + spacing * (len(lines) - 1)
        if max(widths or [0]) <= max_width and total_height <= max_height:
            return font, spacing, widths, heights
    font = _load_thumbnail_font(54)
    spacing = 6
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=8)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    return font, spacing, widths, heights


def _thumbnail_lines_for_overlay(draw, hook_text: str, max_width: int, max_height: int):
    if "\n" not in (hook_text or "") and len((hook_text or "").strip()) > 32:
        font, lines, spacing, widths, heights = _fit_exact_title_layout(draw, hook_text, max_width, max_height)
        return lines, font, spacing, widths, heights

    lines = _thumbnail_hook_lines(hook_text)
    font, spacing, widths, heights = _fit_thumbnail_font(draw, lines, max_width, max_height)
    return lines, font, spacing, widths, heights


def _render_premium_thumbnail(base_image: Path, hook_text: str, output_path: Path,
                              variant: str = "impacto", badge: str | None = None) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    except ImportError:
        print("   ❌ Pillow no disponible para thumbnails")
        return False

    try:
        img = Image.open(base_image).convert("RGB")
        img = _cover_resize_image(img, 1280, 720)

        img = ImageEnhance.Color(img).enhance(1.20)
        img = ImageEnhance.Contrast(img).enhance(1.18)
        img = ImageEnhance.Sharpness(img).enhance(1.12)
        img = ImageEnhance.Brightness(img).enhance(0.90)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(overlay)
        for y in range(220, 720):
            alpha = int(((y - 220) / 500) * 210)
            gd.line([(0, y), (1280, y)], fill=(0, 0, 0, min(alpha, 210)))
        gd.rounded_rectangle((52, 355, 1228, 682), radius=20, fill=(0, 0, 0, 76))
        gd.rectangle((52, 668, 1228, 682), fill=(0, 216, 255, 190 if variant == "impacto" else 120))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)

        draw = ImageDraw.Draw(img, "RGBA")
        lines, font, spacing, widths, heights = _thumbnail_lines_for_overlay(draw, hook_text, 1120, 270)
        total_height = sum(heights) + spacing * (len(lines) - 1)
        y = 385 + (270 - total_height) // 2
        colors = [(255, 255, 255), (255, 214, 10), (255, 255, 255)]

        for idx, line in enumerate(lines):
            width = widths[idx]
            height = heights[idx]
            x = (1280 - width) // 2
            fill = colors[min(idx, len(colors) - 1)]
            if any(token in line for token in ["ATRAC", "QUIM", "QUÍM", "OCULTA", "ELIG"]):
                fill = (255, 214, 10)
            shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.text((x + 8, y + 8), line, font=font, fill=(0, 0, 0, 190), stroke_width=10, stroke_fill=(0, 0, 0, 210))
            shadow = shadow.filter(ImageFilter.GaussianBlur(1.3))
            img = Image.alpha_composite(img, shadow)
            draw = ImageDraw.Draw(img, "RGBA")
            draw.text(
                (x, y),
                line,
                font=font,
                fill=fill,
                stroke_width=8,
                stroke_fill=(0, 0, 0),
            )
            y += height + spacing

        if badge:
            badge_text = badge.strip().upper()[:14]
            badge_font = _load_thumbnail_font(34)
            bbox = draw.textbbox((0, 0), badge_text, font=badge_font, stroke_width=2)
            bw = bbox[2] - bbox[0] + 34
            bh = bbox[3] - bbox[1] + 22
            x0, y0 = 1280 - bw - 52, 52
            draw.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=10, fill=(225, 52, 36, 235))
            draw.text((x0 + 17, y0 + 9), badge_text, font=badge_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))

        img.convert("RGB").save(str(output_path), "JPEG", quality=94, optimize=True)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"   ❌ Premium thumbnail render failed: {e}")
        return False


def _build_premium_thumbnails_for_project(video_dir: Path, project_id: str, title: str,
                                          agent_id: str | None = None) -> list:
    if not _premium_thumbnails_enabled():
        return []

    thumbs_dir = video_dir / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    badge = _thumbnail_format_badge(agent_id)
    exact_title_overlay = _thumbnail_exact_title_overlay_enabled()
    results = []
    for i, plan in enumerate(_thumbnail_hook_plans(title, agent_id=agent_id), 1):
        label = plan["label"]
        variant = plan["variant"]
        safe_variant = _thumbnail_safe_filename(variant)
        raw = thumbs_dir / f"THUMB_RAW_{i:02d}_{safe_variant}.jpg"
        out = thumbs_dir / f"THUMB_{i:02d}_{label}_{safe_variant}.jpg"
        prompt = _build_premium_thumbnail_prompt(
            title,
            plan,
            agent_id=agent_id,
            render_headline=not exact_title_overlay,
        )

        print(f"   🖼️ Diseñando miniatura premium {i}/3 ({variant})")
        if not _generate_premium_thumbnail_image(prompt, raw):
            continue
        if not _finalize_generated_thumbnail(
            raw,
            out,
            badge=badge,
            title_text=title if exact_title_overlay else None,
            variant=variant,
        ):
            continue
        upload = _upload_video_to_storage(out, f"{project_id}/thumbnails")
        if upload:
            results.append({
                "index": i,
                "label": label,
                "variant": variant,
                "source": "gpt-image",
                "hook": plan["hook"],
                "display_text": _thumbnail_display_title(title) if exact_title_overlay else plan["hook"],
                "text_mode": "exact_title_overlay" if exact_title_overlay else "generated_headline",
                "model": _thumbnail_model(),
                "badge": badge,
                "size_kb": round(out.stat().st_size / 1024, 1),
                "gs_path": upload["gs_path"],
                "signed_url": upload["signed_url"],
            })
            print(f"   ✅ Miniatura premium {i} subida ({results[-1]['size_kb']} KB)")
    return results


def _render_thumbnail(source_image: Path, title_text: str, output_path: Path,
                      variant: str = "center", theme: dict = None,
                      badge: str | None = None) -> bool:
    """
    Compone un thumbnail 1280x720 a partir de una imagen base (de las escenas
    ya generadas para el video) + texto grande superpuesto.

    variants:
      - 'center': texto grande al centro con bg gradiente
      - 'bottom': texto en el tercio inferior
      - 'corner': texto en una esquina con caja roja de acento
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        print("   ❌ Pillow no disponible para thumbnails")
        return False

    th = {**THUMBNAIL_DEFAULT_THEME, **(theme or {})}
    try:
        img = Image.open(source_image).convert("RGB")
        # Resize a 1280x720 (cover) preservando aspecto, luego center crop
        target_w, target_h = 1280, 720
        src_w, src_h = img.size
        src_ratio = src_w / src_h
        target_ratio = target_w / target_h
        if src_ratio > target_ratio:
            # mas ancho de lo necesario: ajustar por altura
            new_h = target_h
            new_w = int(new_h * src_ratio)
        else:
            new_w = target_w
            new_h = int(new_w / src_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))

        # Saturar y oscurecer ligeramente para resaltar el texto
        from PIL import ImageEnhance
        img = ImageEnhance.Color(img).enhance(1.15)
        img = ImageEnhance.Contrast(img).enhance(1.10)
        img = ImageEnhance.Brightness(img).enhance(0.85)

        draw = ImageDraw.Draw(img, "RGBA")
        lines, font, spacing, widths, heights = _thumbnail_lines_for_overlay(draw, title_text, 1120, 300)
        text = "\n".join(lines)
        text_w = max(widths or [0])
        text_h = sum(heights) + spacing * (len(lines) - 1)

        # Posición según variant
        if variant == "bottom":
            x = (target_w - text_w) // 2
            y = target_h - text_h - 60
            # Gradiente más fuerte abajo
            grad = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(grad)
            for i in range(target_h // 2, target_h):
                alpha = int(((i - target_h // 2) / (target_h // 2)) * 230)
                gd.line([(0, i), (target_w, i)], fill=(0, 0, 0, alpha))
            img.paste(Image.alpha_composite(img.convert("RGBA"), grad).convert("RGB"))
        elif variant == "corner":
            x = 60
            y = 60
            # Caja roja accent debajo del texto
        else:  # center
            x = (target_w - text_w) // 2
            y = (target_h - text_h) // 2
            # Gradiente radial tenue para resaltar
            grad = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(grad)
            cx, cy = target_w // 2, target_h // 2
            for r in range(0, max(target_w, target_h), 4):
                alpha = max(0, 80 - r * 80 // (target_w // 2))
                gd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=None, fill=(0, 0, 0, alpha))
            img.paste(Image.alpha_composite(img.convert("RGBA"), grad).convert("RGB"))

        # Dibujar texto con stroke
        draw = ImageDraw.Draw(img, "RGBA")
        draw.multiline_text(
            (x, y), text, font=font, fill=th["text_color"],
            stroke_width=th["stroke_width"], stroke_fill=th["stroke_color"],
            align="center", spacing=spacing,
        )

        # Variant 'corner': agregar barra roja vertical de acento a la izquierda
        if variant == "corner":
            draw.rectangle([(0, 0), (12, target_h)], fill=th["accent_color"])

        if badge:
            _draw_thumbnail_badge(draw, badge, target_w, theme=th)

        img.save(str(output_path), "JPEG", quality=92, optimize=True)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"   ❌ Thumbnail render failed: {e}")
        return False


def _build_scene_thumbnails_for_project(video_dir: Path, project_id: str, title: str,
                                        start_index: int = 1,
                                        agent_id: str | None = None) -> list:
    """
    Fallback barato: 3 thumbnails 1280x720 a partir de imagenes del video.
    """
    images_dir = video_dir / "images"
    if not images_dir.is_dir():
        print(f"   ⚠️ No hay carpeta de imágenes en {video_dir}, no genero thumbnails")
        return []

    scenes = sorted(images_dir.glob("scene_*.png")) or sorted(images_dir.glob("scene_*.jpg"))
    if len(scenes) < 3:
        print(f"   ⚠️ Solo {len(scenes)} imágenes disponibles, mínimo 3 para thumbnails")
        return []

    plans = _thumbnail_hook_plans(title, agent_id=agent_id)

    # Pick 3 escenas distintas: 20%, 50%, 80% del video
    picks = [
        ("early", scenes[len(scenes) // 5], "center"),
        ("mid", scenes[len(scenes) // 2], "bottom"),
        ("late", scenes[(len(scenes) * 4) // 5], "corner"),
    ]

    thumbs_dir = video_dir / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    results = []
    badge = _thumbnail_format_badge(agent_id)
    exact_title_overlay = _thumbnail_exact_title_overlay_enabled()
    for offset, (label, src, variant) in enumerate(picks, 0):
        i = start_index + offset
        plan = plans[min(i - 1, len(plans) - 1)]
        hook = title if exact_title_overlay else (plan.get("hook") or _pick_thumbnail_keywords(title, max_words=3))
        out = thumbs_dir / f"THUMB_{i:02d}_{label}_{variant}.jpg"
        print(f"   🖼️ Renderizando thumbnail fallback {i} ({label}, variant={variant})")
        if not _render_thumbnail(src, hook, out, variant=variant, badge=badge):
            continue
        upload = _upload_video_to_storage(out, f"{project_id}/thumbnails")
        if upload:
            results.append({
                "index": i,
                "label": label,
                "variant": variant,
                "source": "scene",
                "hook": hook,
                "display_text": _thumbnail_display_title(title) if exact_title_overlay else hook,
                "text_mode": "exact_title_overlay" if exact_title_overlay else "hook_overlay",
                "badge": badge,
                "size_kb": round(out.stat().st_size / 1024, 1),
                "gs_path": upload["gs_path"],
                "signed_url": upload["signed_url"],
            })
            print(f"   ✅ Thumbnail {i} subido ({results[-1]['size_kb']} KB)")
    return results


def _reindex_thumbnail_results(results: list) -> list:
    normalized = []
    for i, item in enumerate(results, 1):
        normalized.append({**item, "index": i})
    return normalized


def build_thumbnails_for_project(video_dir: Path, project_id: str, title: str,
                                 agent_id: str | None = None,
                                 premium: bool | None = None) -> list:
    """
    Genera 3 thumbnails 1280x720 y las sube a Firebase Storage.

    Ruta premium:
      1. Genera la miniatura completa con GPT Image y texto integrado.
      2. Normaliza a JPEG 1280x720.
      3. Si cualquier parte falla, usa fallback local con hooks cortos.
    """
    use_premium = _premium_thumbnails_enabled() if premium is None else bool(premium)
    results = []
    if use_premium:
        results = _build_premium_thumbnails_for_project(
            video_dir,
            project_id,
            title,
            agent_id=agent_id,
        )
        if len(results) >= 3:
            return _reindex_thumbnail_results(results[:3])
        if results:
            print(f"   ⚠️ Premium thumbnails incompletas ({len(results)}/3); completando con escenas")

    fallback = _build_scene_thumbnails_for_project(
        video_dir,
        project_id,
        title,
        start_index=len(results) + 1,
        agent_id=agent_id,
    )
    return _reindex_thumbnail_results((results + fallback)[:3])


def _build_master_audio(video_dir: Path) -> Path | None:
    """
    Concatena narration_*.mp3 en master_audio.mp3 con validación robusta.

    Estrategia:
      1. Intenta concat demuxer (rápido). Funciona si todos los MP3 tienen mismo formato.
      2. Si falla, intenta filter_complex (re-decodifica todo a un formato común).
      3. Verifica que el archivo final exista y tenga tamaño > 0 antes de retornarlo.

    Retorna Path al master_audio.mp3 si tuvo éxito, None si todo falló.
    Loggea claramente cada paso para que el operador pueda diagnosticar.
    """
    audio_dir = video_dir / "audio"
    if not audio_dir.is_dir():
        print(f"   ⚠️ No existe {audio_dir} — no hay narraciones para concatenar")
        return None

    narrations = sorted(audio_dir.glob("narration_*.mp3"))
    if not narrations:
        print(f"   ⚠️ No se encontraron archivos narration_*.mp3 en {audio_dir}")
        return None

    print(f"   🔗 Concatenando {len(narrations)} narraciones en master_audio.mp3")
    master_audio = video_dir / "master_audio.mp3"
    concat_list = video_dir / "_concat_audio.txt"

    try:
        # Intento 1: concat demuxer (rápido, requiere mismo formato)
        with open(concat_list, "w") as cl:
            for n in narrations:
                cl.write(f"file '{n}'\n")

        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list), "-c:a", "libmp3lame",
             "-b:a", "192k", str(master_audio)],
            capture_output=True, text=True, timeout=180,
        )

        if result.returncode == 0 and master_audio.exists() and master_audio.stat().st_size > 0:
            print(f"   ✅ Concat demuxer OK ({master_audio.stat().st_size // 1024} KB)")
            return master_audio

        print(f"   ⚠️ Concat demuxer falló (rc={result.returncode}); intentando filter_complex")
        if result.stderr:
            print(f"      stderr: {result.stderr[-300:]}")

        # Intento 2: filter_complex (lento pero robusto, re-decodifica todo)
        inputs = []
        for n in narrations:
            inputs.extend(["-i", str(n)])
        filter_str = "".join(f"[{i}:a]" for i in range(len(narrations))) + f"concat=n={len(narrations)}:v=0:a=1[out]"

        result = subprocess.run(
            ["ffmpeg", "-y", *inputs,
             "-filter_complex", filter_str,
             "-map", "[out]", "-c:a", "libmp3lame",
             "-b:a", "192k", str(master_audio)],
            capture_output=True, text=True, timeout=300,
        )

        if result.returncode == 0 and master_audio.exists() and master_audio.stat().st_size > 0:
            print(f"   ✅ filter_complex OK ({master_audio.stat().st_size // 1024} KB)")
            return master_audio

        print(f"   ❌ filter_complex también falló (rc={result.returncode})")
        if result.stderr:
            print(f"      stderr: {result.stderr[-500:]}")
        return None

    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout concatenando audio ({len(narrations)} archivos)")
        return None
    except Exception as e:
        print(f"   ❌ Excepción concatenando audio: {e}")
        return None
    finally:
        if concat_list.exists():
            concat_list.unlink()


@app.get("/images/{project}/{filename}")
def serve_image(project: str, filename: str):
    """Sirve imágenes generadas desde el filesystem del VPS."""
    img_path = Path(f"/app/output/videos/{project}/images/{filename}")
    if img_path.exists():
        return FileResponse(img_path, media_type="image/png")
    return {"error": "Image not found"}


# Catálogo compacto de agentes para el clasificador (id + descripción de 1 línea).
# Mantener sincronizado con web/lib/agents.js — si agregas un agente allá,
# también aquí, en el mismo orden.
_AGENT_CATALOG = """
[agent_horror] Horror Histórico — torturas, plagas, castillos malditos, episodios oscuros documentados
[agent_misterios] Misterios Sin Resolver — desapariciones, casos fríos, anomalías sin explicación
[agent_biografias] Biografías Épicas — vidas legendarias con drama humano, figuras históricas
[agent_ciencia] Ciencia Explicada — universo, física cuántica, biología, asombro cósmico
[agent_finanzas] Catástrofes Financieras — crashes bursátiles, esquemas Ponzi, burbujas, fraudes
[agent_filosofia] Filosofía Estoica — Marco Aurelio, Séneca, sabiduría aplicada al presente
[agent_erotico_historico] Romance Histórico — cortes reales, cortesanas, poder y seducción de época
[agent_historico] Documental Histórico — vida cotidiana en eras antiguas, "un día en la vida de"
[agent_psicologia_oscura] Psicología Oscura — manipulación, narcisistas, psicópatas, cultos, control mental
[agent_civilizaciones] Civilizaciones Perdidas — Mayas, Atlántida, Sumeria, descubrimientos arqueológicos
[agent_true_crime] True Crime — asesinos seriales, crímenes famosos, investigaciones policiacas
[agent_mitologia] Mitología Universal — dioses, mitos, leyendas de culturas del mundo
[agent_conspiraciones] Conspiraciones — MK-Ultra, Area 51, gobiernos secretos, documentos clasificados
[agent_tecnologia] Tecnología del Futuro — IA, neuralink, fusión nuclear, robots, computación cuántica
[agent_guerras] Guerras y Batallas — Stalingrado, batallas decisivas, estrategia militar épica
[agent_espionaje] Espionaje Real — espías reales, KGB, CIA, operaciones encubiertas
[agent_apocalipsis] Apocalipsis y Catástrofes — Pompeya, Chernóbil, desastres naturales históricos
[agent_religiones] Religiones del Mundo — Vaticano, sectas, misticismo, historia de creencias
[agent_metafisica] Metafísica y Consciencia — Jung, DMT, simulación, experiencias cercanas a la muerte
[agent_imperios] Imperios Legendarios — Mongol, Romano, Otomano, auge y caída de potencias
[agent_arte] Arte y Genios Creativos — Van Gogh, Da Vinci, Picasso, vidas atormentadas de artistas
[agent_emprendimiento] Emprendimiento Extremo — Musk, Jobs, fundadores que casi quiebran y resurgen
[agent_negocios] Negocios y Estrategia — guerras corporativas, quiebras famosas, decisiones empresariales
[agent_liderazgo] Liderazgo y Poder — Mandela, Churchill, líderes que cambiaron el mundo
[agent_biblico] Historias Bíblicas — Éxodo, Apocalipsis, arqueología bíblica, relatos sagrados
[agent_viajes] Viajes y Exploraciones — Shackleton, Everest, lugares peligrosos del mundo
[agent_noticias_virales] Noticias Virales — eventos actuales que están en tendencia esta semana
[agent_podcast_general] Esto no es amor — conversación entre dos hosts (Mateo y Lucía) sobre cualquier tema, formato podcast multitema con dos voces alternando
[agent_autohipnosis] Autohipnosis Guiada — wellness, relajación, visualización, afirmaciones positivas, desarrollo personal seguro
[agent_meditacion_larga] Meditación Larga — sesiones de 30 min, 1 h y 3 h para sueño, calma, afirmaciones espaciadas y visuales lentos
""".strip()

_RADAR_EXTRA_AGENTS = [
    {
        "agentId": "agent_tiktok_documentary",
        "name": "TikTok Documental",
        "description": "Mini-documentales verticales con hook inmediato, beats cortos y cierre social",
        "category": "tiktok",
        "platform": "tiktok",
        "format": "tiktok_documentary",
        "promptFile": "agent_tiktok_documentary.md",
    },
    {
        "agentId": "agent_tiktok_podcast",
        "name": "TikTok Podcast",
        "description": "Micro-conversaciones verticales para Esto no es amor sobre apego, limites y amor propio",
        "category": "tiktok",
        "platform": "tiktok",
        "format": "tiktok_podcast",
        "promptFile": "agent_tiktok_podcast.md",
    },
    {
        "agentId": "agent_tiktok_autohipnosis",
        "name": "TikTok Autohipnosis",
        "description": "Autohipnosis vertical breve, segura y calmada sin promesas medicas",
        "category": "tiktok",
        "platform": "tiktok",
        "format": "tiktok_autohypnosis",
        "promptFile": "agent_tiktok_autohipnosis.md",
    },
    {
        "agentId": "agent_tiktok_meditation",
        "name": "TikTok Meditación",
        "description": "Meditaciones verticales cortas para respirar, calmar el cuerpo y volver al presente",
        "category": "tiktok",
        "platform": "tiktok",
        "format": "tiktok_meditation",
        "promptFile": "agent_tiktok_meditation.md",
    },
]

_RADAR_PRIORITY_AGENT_IDS = [
    RADAR_NEWS_AGENT_ID,
    "agent_podcast_general",
    "agent_tiktok_podcast",
    "agent_tiktok_documentary",
    "agent_meditacion_larga",
    "agent_autohipnosis",
    "agent_tecnologia",
    "agent_finanzas",
]


def _radar_is_enabled() -> bool:
    return _flag_enabled("CONTENT_FACTORY_RADAR_ENABLED", default=True)


def _radar_require_admin(request: Request, *, allow_local: bool = False) -> dict:
    if not _radar_is_enabled():
        raise HTTPException(status_code=404, detail="radar disabled")
    if not _flag_enabled("CONTENT_FACTORY_RADAR_ADMIN_ONLY", default=True):
        return _require_principal(request, allow_admin=True, allow_local=allow_local)
    return _require_admin(request, allow_local=allow_local)


def _radar_agent_catalog() -> list[dict]:
    category_by_id = {
        "agent_horror": "history",
        "agent_misterios": "mystery",
        "agent_biografias": "biography",
        "agent_ciencia": "science",
        "agent_finanzas": "finance",
        "agent_filosofia": "philosophy",
        "agent_erotico_historico": "romance",
        "agent_historico": "history",
        "agent_psicologia_oscura": "psychology",
        "agent_civilizaciones": "history",
        "agent_true_crime": "crime",
        "agent_mitologia": "mythology",
        "agent_conspiraciones": "mystery",
        "agent_tecnologia": "technology",
        "agent_guerras": "history",
        "agent_espionaje": "mystery",
        "agent_apocalipsis": "science",
        "agent_religiones": "religion",
        "agent_metafisica": "philosophy",
        "agent_imperios": "history",
        "agent_arte": "biography",
        "agent_emprendimiento": "business",
        "agent_negocios": "business",
        "agent_liderazgo": "biography",
        "agent_biblico": "religion",
        "agent_viajes": "travel",
        "agent_noticias_virales": "news",
        "agent_podcast_general": "podcast",
        "agent_autohipnosis": "wellness",
        "agent_meditacion_larga": "wellness",
    }
    agents = []
    for line in _AGENT_CATALOG.splitlines():
        match = re.match(r"\[(?P<id>agent_[^\]]+)\]\s*(?P<name>[^—]+)—\s*(?P<desc>.+)$", line.strip())
        if not match:
            continue
        aid = match.group("id").strip()
        platform = "tiktok" if aid in _TIKTOK_AGENT_IDS else "youtube"
        project_format = _TIKTOK_FORMAT_BY_AGENT.get(aid) or ""
        if aid == "agent_podcast_general":
            project_format = "podcast"
        elif aid == "agent_autohipnosis":
            project_format = "autohipnosis"
        elif aid == "agent_meditacion_larga":
            project_format = "meditacion_larga"
        agents.append({
            "agentId": aid,
            "name": match.group("name").strip(),
            "description": match.group("desc").strip(),
            "category": category_by_id.get(aid, "general"),
            "platform": platform,
            "format": project_format,
            "promptFile": f"{aid}.md",
        })
    known = {agent["agentId"] for agent in agents}
    agents.extend(agent for agent in _RADAR_EXTRA_AGENTS if agent["agentId"] not in known)
    return agents


def _radar_agent_by_id(agent_id: str) -> dict | None:
    for agent in _radar_agent_catalog():
        if agent["agentId"] == agent_id:
            return agent
    return None


def _radar_request_defaults(data: dict | None) -> dict:
    data = data or {}
    scope = str(data.get("scope") or "global").strip().lower()
    if scope not in {"global", "agent", "news"}:
        scope = "global"
    agent_id = str(data.get("agentId") or data.get("agent_id") or "").strip()
    intent = str(data.get("intent") or data.get("radarIntent") or RADAR_DEFAULT_INTENT).strip().lower().replace(" ", "_")
    if intent not in {"news", "viral_topics", "audience_pain", "evergreen", "shorts_hooks", "calendar_gaps"}:
        intent = RADAR_DEFAULT_INTENT
    if scope == "news":
        agent_id = RADAR_NEWS_AGENT_ID
        intent = "news"
    limit = max(1, min(RADAR_MAX_MANUAL_LIMIT, _safe_int(data.get("limit"), 3)))
    query_limit = max(1, min(5, _safe_int(data.get("queryLimit"), 2)))
    return {
        "scope": scope,
        "agentId": agent_id,
        "intent": intent,
        "market": str(data.get("market") or RADAR_DEFAULT_MARKET).strip().lower()[:24],
        "language": str(data.get("language") or RADAR_DEFAULT_LANGUAGE).strip().lower()[:12],
        "category": str(data.get("category") or RADAR_DEFAULT_CATEGORY).strip().lower()[:48],
        "window": str(data.get("window") or RADAR_DEFAULT_WINDOW).strip().lower()[:24],
        "limit": limit,
        "queryLimit": query_limit,
        "force": bool(data.get("force")),
    }


def _radar_library_doc_id(uid: str, candidate_hash: str) -> str:
    raw = f"{uid}|{candidate_hash}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:28]


def _radar_firestore_ts_expired(value) -> bool:
    if not value:
        return True
    try:
        if hasattr(value, "timestamp"):
            dt = datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= datetime.now(timezone.utc)
    except Exception:
        return True


def _radar_doc_to_public(doc_id: str, data: dict | None) -> dict:
    data = data or {}
    return {
        "runId": data.get("runId") or doc_id,
        "cacheKey": data.get("cacheKey") or doc_id,
        "mode": data.get("mode") or "",
        "scope": data.get("scope") or "",
        "agentId": data.get("agentId") or "",
        "intent": data.get("intent") or data.get("radarIntent") or RADAR_DEFAULT_INTENT,
        "radarIntent": data.get("intent") or data.get("radarIntent") or RADAR_DEFAULT_INTENT,
        "market": data.get("market") or RADAR_DEFAULT_MARKET,
        "language": data.get("language") or RADAR_DEFAULT_LANGUAGE,
        "category": data.get("category") or RADAR_DEFAULT_CATEGORY,
        "window": data.get("window") or RADAR_DEFAULT_WINDOW,
        "status": data.get("status") or "empty",
        "items": data.get("items") or [],
        "itemsCount": len(data.get("items") or []),
        "generatedAt": _serialize_firestore_value(data.get("generatedAt") or data.get("createdAt")),
        "expiresAt": _serialize_firestore_value(data.get("expiresAt")),
        "cached": bool(data.get("cached", False)),
        "error": data.get("error") or "",
    }


def _radar_existing_sets(db, uid: str) -> tuple[set[str], set[str]]:
    hashes = set()
    title_keys = set()
    try:
        for doc in db.collection("topicLibrary").stream():
            data = doc.to_dict() or {}
            if data.get("userId") not in {uid, "admin"}:
                continue
            if data.get("candidateHash"):
                hashes.add(data["candidateHash"])
            if data.get("agentId") and data.get("title"):
                title_keys.add(_radar_canonical_title_key(data["agentId"], data["title"]))
    except Exception:
        pass
    try:
        for doc in db.collection("projects").where("userId", "==", uid).stream():
            data = doc.to_dict() or {}
            if data.get("agentId") and data.get("title"):
                title_keys.add(_radar_canonical_title_key(data["agentId"], data["title"]))
            radar_hash = ((data.get("radar") or {}).get("candidateHash") or "")
            if radar_hash:
                hashes.add(radar_hash)
    except Exception:
        pass
    return hashes, title_keys


def _radar_search_tavily(query: str) -> dict:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return {}
    try:
        import requests
        timeout = max(2, min(12, _safe_int(os.environ.get("CONTENT_FACTORY_RADAR_TAVILY_TIMEOUT_SECONDS"), 5)))
        search_depth = os.environ.get("CONTENT_FACTORY_RADAR_TAVILY_DEPTH", "basic").strip() or "basic"
        lower_query = query.lower()
        tavily_payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": 5,
            "include_answer": "basic",
            "include_raw_content": False,
            "time_range": "day" if any(token in lower_query for token in ["hoy", "today", "dia", "día"]) else "week",
        }
        if any(token in lower_query for token in ["noticia", "noticias", "viral hoy", "ultima hora", "última hora"]):
            tavily_payload["topic"] = "news"
            tavily_payload["days"] = 7
        else:
            tavily_payload["topic"] = "general"
            if any(token in lower_query for token in ["mexico", "méxico", "latinoamerica", "latinoamérica"]):
                tavily_payload["country"] = "mexico"
        resp = requests.post(
            "https://api.tavily.com/search",
            json=tavily_payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        try:
            log.warning("radar_tavily_failed", query=query[:120], error=str(exc)[:200])
        except Exception:
            pass
        return {}


def _radar_rank_with_llm(candidates: list[dict], *, scope: str, intent: str) -> list[dict]:
    if not candidates or not os.environ.get("ANTHROPIC_API_KEY"):
        return candidates
    if scope == "global" and not _flag_enabled("CONTENT_FACTORY_RADAR_LLM_GLOBAL", default=False):
        return candidates
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=os.environ.get("CONTENT_FACTORY_RADAR_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1800,
            messages=[{"role": "user", "content": _radar_build_ranking_prompt(candidates, scope=scope, intent=intent)}],
        )
        ranked = _radar_parse_ranking_response(resp.content[0].text)
        return _radar_apply_llm_ranking(candidates, ranked)
    except Exception as exc:
        try:
            log.warning("radar_llm_ranking_failed", error=str(exc)[:200])
        except Exception:
            pass
        return candidates


def _radar_candidates_for_agent(
    agent: dict,
    *,
    market: str,
    language: str,
    category: str,
    intent: str,
    query_limit: int,
    limit: int,
) -> list[dict]:
    candidates = []
    for query in _radar_build_agent_queries(
        agent,
        market=market,
        language=language,
        category=category,
        intent=intent,
        max_queries=query_limit,
    ):
        result = _radar_search_tavily(query)
        candidates.extend(_radar_tavily_results_to_candidates(agent, query, result, limit=5, intent=intent))
    if not candidates:
        candidates = _radar_fallback_candidates_for_agent(agent, limit=limit, intent=intent)
    return _radar_rank_with_llm(candidates, scope="agent", intent=intent)[:limit]


def _radar_run_discovery(db, uid: str, params: dict, *, mode: str) -> dict:
    if params["scope"] == "agent":
        agent = _radar_agent_by_id(params["agentId"])
        if not agent:
            raise HTTPException(status_code=400, detail="invalid radar agentId")
        agents = [agent]
    elif params["scope"] == "news":
        agents = [_radar_agent_by_id(RADAR_NEWS_AGENT_ID)]
    else:
        agents = _radar_agent_catalog()
    agents = [agent for agent in agents if agent]
    if mode == "manual" and params["scope"] == "global":
        max_agents = max(
            1,
            min(
                len(agents),
                _safe_int(os.environ.get("CONTENT_FACTORY_RADAR_MANUAL_GLOBAL_AGENT_LIMIT"), 6),
            ),
        )
        priority = {agent_id: index for index, agent_id in enumerate(_RADAR_PRIORITY_AGENT_IDS)}
        agents = sorted(
            agents,
            key=lambda agent: (
                priority.get(agent.get("agentId"), len(priority) + 100),
                agent.get("name") or "",
            ),
        )[:max_agents]
        params = {**params, "queryLimit": min(params.get("queryLimit") or 1, 1)}

    existing_hashes, existing_titles = _radar_existing_sets(db, uid)
    all_items = []
    errors = []
    per_agent_limit = max(1, min(RADAR_MAX_AGENT_LIMIT, params["limit"]))
    for agent in agents:
        try:
            candidates = _radar_candidates_for_agent(
                agent,
                market=params["market"],
                language=params["language"],
                category=params["category"],
                intent=params["intent"],
                query_limit=params["queryLimit"],
                limit=per_agent_limit * 2,
            )
            filtered = _radar_dedupe_candidates(
                candidates,
                existing_hashes=existing_hashes,
                existing_title_keys=existing_titles,
                limit=per_agent_limit,
            )
            for item in filtered:
                existing_hashes.add(item["candidateHash"])
                existing_titles.add(_radar_canonical_title_key(item["agentId"], item["title"]))
            all_items.extend(filtered)
        except Exception as exc:
            errors.append({"agentId": agent.get("agentId"), "error": str(exc)[:160]})

    all_items = sorted(all_items, key=lambda item: item.get("editorialScore", 0), reverse=True)
    generated_at = datetime.now(timezone.utc)
    expires_at = generated_at + timedelta(seconds=RADAR_CACHE_TTL_SECONDS)
    cache_id = _radar_cache_key(
        scope=params["scope"],
        agent_id=params["agentId"] or "all",
        market=params["market"],
        language=params["language"],
        category=params["category"],
        window=params["window"],
        intent=params["intent"],
    )
    payload = {
        "runId": f"{cache_id}-{int(generated_at.timestamp())}",
        "cacheKey": cache_id,
        "mode": mode,
        "scope": params["scope"],
        "agentId": params["agentId"] or "",
        "intent": params["intent"],
        "radarIntent": params["intent"],
        "market": params["market"],
        "language": params["language"],
        "category": params["category"],
        "window": params["window"],
        "status": "ok" if all_items else "empty",
        "itemsCount": len(all_items),
        "items": all_items,
        "errors": errors,
        "generatedAt": generated_at,
        "expiresAt": expires_at,
        "createdAt": generated_at,
        "updatedAt": generated_at,
    }
    db.collection("radarRuns").document(cache_id).set(payload)
    return _radar_doc_to_public(cache_id, payload)


def _radar_cached_run(db, params: dict) -> dict | None:
    cache_id = _radar_cache_key(
        scope=params["scope"],
        agent_id=params["agentId"] or "all",
        market=params["market"],
        language=params["language"],
        category=params["category"],
        window=params["window"],
        intent=params["intent"],
    )
    snap = db.collection("radarRuns").document(cache_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if _radar_firestore_ts_expired(data.get("expiresAt")):
        return None
    public = _radar_doc_to_public(snap.id, data)
    public["cached"] = True
    return public


def _radar_find_candidate(db, uid: str, candidate_hash: str) -> tuple[dict | None, dict | None]:
    library_id = _radar_library_doc_id(uid, candidate_hash)
    lib_snap = db.collection("topicLibrary").document(library_id).get()
    if lib_snap.exists:
        data = lib_snap.to_dict() or {}
        candidate = data.get("candidate") or data
        return candidate, {"id": library_id, **data}

    for lib_doc in db.collection("topicLibrary").stream():
        data = lib_doc.to_dict() or {}
        if data.get("userId") not in {uid, "admin"}:
            continue
        if data.get("candidateHash") != candidate_hash:
            continue
        candidate = data.get("candidate") or data
        return candidate, {"id": lib_doc.id, **data}

    for run in db.collection("radarRuns").stream():
        data = run.to_dict() or {}
        for item in data.get("items") or []:
            if item.get("candidateHash") == candidate_hash:
                return item, None
    return None, None


def _radar_context_from_candidate(candidate: dict) -> dict:
    return _clean_radar_context_payload({
        "candidateHash": candidate.get("candidateHash"),
        "intent": candidate.get("intent") or candidate.get("radarIntent") or RADAR_DEFAULT_INTENT,
        "title": candidate.get("title") or candidate.get("headline"),
        "angle": candidate.get("angle"),
        "summary": candidate.get("summary"),
        "whyNow": candidate.get("whyNow"),
        "riskLevel": candidate.get("riskLevel"),
        "riskReason": candidate.get("riskReason"),
        "recommendedFormat": candidate.get("recommendedFormat"),
        "sources": candidate.get("sources") or [],
    })


def _radar_upsert_library_candidate(db, firestore, uid: str, candidate: dict, *, status: str = "saved") -> dict:
    doc_id = _radar_library_doc_id(uid, candidate["candidateHash"])
    ref = db.collection("topicLibrary").document(doc_id)
    snap = ref.get()
    existing = snap.to_dict() if snap.exists else {}
    next_status = existing.get("status") if existing.get("status") == "project_created" else status
    payload = {
        "userId": uid,
        "agentId": candidate.get("agentId"),
        "agentName": candidate.get("agentName"),
        "agentFile": candidate.get("agentFile"),
        "platform": candidate.get("platform") or "youtube",
        "format": candidate.get("format") or "",
        "intent": candidate.get("intent") or candidate.get("radarIntent") or RADAR_DEFAULT_INTENT,
        "title": candidate.get("title"),
        "angle": candidate.get("angle"),
        "summary": candidate.get("summary"),
        "sources": candidate.get("sources") or [],
        "scores": candidate.get("scores") or {},
        "editorialScore": candidate.get("editorialScore") or 0,
        "risk": {
            "level": candidate.get("riskLevel") or "low",
            "reason": candidate.get("riskReason") or "",
        },
        "recommendedFormat": candidate.get("recommendedFormat") or "youtube_long",
        "status": next_status,
        "candidateHash": candidate.get("candidateHash"),
        "candidate": candidate,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }
    if not existing:
        payload["createdAt"] = firestore.SERVER_TIMESTAMP
    ref.set(payload, merge=True)
    return {"itemId": doc_id, **payload, "createdAt": _serialize_firestore_value(payload.get("createdAt")), "updatedAt": None}


def _radar_project_payload_from_candidate(candidate: dict) -> dict:
    agent_id = candidate.get("agentId")
    payload = {
        "title": _radar_compact_text(candidate.get("angle") or candidate.get("title"), 180),
        "agentId": agent_id,
        "agentFile": candidate.get("agentFile") or f"{agent_id}.md",
        "platform": candidate.get("platform") or ("tiktok" if agent_id in _TIKTOK_AGENT_IDS else "youtube"),
        "radarContext": _radar_context_from_candidate(candidate),
    }
    if agent_id in _TIKTOK_AGENT_IDS:
        payload.setdefault("durationProfile", "90s")
        category = str(candidate.get("category") or "").lower()
        payload["sourceGenre"] = category if category in _TIKTOK_SOURCE_GENRES else "psychology"
    if agent_id == "agent_meditacion_larga":
        payload.setdefault("durationProfile", "60m")
    return payload


def _library_public_item(doc_id: str, data: dict) -> dict:
    risk = data.get("risk") or {}
    return {
        "itemId": doc_id,
        "type": "idea",
        "status": data.get("status") or "suggested",
        "agentId": data.get("agentId") or "",
        "agentName": data.get("agentName") or "",
        "title": data.get("title") or "",
        "angle": data.get("angle") or "",
        "summary": data.get("summary") or "",
        "intent": data.get("intent") or data.get("radarIntent") or RADAR_DEFAULT_INTENT,
        "radarIntent": data.get("intent") or data.get("radarIntent") or RADAR_DEFAULT_INTENT,
        "candidateHash": data.get("candidateHash") or "",
        "editorialScore": data.get("editorialScore") or (data.get("scores") or {}).get("overall") or 0,
        "riskLevel": risk.get("level") or data.get("riskLevel") or "low",
        "riskReason": risk.get("reason") or data.get("riskReason") or "",
        "recommendedFormat": data.get("recommendedFormat") or "youtube_long",
        "sources": data.get("sources") or [],
        "projectId": data.get("projectId") or "",
        "updatedAt": _serialize_firestore_value(data.get("updatedAt") or data.get("createdAt")),
    }


def _library_public_project(doc_id: str, data: dict) -> dict:
    shorts = data.get("shorts") or []
    return {
        "itemId": doc_id,
        "type": "project",
        "status": data.get("status") or "draft",
        "agentId": data.get("agentId") or "",
        "agentName": "",
        "title": data.get("title") or "",
        "format": data.get("format") or "",
        "platform": data.get("platform") or "youtube",
        "projectId": doc_id,
        "videoUrl": data.get("videoUrl") or "",
        "hasVideo": bool(data.get("videoUrl") or data.get("videoPath")),
        "shortsCount": len(shorts) if isinstance(shorts, list) else 0,
        "createdAt": _serialize_firestore_value(data.get("createdAt")),
        "updatedAt": _serialize_firestore_value(data.get("completedAt") or data.get("updatedAt") or data.get("createdAt")),
    }


KNOWLEDGE_UPLOAD_DIR = Path(os.environ.get("KNOWLEDGE_UPLOAD_DIR", str(BASE_DIR / "output" / "knowledge_uploads")))
KNOWLEDGE_MAX_UPLOAD_BYTES = int(os.environ.get("KNOWLEDGE_MAX_UPLOAD_BYTES", str(80 * 1024 * 1024)))
KNOWLEDGE_SYNC_MAX_POINTS = int(os.environ.get("KNOWLEDGE_SYNC_MAX_POINTS", "300000"))
KNOWLEDGE_MAX_BOOKS_RESPONSE = int(os.environ.get("KNOWLEDGE_MAX_BOOKS_RESPONSE", "1000"))
KNOWLEDGE_ALLOWED_EXTENSIONS = {".pdf", ".epub"}


def _knowledge_is_enabled() -> bool:
    return _flag_enabled("CONTENT_FACTORY_KNOWLEDGE_ENABLED", default=True)


def _knowledge_require_admin(request: Request, *, allow_local: bool = False) -> dict:
    if not _knowledge_is_enabled():
        raise HTTPException(status_code=404, detail="knowledge disabled")
    if not _flag_enabled("CONTENT_FACTORY_KNOWLEDGE_ADMIN_ONLY", default=True):
        return _require_principal(request, allow_admin=True, allow_local=allow_local)
    return _require_admin(request, allow_local=allow_local)


def _knowledge_collection() -> str:
    return (os.environ.get("QDRANT_KNOWLEDGE_COLLECTION") or KNOWLEDGE_DEFAULT_COLLECTION).strip()


def _knowledge_config_status() -> dict:
    cfg = KnowledgeConfig.from_env()
    return {
        "qdrantUrlConfigured": bool(cfg.qdrant_url),
        "apiKeyConfigured": bool(cfg.api_key),
        "collection": cfg.collection,
        "embeddingModel": cfg.embedding_model,
    }


def _knowledge_client() -> QdrantKnowledgeClient:
    return QdrantKnowledgeClient()


def _knowledge_public_book(doc_id: str, data: dict) -> dict:
    blob_type = data.get("blobType") or data.get("blob_type") or ""
    return {
        "bookId": data.get("bookId") or doc_id,
        "title": data.get("title") or "Unknown",
        "category": data.get("category") or "General",
        "collection": data.get("collection") or _knowledge_collection(),
        "chunksCount": _safe_int(data.get("chunksCount"), 0),
        "sample": data.get("sample") or "",
        "source": data.get("source") or "",
        "blobType": blob_type,
        "fileType": "epub" if "epub" in str(blob_type).lower() else "pdf" if "pdf" in str(blob_type).lower() else "",
        "status": data.get("status") or "indexed",
        "firstSeenAt": _serialize_firestore_value(data.get("firstSeenAt")),
        "lastSyncedAt": _serialize_firestore_value(data.get("lastSyncedAt")),
        "updatedAt": _serialize_firestore_value(data.get("updatedAt")),
    }


def _knowledge_public_job(doc_id: str, data: dict) -> dict:
    blob_type = data.get("blobType") or data.get("blob_type") or ""
    return {
        "jobId": data.get("jobId") or doc_id,
        "fileName": data.get("fileName") or "",
        "fileType": data.get("fileType") or ("epub" if "epub" in str(blob_type).lower() else "pdf" if "pdf" in str(blob_type).lower() else ""),
        "blobType": blob_type,
        "title": data.get("title") or "",
        "category": data.get("category") or "",
        "collection": data.get("collection") or _knowledge_collection(),
        "status": data.get("status") or "queued",
        "progress": _safe_int(data.get("progress"), 0),
        "chunksCount": _safe_int(data.get("chunksCount"), 0),
        "error": data.get("error") or "",
        "duplicate": bool(data.get("duplicate")),
        "createdAt": _serialize_firestore_value(data.get("createdAt")),
        "completedAt": _serialize_firestore_value(data.get("completedAt")),
        "updatedAt": _serialize_firestore_value(data.get("updatedAt")),
    }


def _knowledge_book_doc(db, collection: str, title: str, category: str):
    book_id = _knowledge_book_id(collection, title, category)
    return book_id, db.collection("knowledgeBooks").document(book_id)


def _knowledge_sync_index(db, firestore_module) -> dict:
    client = _knowledge_client()
    info = client.collection_info()
    books = _knowledge_scan_book_index(client, page_limit=512, max_points=KNOWLEDGE_SYNC_MAX_POINTS)
    batch = db.batch()
    written = 0
    now = firestore_module.SERVER_TIMESTAMP
    for book_id, item in books.items():
        batch.set(
            db.collection("knowledgeBooks").document(book_id),
            {
                **item,
                "status": "indexed",
                "firstSeenAt": now,
                "lastSyncedAt": now,
                "updatedAt": now,
            },
            merge=True,
        )
        written += 1
        if written % 400 == 0:
            batch.commit()
            batch = db.batch()
    if written % 400:
        batch.commit()

    db.collection("knowledgeMeta").document("summary").set({
        "collection": client.config.collection,
        "pointsCount": info.get("points_count"),
        "indexedVectorsCount": info.get("indexed_vectors_count"),
        "status": info.get("status"),
        "booksCount": len(books),
        "lastSyncedAt": now,
        "updatedAt": now,
    }, merge=True)
    categories = sorted({item.get("category") or "General" for item in books.values()})
    return {
        "ok": True,
        "collection": client.config.collection,
        "booksCount": len(books),
        "categories": categories,
        "pointsCount": info.get("points_count") or 0,
        "indexedVectorsCount": info.get("indexed_vectors_count") or 0,
        "status": info.get("status") or "",
    }


def _knowledge_list_books(db, *, category: str = "", query: str = "", limit: int = 80) -> list[dict]:
    limit = max(1, min(KNOWLEDGE_MAX_BOOKS_RESPONSE, _safe_int(limit, 80)))
    text = (query or "").strip().lower()
    collection = _knowledge_collection()
    books: list[dict] = []
    for doc in db.collection("knowledgeBooks").stream():
        data = doc.to_dict() or {}
        if data.get("collection") and data.get("collection") != collection:
            continue
        if category and category != "all" and data.get("category") != category:
            continue
        haystack = " ".join([
            str(data.get("title") or ""),
            str(data.get("category") or ""),
            str(data.get("sample") or ""),
        ]).lower()
        if text and text not in haystack:
            continue
        books.append(_knowledge_public_book(doc.id, data))
    books.sort(key=lambda item: (-_safe_int(item.get("chunksCount"), 0), item.get("title", "").lower()))
    return books[:limit]


def _knowledge_chunk_from_point(point: dict) -> dict:
    payload = point.get("payload") or {}
    return {
        "pointId": str(point.get("id") or ""),
        "score": point.get("score"),
        "title": _knowledge_payload_book_title(payload),
        "category": _knowledge_payload_category(payload),
        "blobType": _knowledge_payload_blob_type(payload),
        "content": _knowledge_payload_content(payload, limit=900),
        "metadata": payload.get("metadata") or {},
    }


def _knowledge_search(query: str, *, category: str = "", book_title: str = "", limit: int = 6) -> dict:
    clean = re.sub(r"\s+", " ", str(query or "")).strip()
    if len(clean) < 3:
        raise HTTPException(status_code=400, detail="query too short")
    client = _knowledge_client()
    vector = _knowledge_embed_texts([clean], model=client.config.embedding_model)[0]
    items = client.search(
        vector,
        limit=max(1, min(KNOWLEDGE_MAX_SEARCH_LIMIT, _safe_int(limit, 6))),
        payload_filter=_knowledge_search_filter(category if category != "all" else "", book_title),
    )
    return {
        "ok": True,
        "query": clean,
        "collection": client.config.collection,
        "items": [_knowledge_chunk_from_point(item) for item in items],
    }


def _knowledge_update_job(db, firestore_module, job_id: str, **updates):
    updates.setdefault("updatedAt", firestore_module.SERVER_TIMESTAMP)
    db.collection("knowledgeIngestJobs").document(job_id).set(updates, merge=True)


def _run_knowledge_ingest_job(job_id: str) -> dict:
    _ensure_firebase_initialized()
    from firebase_admin import firestore

    db = firestore.client()
    ref = db.collection("knowledgeIngestJobs").document(job_id)
    snap = ref.get()
    if not snap.exists:
        raise RuntimeError(f"knowledge ingest job not found: {job_id}")
    job = snap.to_dict() or {}
    title = re.sub(r"\s+", " ", str(job.get("title") or "")).strip()
    category = re.sub(r"\s+", " ", str(job.get("category") or "General")).strip() or "General"
    path = Path(str(job.get("filePath") or ""))
    blob_type = str(job.get("blobType") or _knowledge_document_blob_type(path, job.get("fileName") or "")).strip()
    file_type = "epub" if "epub" in blob_type.lower() else "pdf" if "pdf" in blob_type.lower() else "file"
    reindex = bool(job.get("reindex"))
    client = _knowledge_client()

    try:
        _knowledge_update_job(db, firestore, job_id, status="extracting", progress=10, error="")
        if not path.exists():
            raise KnowledgeError("archivo no encontrado")

        exact_filter = _knowledge_book_filter(title, category)
        existing_count = client.count(exact_filter)
        book_id, book_ref = _knowledge_book_doc(db, client.config.collection, title, category)
        if existing_count > 0 and not reindex:
            book_ref.set({
                "bookId": book_id,
                "title": title,
                "category": category,
                "collection": client.config.collection,
                "chunksCount": existing_count,
                "source": "qdrant",
                "blobType": blob_type,
                "fileType": file_type,
                "status": "indexed",
                "lastSyncedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            _knowledge_update_job(
                db,
                firestore,
                job_id,
                status="completed",
                progress=100,
                chunksCount=existing_count,
                duplicate=True,
                completedAt=firestore.SERVER_TIMESTAMP,
            )
            return {"ok": True, "jobId": job_id, "duplicate": True, "chunksCount": existing_count}

        text = _knowledge_extract_document_text(path, blob_type=blob_type)
        if not text:
            raise KnowledgeError("archivo sin texto extraible")
        _knowledge_update_job(db, firestore, job_id, status="chunking", progress=28)
        chunks = _knowledge_chunk_text(text, chunk_size=1200, overlap=200)
        if not chunks:
            raise KnowledgeError("archivo sin chunks validos")

        if reindex and existing_count > 0:
            client.delete_by_filter(exact_filter)

        all_points = []
        for start in range(0, len(chunks), 64):
            batch = chunks[start:start + 64]
            _knowledge_update_job(
                db,
                firestore,
                job_id,
                status="embedding",
                progress=35 + int((start / max(1, len(chunks))) * 35),
                chunksCount=len(chunks),
            )
            vectors = _knowledge_embed_texts(batch, model=client.config.embedding_model)
            all_points.extend(_knowledge_build_points(
                collection=client.config.collection,
                title=title,
                category=category,
                chunks=batch,
                vectors=vectors,
                source=job.get("fileName") or path.name,
                blob_type=blob_type,
                start_index=start,
            ))

        _knowledge_update_job(db, firestore, job_id, status="upserting", progress=78, chunksCount=len(chunks))
        client.upsert_points(all_points)
        book_ref.set({
            "bookId": book_id,
            "title": title,
            "category": category,
            "collection": client.config.collection,
            "chunksCount": len(chunks),
            "sample": chunks[0][:320],
            "source": job.get("fileName") or path.name,
            "blobType": blob_type,
            "fileType": file_type,
            "status": "indexed",
            "firstSeenAt": firestore.SERVER_TIMESTAMP,
            "lastSyncedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        _knowledge_update_job(
            db,
            firestore,
            job_id,
            status="completed",
            progress=100,
            chunksCount=len(chunks),
            completedAt=firestore.SERVER_TIMESTAMP,
        )
        return {"ok": True, "jobId": job_id, "chunksCount": len(chunks)}
    except Exception as exc:
        _knowledge_update_job(
            db,
            firestore,
            job_id,
            status="failed",
            error=str(exc)[:500],
            completedAt=firestore.SERVER_TIMESTAMP,
        )
        raise


def _enqueue_knowledge_ingest(job_id: str, background_tasks: BackgroundTasks) -> str:
    try:
        from worker_tasks import ingest_knowledge_pdf
        task = ingest_knowledge_pdf.delay(job_id)
        return getattr(task, "id", "") or "celery"
    except Exception as exc:
        print(f"   [knowledge] Celery enqueue failed, using background task: {exc}", flush=True)
        background_tasks.add_task(_run_knowledge_ingest_job, job_id)
        return "background"


@app.post("/thumbnails/build/{project_id}")
def thumbnails_build(project_id: str, request: Request, force: bool = False, premium: bool | None = None):
    """
    Genera thumbnails on-demand para un proyecto completado (backfill).
    Idempotency: si ya hay thumbnails y no se pasa ?force=true, devuelve los
    existentes sin regenerar (evita doble gasto accidental).
    """
    _require_project_access(request, project_id, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()

        # Idempotency: skip si ya hay thumbnails. ?force=true para regenerar.
        existing = data.get("thumbnails") or []
        if existing and not force and len(existing) >= 3:
            return {
                "thumbnails": existing,
                "count": len(existing),
                "cached": True,
                "message": "Thumbnails ya existen; usar ?force=true para regenerar.",
            }

        folder = data.get("videoFolder") or ""
        title = data.get("title") or ""
        agent_id = data.get("agentId") or ""
        if not folder:
            return JSONResponse(status_code=400, content={"error": "project has no videoFolder"})
        video_dir = Path(f"/app/output/videos/{folder}")
        if not video_dir.is_dir():
            return JSONResponse(status_code=404, content={"error": "video folder not on disk"})

        results = build_thumbnails_for_project(video_dir, project_id, title, agent_id=agent_id, premium=premium)
        if results:
            doc_ref.update({"thumbnails": results})
        return {"thumbnails": results, "count": len(results), "cached": False}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/shorts/build/{project_id}")
def shorts_build(project_id: str, request: Request):
    """
    Genera shorts on-demand para un proyecto ya completado.
    Útil para backfill de proyectos producidos antes de Sprint 2.1.
    """
    _require_project_access(request, project_id, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()
        folder = data.get("videoFolder") or ""
        if not folder:
            return JSONResponse(status_code=400, content={"error": "project has no videoFolder"})
        video_dir = Path(f"/app/output/videos/{folder}")
        if not video_dir.is_dir():
            return JSONResponse(status_code=404, content={"error": "video folder not on disk"})

        results = build_shorts_for_project(video_dir, project_id)
        if results:
            db.collection("projects").document(project_id).update({"shorts": results})
        return {"shorts": results, "count": len(results)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/factcheck/run/{project_id}")
def factcheck_run(project_id: str, request: Request, force: bool = False):
    """
    Corre fact-checking del guion del proyecto on-demand.
    Util para backfill o re-check tras editar el guion.

    Idempotency: si ya hay factCheck reciente (<1h) y el script no cambió,
    devuelve el cached. Pasar ?force=true para forzar re-check.
    """
    _require_project_access(request, project_id, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()
        script_text = (data.get("script") or {}).get("plain") or ""
        if not script_text:
            return JSONResponse(
                status_code=400,
                content={"error": "project has no script.plain to fact-check"},
            )

        # Idempotency: skip si hay factCheck reciente sobre el mismo script.
        # Comparamos hash del script para detectar si fue editado.
        import hashlib
        script_hash = hashlib.sha256(script_text.encode("utf-8")).hexdigest()[:16]
        existing = data.get("factCheck") or {}
        existing_hash = existing.get("scriptHash")
        existing_at = existing.get("checkedAt")
        if (
            not force
            and existing_hash == script_hash
            and existing_at and hasattr(existing_at, "timestamp")
        ):
            age = datetime.now(timezone.utc).timestamp() - existing_at.timestamp()
            if age < 3600:  # < 1 hora
                return {**existing, "cached": True, "age_sec": int(age)}

        result = fact_check_script(script_text, topic_hint=data.get("title", ""))
        result["scriptHash"] = script_hash
        result["checkedAt"] = firestore.SERVER_TIMESTAMP
        doc_ref.update({"factCheck": result})
        # firestore.SERVER_TIMESTAMP no es serializable directo en JSON respuesta
        result.pop("checkedAt", None)
        return {**result, "cached": False}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/moderation/check/{project_id}")
def moderation_check(project_id: str, request: Request):
    """
    Corre moderacion del guion del proyecto y guarda el resultado en Firestore.
    Util para:
      - Backfill de proyectos viejos sin moderacion
      - Re-check despues de que el usuario edita el guion manualmente
    """
    _require_project_access(request, project_id, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})
        script_text = (doc.to_dict().get("script") or {}).get("plain") or ""
        if not script_text:
            return JSONResponse(
                status_code=400,
                content={"error": "project has no script.plain to moderate"},
            )
        result = check_content_moderation(script_text)
        db.collection("projects").document(project_id).update({"moderation": result})
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/recommend-agent")
async def recommend_agent(request: Request):
    """
    Dado un tema/idea de video del usuario, devuelve los 3 agentes más adecuados
    en orden de mejor a peor match. Cada uno con score (0-100) y razón corta.
    """
    _require_principal(request)
    try:
        data = await request.json()
        topic = (data.get("topic") or "").strip()
        if len(topic) < 5:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={"error": "topic too short (min 5 chars)"},
            )

        prompt = (
            f"Tienes este catálogo de agentes especializados (cada uno con un id y descripción):\n"
            f"{_AGENT_CATALOG}\n\n"
            f'El usuario quiere hacer un video documental sobre: "{topic}"\n\n'
            f"Responde EXCLUSIVAMENTE con un JSON array de los 3 mejores agentes, "
            f"ordenados de mejor a peor match. Sin texto adicional, sin markdown, solo el JSON.\n"
            f"Formato exacto:\n"
            f'[\n'
            f'  {{"agent_id": "agent_xxx", "score": 95, "reason": "frase corta en español"}},\n'
            f'  {{"agent_id": "agent_xxx", "score": 80, "reason": "frase corta en español"}},\n'
            f'  {{"agent_id": "agent_xxx", "score": 70, "reason": "frase corta en español"}}\n'
            f"]\n"
            f"Reglas: score 0-100. Reason en español, máximo 12 palabras, explica por qué encaja."
        )

        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        # Por si el modelo envuelve en markdown a pesar de la instrucción
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0].strip()

        recommendations = json.loads(text)
        if not isinstance(recommendations, list) or not recommendations:
            raise ValueError("respuesta sin recomendaciones")

        return {
            "recommendations": recommendations[:3],
            "tokens_used": resp.usage.input_tokens + resp.usage.output_tokens,
        }
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": str(e)[:200], "recommendations": []},
        )


@app.get("/knowledge/summary")
def knowledge_summary(request: Request):
    _knowledge_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        config = _knowledge_config_status()
        qdrant = {}
        try:
            info = _knowledge_client().collection_info()
            qdrant = {
                "ok": True,
                "status": info.get("status"),
                "pointsCount": info.get("points_count") or 0,
                "indexedVectorsCount": info.get("indexed_vectors_count") or 0,
                "segmentsCount": info.get("segments_count") or 0,
            }
        except Exception as exc:
            qdrant = {"ok": False, "error": str(exc)[:220]}

        books = _knowledge_list_books(db, limit=KNOWLEDGE_MAX_BOOKS_RESPONSE)
        categories = sorted({book.get("category") or "General" for book in books})
        meta_snap = db.collection("knowledgeMeta").document("summary").get()
        meta = meta_snap.to_dict() if meta_snap.exists else {}
        recent_jobs = []
        try:
            for doc in db.collection("knowledgeIngestJobs").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(5).stream():
                recent_jobs.append(_knowledge_public_job(doc.id, doc.to_dict() or {}))
        except Exception:
            pass
        return {
            "ok": True,
            "config": config,
            "qdrant": qdrant,
            "collection": config["collection"],
            "booksCount": max(len(books), _safe_int(meta.get("booksCount"), 0)),
            "chunksCount": sum(_safe_int(book.get("chunksCount"), 0) for book in books),
            "categories": categories,
            "lastSyncedAt": _serialize_firestore_value(meta.get("lastSyncedAt")),
            "recentJobs": recent_jobs,
        }
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220]})


@app.post("/knowledge/sync-index")
async def knowledge_sync_index(request: Request):
    _knowledge_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        result = await run_in_threadpool(_knowledge_sync_index, db, firestore)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220]})


@app.get("/knowledge/books")
def knowledge_books(request: Request, category: str = "", q: str = "", limit: int = 80):
    _knowledge_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        books = _knowledge_list_books(db, category=category, query=q, limit=limit)
        return {"ok": True, "books": books, "count": len(books)}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220], "books": []})


@app.get("/knowledge/books/{book_id}")
def knowledge_book_detail(book_id: str, request: Request):
    _knowledge_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        snap = db.collection("knowledgeBooks").document(book_id).get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="book not found")
        return {"ok": True, "book": _knowledge_public_book(snap.id, snap.to_dict() or {})}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220]})


@app.get("/knowledge/books/{book_id}/chunks")
def knowledge_book_chunks(book_id: str, request: Request, limit: int = 12, cursor: str = ""):
    _knowledge_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        snap = db.collection("knowledgeBooks").document(book_id).get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="book not found")
        book = snap.to_dict() or {}
        client = _knowledge_client()
        result = client.scroll(
            limit=max(1, min(50, _safe_int(limit, 12))),
            offset=cursor or None,
            payload_filter=_knowledge_book_filter(book.get("title") or "", book.get("category") or ""),
            with_payload=True,
        )
        points = result.get("points") or []
        return {
            "ok": True,
            "book": _knowledge_public_book(snap.id, book),
            "chunks": [_knowledge_chunk_from_point(point) for point in points],
            "nextCursor": result.get("next_page_offset") or "",
        }
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220], "chunks": []})


@app.post("/knowledge/search")
async def knowledge_search(request: Request):
    _knowledge_require_admin(request)
    try:
        body = await request.json()
        result = await run_in_threadpool(
            _knowledge_search,
            body.get("query") or "",
            category=str(body.get("category") or ""),
            book_title=str(body.get("bookTitle") or body.get("book_title") or ""),
            limit=_safe_int(body.get("limit"), 6),
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220], "items": []})


@app.post("/knowledge/ingest/file")
@app.post("/knowledge/ingest/pdf")
async def knowledge_ingest_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("General"),
    reindex: bool = Form(False),
):
    principal = _knowledge_require_admin(request)
    clean_title = re.sub(r"\s+", " ", str(title or "")).strip()
    clean_category = re.sub(r"\s+", " ", str(category or "General")).strip() or "General"
    if len(clean_title) < 2:
        raise HTTPException(status_code=400, detail="title required")
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in KNOWLEDGE_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="solo PDF o EPUB")
    blob_type = _knowledge_document_blob_type(filename, filename)
    file_type = "epub" if suffix == ".epub" else "pdf"

    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        job_ref = db.collection("knowledgeIngestJobs").document()
        job_id = job_ref.id
        folder = KNOWLEDGE_UPLOAD_DIR / job_id
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / filename
        total = 0
        with file_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > KNOWLEDGE_MAX_UPLOAD_BYTES:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
                    raise HTTPException(status_code=413, detail="PDF demasiado grande")
                out.write(chunk)

        job_ref.set({
            "jobId": job_id,
            "fileName": filename,
            "filePath": str(file_path),
            "fileSize": total,
            "fileType": file_type,
            "blobType": blob_type,
            "title": clean_title,
            "category": clean_category,
            "collection": _knowledge_collection(),
            "status": "queued",
            "progress": 0,
            "chunksCount": 0,
            "error": "",
            "reindex": bool(reindex),
            "requestedBy": principal.get("uid") or "admin",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        task_id = _enqueue_knowledge_ingest(job_id, background_tasks)
        job_ref.set({"taskId": task_id, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
        return {
            "ok": True,
            "job": _knowledge_public_job(job_id, {
                "jobId": job_id,
                "fileName": filename,
                "fileType": file_type,
                "blobType": blob_type,
                "title": clean_title,
                "category": clean_category,
                "status": "queued",
                "progress": 0,
            }),
            "taskId": task_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220]})


@app.get("/knowledge/ingest/{job_id}")
def knowledge_ingest_status(job_id: str, request: Request):
    _knowledge_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        snap = db.collection("knowledgeIngestJobs").document(job_id).get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="job not found")
        return {"ok": True, "job": _knowledge_public_job(snap.id, snap.to_dict() or {})}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:220]})


@app.post("/radar/run")
async def radar_run(request: Request):
    principal = _radar_require_admin(request)
    data = await request.json()
    params = _radar_request_defaults(data)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        if not params["force"]:
            cached = await run_in_threadpool(_radar_cached_run, db, params)
            if cached:
                return cached
        return await run_in_threadpool(_radar_run_discovery, db, principal["uid"], params, mode="manual")
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:200], "items": []})


@app.get("/radar/latest")
def radar_latest(
    request: Request,
    scope: str = "global",
    agentId: str = "",
    intent: str = RADAR_DEFAULT_INTENT,
    market: str = RADAR_DEFAULT_MARKET,
    language: str = RADAR_DEFAULT_LANGUAGE,
    category: str = RADAR_DEFAULT_CATEGORY,
    window: str = RADAR_DEFAULT_WINDOW,
):
    _radar_require_admin(request)
    params = _radar_request_defaults({
        "scope": scope,
        "agentId": agentId,
        "intent": intent,
        "market": market,
        "language": language,
        "category": category,
        "window": window,
    })
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        cached = _radar_cached_run(db, params)
        if cached:
            return cached
        return {
            "runId": "",
            "cacheKey": _radar_cache_key(
                scope=params["scope"],
                agent_id=params["agentId"] or "all",
                market=params["market"],
                language=params["language"],
                category=params["category"],
                window=params["window"],
                intent=params["intent"],
            ),
            "scope": params["scope"],
            "agentId": params["agentId"],
            "intent": params["intent"],
            "radarIntent": params["intent"],
            "market": params["market"],
            "language": params["language"],
            "category": params["category"],
            "window": params["window"],
            "status": "empty",
            "items": [],
            "itemsCount": 0,
            "cached": False,
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:200], "items": []})


@app.post("/radar/candidates/{candidate_hash}/save")
async def radar_candidate_save(candidate_hash: str, request: Request):
    principal = _radar_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        candidate, _existing = _radar_find_candidate(db, principal["uid"], candidate_hash)
        if not candidate:
            raise HTTPException(status_code=404, detail="candidate not found")
        item = _radar_upsert_library_candidate(db, firestore, principal["uid"], candidate, status="saved")
        return {"ok": True, "item": _library_public_item(item["itemId"], item)}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:200]})


@app.post("/radar/candidates/{candidate_hash}/create-project")
async def radar_candidate_create_project(candidate_hash: str, request: Request, background_tasks: BackgroundTasks):
    principal = _radar_require_admin(request)
    body = await request.json()
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        candidate, existing = _radar_find_candidate(db, principal["uid"], candidate_hash)
        if not candidate:
            raise HTTPException(status_code=404, detail="candidate not found")
        library_doc_id = _radar_library_doc_id(principal["uid"], candidate_hash)
        existing_project_id = (existing or {}).get("projectId")
        if existing_project_id:
            return {"ok": True, "projectId": existing_project_id, "existing": True}
        if candidate.get("riskLevel") == "high" and not bool(body.get("allowHighRisk")):
            raise HTTPException(status_code=409, detail="high risk candidate requires explicit review")

        _radar_upsert_library_candidate(db, firestore, principal["uid"], candidate, status="saved")
        library_ref = db.collection("topicLibrary").document(library_doc_id)

        @firestore.transactional
        def _claim_create(transaction):
            snap = library_ref.get(transaction=transaction)
            data = snap.to_dict() if snap.exists else {}
            if data.get("projectId"):
                return data["projectId"]
            if data.get("creatingProject"):
                raise HTTPException(status_code=409, detail="project creation already in progress")
            transaction.set(library_ref, {
                "creatingProject": True,
                "createProjectRequestedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            return None

        claimed_project_id = _claim_create(db.transaction())
        if claimed_project_id:
            return {"ok": True, "projectId": claimed_project_id, "existing": True}

        project_payload = _validate_project_payload(_radar_project_payload_from_candidate(candidate))
        radar_context = _radar_context_from_candidate(candidate)
        try:
            result = _create_project_with_credit(
                principal=principal,
                payload=project_payload,
                background_tasks=background_tasks,
                project_extra={
                    "radar": {
                        "candidateHash": candidate_hash,
                        "source": "radar",
                        "riskLevel": candidate.get("riskLevel") or "low",
                        "recommendedFormat": candidate.get("recommendedFormat") or "",
                        "createdFromRadarAt": firestore.SERVER_TIMESTAMP,
                    },
                    "factCheckRequired": candidate.get("agentId") == RADAR_NEWS_AGENT_ID or candidate.get("riskLevel") != "low",
                },
                credit_metadata={"source": "radar", "candidateHash": candidate_hash},
                ledger_reason="radar_project_create",
            )
        except Exception:
            try:
                library_ref.set({
                    "creatingProject": False,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }, merge=True)
            except Exception:
                pass
            raise
        db.collection("topicLibrary").document(library_doc_id).set({
            "status": "project_created",
            "projectId": result["projectId"],
            "creatingProject": False,
            "radarContext": radar_context,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        return {**result, "candidateHash": candidate_hash}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:200]})


@app.get("/library/agents")
def library_agents(request: Request):
    principal = _radar_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        agents = {agent["agentId"]: {**agent, "ideas": [], "projects": [], "gaps": []} for agent in _radar_agent_catalog()}
        for doc in db.collection("topicLibrary").stream():
            data = doc.to_dict() or {}
            if data.get("userId") not in {principal["uid"], "admin"}:
                continue
            aid = data.get("agentId") or ""
            if aid not in agents:
                agents[aid] = {
                    "agentId": aid,
                    "name": data.get("agentName") or aid.replace("agent_", "").replace("_", " "),
                    "description": "",
                    "category": "",
                    "platform": "youtube",
                    "format": "",
                    "promptFile": f"{aid}.md",
                    "ideas": [],
                    "projects": [],
                    "gaps": [],
                }
            agents[aid]["ideas"].append(_library_public_item(doc.id, data))

        for doc in db.collection("projects").where("userId", "==", principal["uid"]).stream():
            data = doc.to_dict() or {}
            aid = data.get("agentId") or ""
            if aid not in agents:
                agents[aid] = {
                    "agentId": aid,
                    "name": aid.replace("agent_", "").replace("_", " "),
                    "description": "",
                    "category": "",
                    "platform": data.get("platform") or "youtube",
                    "format": data.get("format") or "",
                    "promptFile": data.get("agentFile") or f"{aid}.md",
                    "ideas": [],
                    "projects": [],
                    "gaps": [],
                }
            agents[aid]["projects"].append(_library_public_project(doc.id, data))

        groups = []
        for group in agents.values():
            group["ideas"].sort(key=lambda item: item.get("editorialScore", 0), reverse=True)
            group["projects"].sort(key=lambda item: item.get("updatedAt") or "", reverse=True)
            saved_without_project = [i for i in group["ideas"] if i.get("status") in {"saved", "suggested"} and not i.get("projectId")]
            completed_without_shorts = [
                p for p in group["projects"]
                if p.get("status") == "completed" and p.get("platform") != "tiktok" and not p.get("shortsCount")
            ]
            if saved_without_project:
                group["gaps"].append(f"{len(saved_without_project)} idea(s) listas sin proyecto")
            if completed_without_shorts:
                group["gaps"].append(f"{len(completed_without_shorts)} video(s) sin Shorts registrados")
            if not group["projects"]:
                group["gaps"].append("Sin material creado todavia")
            group["counts"] = {
                "ideas": len(group["ideas"]),
                "projects": len(group["projects"]),
                "completed": sum(1 for p in group["projects"] if p.get("status") == "completed"),
                "saved": sum(1 for i in group["ideas"] if i.get("status") == "saved"),
            }
            if group["ideas"] or group["projects"]:
                groups.append(group)
        groups.sort(key=lambda item: (item["counts"]["ideas"] + item["counts"]["projects"], item.get("name", "")), reverse=True)
        return {"ok": True, "agents": groups, "totalAgents": len(groups)}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:200], "agents": []})


@app.post("/library/items/{item_id}/archive")
def library_archive_item(item_id: str, request: Request):
    principal = _radar_require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        ref = db.collection("topicLibrary").document(item_id)
        snap = ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="library item not found")
        data = snap.to_dict() or {}
        if data.get("userId") not in {principal["uid"], "admin"}:
            raise HTTPException(status_code=403, detail="library item access denied")
        ref.update({"status": "archived", "updatedAt": firestore.SERVER_TIMESTAMP})
        return {"ok": True, "itemId": item_id, "status": "archived"}
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)[:200]})


@app.post("/admin/radar/refresh-nightly")
async def radar_refresh_nightly(request: Request):
    principal = _radar_require_admin(request, allow_local=True)
    try:
        body = await request.json()
    except Exception:
        body = {}
    params = _radar_request_defaults({
        **(body or {}),
        "scope": "global",
        "limit": min(RADAR_MAX_AGENT_LIMIT, _safe_int((body or {}).get("limit"), RADAR_MAX_AGENT_LIMIT)),
        "queryLimit": min(2, _safe_int((body or {}).get("queryLimit"), 2)),
    })
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        cached = None if params["force"] else await run_in_threadpool(_radar_cached_run, db, params)
        result = cached or await run_in_threadpool(_radar_run_discovery, db, principal["uid"], params, mode="nightly")
        saved = 0
        for item in result.get("items") or []:
            try:
                _radar_upsert_library_candidate(db, firestore, principal["uid"], item, status="suggested")
                saved += 1
            except Exception:
                continue
        return {**result, "ok": True, "savedSuggestions": saved, "nightly": True}
    except Exception as exc:
        try:
            from firebase_admin import firestore
            db = firestore.client()
            db.collection("radarRuns").document("nightly-last-error").set({
                "status": "error",
                "mode": "nightly",
                "error": str(exc)[:300],
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": str(exc)[:200], "items": []})


@app.get("/video-url/{project_id}")
def get_video_url(project_id: str, request: Request):
    """
    Devuelve una URL firmada fresca (7 días) para el video del proyecto.
    El frontend llama a este endpoint para obtener un link de descarga válido.
    """
    _require_project_access(request, project_id, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore, storage

        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()

        gs_path = data.get("videoStoragePath", "")
        if gs_path and gs_path.startswith("gs://"):
            blob_name = gs_path.split("/", 3)[3]  # remove gs://bucket/
            bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
            blob = bucket.blob(blob_name)
            if blob.exists():
                signed_url = blob.generate_signed_url(
                    version="v4", expiration=timedelta(days=7), method="GET",
                )
                return {"url": signed_url, "expiresInDays": 7, "source": "storage"}

        # Fallback: video aún en VPS (proyecto producido antes de la migración)
        video_folder = data.get("videoFolder", "")
        if video_folder:
            return {"url": f"/download/video/{video_folder}", "source": "vps", "note": "video not yet in Storage"}

        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "no video available"})
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


def _as_text_list(value) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = re.split(r"[,#\n;]+", value)
    else:
        raw_items = []
    items: list[str] = []
    for item in raw_items:
        clean = " ".join(str(item).strip().strip("#").split())
        if clean and clean.lower() not in {x.lower() for x in items}:
            items.append(clean)
    return items


def _compact_title_words(title: str, limit: int = 7) -> list[str]:
    stopwords = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
        "y", "o", "que", "por", "para", "con", "sin", "en", "te", "tu", "tus",
        "su", "sus", "se", "es", "no", "lo", "le", "a",
    }
    words = []
    for token in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", title or ""):
        if len(token) < 3 or token.lower() in stopwords:
            continue
        if token.lower() not in {w.lower() for w in words}:
            words.append(token)
        if len(words) >= limit:
            break
    return words


def _youtube_hashtag(value: str) -> str:
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", value or "")
    if not words:
        return ""
    tag = "#" + "".join(word[:1].upper() + word[1:] for word in words)
    return tag[:80]


def _youtube_tags_for_project(data: dict, title: str) -> list[str]:
    seo = data.get("seo_metadata") or {}
    agent_id = data.get("agentId") or data.get("agent")
    fmt = data.get("format")
    if agent_id == "agent_podcast_general" or fmt == "podcast":
        extras = [
            "Esto no es amor",
            "podcast en español",
            "apego emocional",
            "dependencia emocional",
            "amor propio",
            "relaciones",
            "contacto cero",
            "sanación emocional",
        ]
    elif fmt in {"autohipnosis", "meditacion_larga"}:
        extras = ["meditación guiada", "relajación", "calma", "bienestar"]
    else:
        extras = ["documental", "historia", "video educativo"]
    tags = []
    for extra in extras:
        if extra.lower() not in {tag.lower() for tag in tags}:
            tags.append(extra)
    for word in _compact_title_words(title, limit=8):
        if word.lower() not in {tag.lower() for tag in tags}:
            tags.append(word)
    for tag in _as_text_list(seo.get("tags")):
        if tag.lower() not in {item.lower() for item in tags}:
            tags.append(tag)

    limited: list[str] = []
    total = 0
    for tag in tags:
        candidate_len = len(tag) + (2 if limited else 0)
        if total + candidate_len > 480:
            break
        limited.append(tag)
        total += candidate_len
    return limited[:30]


def _youtube_hashtags_for_project(data: dict, title: str, tags: list[str]) -> list[str]:
    agent_id = data.get("agentId") or data.get("agent")
    fmt = data.get("format")
    if agent_id == "agent_podcast_general" or fmt == "podcast":
        base = [
            "Esto no es amor",
            "Apego emocional",
            "Dependencia emocional",
            "Amor propio",
            "Relaciones",
            "Podcast en español",
        ]
    elif fmt in {"autohipnosis", "meditacion_larga"}:
        base = ["Meditación guiada", "Calma", "Bienestar", "Relajación"]
    else:
        base = ["Documental", "Historia", "Cultura"]
    candidates = base if (agent_id == "agent_podcast_general" or fmt == "podcast") else base + tags[:6] + _compact_title_words(title, limit=5)
    hashtags: list[str] = []
    for item in candidates:
        tag = _youtube_hashtag(item)
        if tag and tag.lower() not in {h.lower() for h in hashtags}:
            hashtags.append(tag)
        if len(hashtags) >= 8:
            break
    return hashtags


def _chapter_lines_from_scenes(scenes: list) -> list[str]:
    lines = []
    current = 0
    meaningful_labels = []
    for scene in scenes or []:
        label = " ".join(str(scene.get("title") or scene.get("label") or "").split())
        if label and not re.fullmatch(r"(?i)(parte|part|scene|escena)\s*\d+", label):
            meaningful_labels.append(label)
    if len(meaningful_labels) < 2:
        return []

    for i, scene in enumerate(scenes or [], 1):
        duration = scene.get("target_duration_seconds") or scene.get("targetDurationSeconds")
        label = " ".join(str(scene.get("title") or scene.get("label") or "").split())
        if not label or re.fullmatch(r"(?i)(parte|part|scene|escena)\s*\d+", label):
            label = "Inicio" if i == 1 else ""
        if not label:
            try:
                current += max(1, float(duration or 0))
            except (TypeError, ValueError):
                current += 0
            continue
        if i == 1:
            label = "Inicio"
        minutes = int(current // 60)
        seconds = int(current % 60)
        lines.append(f"{minutes:02d}:{seconds:02d} {label}")
        try:
            current += max(1, float(duration or 0))
        except (TypeError, ValueError):
            current += 0
    return lines if len(lines) >= 3 and current > 0 else []


def _is_podcast_project(data: dict) -> bool:
    return (data.get("agentId") or data.get("agent")) == "agent_podcast_general" or data.get("format") == "podcast"


def _is_tiktok_project(data: dict) -> bool:
    fmt = data.get("format") or ""
    agent = data.get("agentId") or data.get("agent") or ""
    return data.get("platform") == "tiktok" or fmt in set(_TIKTOK_FORMAT_BY_AGENT.values()) or agent in _TIKTOK_AGENT_IDS


def _youtube_base_description(data: dict, title: str) -> str:
    seo = data.get("seo_metadata") or {}
    description = " ".join(str(seo.get("description") or "").split())
    if description:
        return description
    if _is_podcast_project(data):
        return (
            f"Un episodio de Esto no es amor sobre {title}, apego emocional, "
            "amor propio y relaciones donde la ansiedad puede confundirse con cariño."
        )
    return f"Nuevo video: {title}."


def _youtube_description_for_project(
    data: dict,
    title: str,
    base_description: str,
    hashtags: list[str],
    chapters: list[str],
) -> str:
    hashtag_line = " ".join(hashtags)
    if _is_podcast_project(data):
        parts = [
            base_description,
            (
                f"En este episodio de Esto no es amor hablamos de {title} desde el apego emocional, "
                "la dependencia emocional, la dependencia afectiva, el amor propio y esas relaciones donde la intensidad se siente como amor, "
                "pero en realidad puede esconder ansiedad, miedo al abandono o necesidad de validación."
            ),
            (
                "Si alguna vez perseguiste a quien no te elegía, confundiste incertidumbre con química o sentiste "
                "que soltar era imposible, este espacio es para mirar la verdad sin juicio y volver a elegirte."
            ),
            (
                "Suscríbete para más conversaciones sobre relaciones, límites, contacto cero, autoestima y sanación emocional. "
                "Déjame en comentarios qué parte te movió más o qué tema quieres que hablemos en un próximo episodio."
            ),
            (
                "Si quieres crear tu propio podcast o necesitas ayuda para convertir tus ideas en contenido listo para publicar, "
                "también puedes ponerte en contacto con nosotros."
            ),
        ]
        if chapters:
            parts.extend(["Momentos del episodio:", *chapters[:12]])
        if hashtag_line:
            parts.append(hashtag_line)
        return "\n\n".join(part for part in parts if part).strip()[:5000]

    parts = [
        base_description,
        "En este video exploramos el tema con una mirada clara, emocional y práctica.",
    ]
    if chapters:
        parts.extend(["Capítulos:", *chapters[:20]])
    if hashtag_line:
        parts.append(hashtag_line)
    return "\n\n".join(part for part in parts if part).strip()[:5000]


def _build_youtube_publish_pack(project_id: str, data: dict) -> dict:
    title = data.get("title") or (data.get("seo_metadata") or {}).get("title") or "Video listo para publicar"
    tags = _youtube_tags_for_project(data, title)
    hashtags = _youtube_hashtags_for_project(data, title, tags)
    chapters = _chapter_lines_from_scenes(data.get("scenes") or [])
    description = _youtube_base_description(data, title)
    youtube_description = _youtube_description_for_project(data, title, description, hashtags, chapters)

    pinned_comment = (
        "¿Qué parte de este tema te hizo más sentido? Te leo en comentarios."
        if data.get("format") != "podcast"
        else "¿Esto te sonó a amor o a apego? Cuéntame en comentarios qué parte te pegó más."
    )
    checklist = "\n".join([
        "# Checklist de publicación",
        "",
        "- [ ] Subir el video final con subtítulos.",
        "- [ ] Elegir una de las 3 miniaturas.",
        "- [ ] Pegar título, descripción, hashtags y tags.",
        "- [ ] Revisar que los primeros 30 segundos enganchen.",
        "- [ ] Confirmar volumen, subtítulos y cortes de shorts.",
        "- [ ] Publicar o programar.",
        "- [ ] Fijar el comentario sugerido.",
        "- [ ] Usar los shorts como promoción del video largo.",
    ])
    return {
        "project_id": project_id,
        "title": title,
        "description": youtube_description,
        "hashtags": hashtags,
        "tags": tags,
        "tags_csv": ", ".join(tags),
        "pinned_comment": pinned_comment,
        "chapters": chapters,
        "checklist": checklist,
    }


_YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
_YOUTUBE_WEB_URL = os.environ.get(
    "CONTENT_FACTORY_WEB_URL",
    "https://content-youtube-generator.vercel.app",
).rstrip("/")


def _youtube_oauth_settings() -> dict:
    redirect_uri = os.environ.get("YOUTUBE_OAUTH_REDIRECT_URI", "").strip()
    if not redirect_uri:
        public_api = os.environ.get("VPS_PUBLIC_URL", "").strip().rstrip("/")
        if public_api:
            redirect_uri = f"{public_api}/youtube/oauth/callback"

    return {
        "client_id": os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "").strip(),
        "redirect_uri": redirect_uri,
        "state_secret": (
            os.environ.get("CONTENT_FACTORY_YOUTUBE_STATE_SECRET", "").strip()
            or _ADMIN_TOKEN
            or os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "").strip()
        ),
        "token_secret": (
            os.environ.get("CONTENT_FACTORY_YOUTUBE_TOKEN_SECRET", "").strip()
            or _ADMIN_TOKEN
        ),
    }


def _youtube_config_status() -> dict:
    settings = _youtube_oauth_settings()
    missing = [
        key
        for key in ["client_id", "client_secret", "redirect_uri", "state_secret", "token_secret"]
        if not settings.get(key)
    ]
    return {
        "configured": not missing,
        "missing": missing,
        "redirectUri": settings.get("redirect_uri") or None,
        "scopes": list(_YOUTUBE_SCOPES),
    }


def _youtube_require_config() -> dict:
    status = _youtube_config_status()
    if not status["configured"]:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "youtube_oauth_not_configured",
                "missing": status["missing"],
                "redirectUri": status.get("redirectUri"),
            },
        )
    return _youtube_oauth_settings()


def _safe_youtube_return_path(value: str | None) -> str:
    raw = (value or "/dashboard").strip()
    if not raw.startswith("/") or raw.startswith("//"):
        return "/dashboard"
    if "\n" in raw or "\r" in raw:
        return "/dashboard"
    return raw[:300]


def _youtube_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _youtube_unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _youtube_sign_state(payload: dict) -> str:
    settings = _youtube_require_config()
    body = _youtube_b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = hmac.new(settings["state_secret"].encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_youtube_b64(sig)}"


def _youtube_verify_state(state: str) -> dict:
    settings = _youtube_require_config()
    try:
        body, sig = state.split(".", 1)
        expected = hmac.new(settings["state_secret"].encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        provided = _youtube_unb64(sig)
        if not hmac.compare_digest(expected, provided):
            raise ValueError("bad signature")
        payload = json.loads(_youtube_unb64(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid youtube oauth state") from exc


def _youtube_fernet():
    settings = _youtube_require_config()
    try:
        from cryptography.fernet import Fernet
    except Exception as exc:
        raise HTTPException(status_code=503, detail="cryptography dependency missing") from exc
    key = base64.urlsafe_b64encode(hashlib.sha256(settings["token_secret"].encode("utf-8")).digest())
    return Fernet(key)


def _youtube_encrypt_token(value: str) -> str:
    return _youtube_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def _youtube_decrypt_token(value: str) -> str:
    return _youtube_fernet().decrypt(value.encode("ascii")).decode("utf-8")


def _youtube_authorization_url(uid: str, return_to: str) -> str:
    settings = _youtube_require_config()
    state = _youtube_sign_state({
        "uid": uid,
        "returnTo": _safe_youtube_return_path(return_to),
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + 15 * 60,
    })
    params = {
        "client_id": settings["client_id"],
        "redirect_uri": settings["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(_YOUTUBE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def _youtube_request_tokens(code: str) -> dict:
    settings = _youtube_require_config()
    import requests
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings["client_id"],
            "client_secret": settings["client_secret"],
            "redirect_uri": settings["redirect_uri"],
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"youtube token exchange failed: {response.text[:200]}")
    return response.json()


def _youtube_refresh_access_token(refresh_token: str) -> dict:
    settings = _youtube_require_config()
    import requests
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings["client_id"],
            "client_secret": settings["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"youtube refresh failed: {response.text[:200]}")
    return response.json()


def _youtube_fetch_channels(access_token: str) -> list[dict]:
    import requests
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet,brandingSettings,status", "mine": "true", "maxResults": 50},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"youtube channel lookup failed: {response.text[:200]}")
    channels = []
    for item in response.json().get("items", []):
        snippet = item.get("snippet") or {}
        branding = item.get("brandingSettings") or {}
        status = item.get("status") or {}
        channels.append({
            "channelId": item.get("id"),
            "title": snippet.get("title") or "Canal sin nombre",
            "description": (branding.get("channel") or {}).get("description") or snippet.get("description") or "",
            "thumbnailUrl": ((snippet.get("thumbnails") or {}).get("default") or {}).get("url"),
            "longUploadsStatus": status.get("longUploadsStatus"),
            "madeForKids": status.get("madeForKids"),
            "selfDeclaredMadeForKids": status.get("selfDeclaredMadeForKids"),
        })
    return [c for c in channels if c.get("channelId")]


_TIKTOK_SCOPES = ["user.info.basic", "video.upload"]
_TIKTOK_WEB_URL = _YOUTUBE_WEB_URL
_TIKTOK_ACTIVE_JOB_STATUSES = {
    "queued",
    "leased",
    "upload_initialized",
    "uploading",
    "inbox_delivered",
    "needs_review",
    "completed",
}
_TIKTOK_INBOX_PENDING_STATUSES = {
    "queued",
    "leased",
    "upload_initialized",
    "uploading",
    "inbox_delivered",
    "needs_review",
}


def _tiktok_oauth_settings() -> dict:
    redirect_uri = os.environ.get("TIKTOK_OAUTH_REDIRECT_URI", "").strip()
    if not redirect_uri:
        public_api = os.environ.get("VPS_PUBLIC_URL", "").strip().rstrip("/")
        if public_api:
            redirect_uri = f"{public_api}/tiktok/oauth/callback"
    return {
        "client_key": os.environ.get("TIKTOK_CLIENT_KEY", "").strip(),
        "client_secret": os.environ.get("TIKTOK_CLIENT_SECRET", "").strip(),
        "redirect_uri": redirect_uri,
        "state_secret": (
            os.environ.get("CONTENT_FACTORY_TIKTOK_STATE_SECRET", "").strip()
            or _ADMIN_TOKEN
            or os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
        ),
        "token_secret": (
            os.environ.get("CONTENT_FACTORY_TIKTOK_TOKEN_SECRET", "").strip()
            or _ADMIN_TOKEN
        ),
    }


def _tiktok_config_status() -> dict:
    settings = _tiktok_oauth_settings()
    missing = [
        key
        for key in ["client_key", "client_secret", "redirect_uri", "state_secret", "token_secret"]
        if not settings.get(key)
    ]
    return {
        "configured": not missing,
        "missing": missing,
        "redirectUri": settings.get("redirect_uri") or None,
        "scopes": list(_TIKTOK_SCOPES),
    }


def _tiktok_require_config() -> dict:
    status = _tiktok_config_status()
    if not status["configured"]:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "tiktok_oauth_not_configured",
                "missing": status["missing"],
                "redirectUri": status.get("redirectUri"),
            },
        )
    return _tiktok_oauth_settings()


def _safe_tiktok_return_path(value: str | None) -> str:
    return _safe_youtube_return_path(value)


def _tiktok_sign_state(payload: dict) -> str:
    settings = _tiktok_require_config()
    body = _youtube_b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = hmac.new(settings["state_secret"].encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_youtube_b64(sig)}"


def _tiktok_verify_state(state: str) -> dict:
    settings = _tiktok_require_config()
    try:
        body, sig = state.split(".", 1)
        expected = hmac.new(settings["state_secret"].encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        provided = _youtube_unb64(sig)
        if not hmac.compare_digest(expected, provided):
            raise ValueError("bad signature")
        payload = json.loads(_youtube_unb64(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid tiktok oauth state") from exc


def _tiktok_fernet():
    settings = _tiktok_require_config()
    try:
        from cryptography.fernet import Fernet
    except Exception as exc:
        raise HTTPException(status_code=503, detail="cryptography dependency missing") from exc
    key = base64.urlsafe_b64encode(hashlib.sha256(settings["token_secret"].encode("utf-8")).digest())
    return Fernet(key)


def _tiktok_encrypt_token(value: str) -> str:
    return _tiktok_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def _tiktok_decrypt_token(value: str) -> str:
    return _tiktok_fernet().decrypt(value.encode("ascii")).decode("utf-8")


def _tiktok_authorization_url(uid: str, return_to: str) -> str:
    settings = _tiktok_require_config()
    state = _tiktok_sign_state({
        "uid": uid,
        "returnTo": _safe_tiktok_return_path(return_to),
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + 15 * 60,
    })
    params = {
        "client_key": settings["client_key"],
        "redirect_uri": settings["redirect_uri"],
        "response_type": "code",
        "scope": ",".join(_TIKTOK_SCOPES),
        "state": state,
    }
    return "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)


def _tiktok_request_tokens(code: str) -> dict:
    settings = _tiktok_require_config()
    import requests
    response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": settings["client_key"],
            "client_secret": settings["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings["redirect_uri"],
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"tiktok token exchange failed: {response.text[:200]}")
    return response.json()


def _tiktok_refresh_access_token(refresh_token: str) -> dict:
    settings = _tiktok_require_config()
    import requests
    response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": settings["client_key"],
            "client_secret": settings["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"tiktok refresh failed: {response.text[:200]}")
    return response.json()


def _tiktok_fetch_user(access_token: str) -> dict:
    import requests
    response = requests.get(
        "https://open.tiktokapis.com/v2/user/info/",
        params={"fields": "open_id,union_id,avatar_url,display_name"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"tiktok user lookup failed: {response.text[:200]}")
    data = response.json().get("data") or {}
    user = data.get("user") or {}
    return {
        "openId": user.get("open_id") or data.get("open_id") or "",
        "unionId": user.get("union_id") or data.get("union_id") or "",
        "displayName": user.get("display_name") or "Cuenta TikTok",
        "avatarUrl": user.get("avatar_url") or "",
    }


def _tiktok_public_account_doc(doc) -> dict:
    data = doc.to_dict() or {}
    return {
        "accountId": doc.id,
        "openId": data.get("openId") or doc.id,
        "displayName": data.get("displayName") or "Cuenta TikTok",
        "avatarUrl": data.get("avatarUrl") or "",
        "connectedAt": _serialize_firestore_value(data.get("connectedAt")),
        "updatedAt": _serialize_firestore_value(data.get("updatedAt")),
        "scopes": data.get("scopes") or list(_TIKTOK_SCOPES),
    }


def _tiktok_final_video_file(video_dir: Path) -> Path | None:
    candidate = video_dir / "FINAL_TIKTOK.mp4"
    if candidate.is_file():
        return candidate
    candidates = sorted(video_dir.glob("*TIKTOK*.mp4"))
    for item in candidates:
        if item.is_file():
            return item
    return None


def _tiktok_cover_file(video_dir: Path) -> Path | None:
    candidate = video_dir / "tiktok" / "cover.jpg"
    return candidate if candidate.is_file() else None


def _tiktok_video_file_hash(video_file: Path) -> str:
    digest = hashlib.sha256()
    with video_file.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tiktok_video_preflight(data: dict) -> dict:
    result = {
        "eligible": False,
        "filename": None,
        "durationSeconds": None,
        "durationMinutes": None,
        "width": None,
        "height": None,
        "sizeMb": None,
        "error": "",
    }
    try:
        video_dir = _youtube_project_video_dir(data)
        video_file = _tiktok_final_video_file(video_dir)
        if not video_file:
            return {**result, "error": "FINAL_TIKTOK.mp4 not found"}
        ok, duration, err = _validate_media_file(video_file, min_duration_seconds=1)
        width, height = _youtube_video_dimensions(video_file)
        result.update({
            "filename": video_file.name,
            "durationSeconds": round(duration or 0, 2),
            "durationMinutes": round((duration or 0) / 60, 1),
            "width": width or None,
            "height": height or None,
            "sizeMb": round(video_file.stat().st_size / (1024 * 1024), 1),
        })
        if not ok:
            return {**result, "error": err or "video is not readable"}
        if duration > 600:
            return {**result, "error": "TikTok video exceeds 10 minutes"}
        if not width or not height:
            return {**result, "error": "video dimensions could not be read"}
        if height <= width:
            return {**result, "error": "TikTok video must be vertical"}
        return {**result, "eligible": True}
    except Exception as exc:
        return {**result, "error": str(exc)[:200]}


def _tiktok_caption_pack(project_id: str, data: dict, payload: dict | None = None) -> dict:
    payload = payload or {}
    title = str(data.get("title") or "TikTok listo").strip()
    tiktok = data.get("tiktok") or {}

    def _normalize_hashtags(value) -> list[str]:
        raw = value if isinstance(value, list) else re.split(r"[\s,;]+", str(value or ""))
        tags = []
        seen = set()
        for item in raw:
            tag = str(item or "").strip()
            if not tag:
                continue
            if not tag.startswith("#"):
                tag = f"#{tag.lstrip('#')}"
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            tags.append(tag[:80])
        return tags

    hashtags = _normalize_hashtags(payload.get("hashtags"))
    if not hashtags:
        hashtags = _normalize_hashtags(tiktok.get("hashtags") if isinstance(tiktok.get("hashtags"), list) else [])
    if not hashtags:
        hashtags = ["#EstoNoEsAmor", "#ApegoEmocional", "#AmorPropio", "#TikTok"]
    caption = str(payload.get("caption") or tiktok.get("caption") or title).strip()
    if not any(str(tag).lower() in caption.lower() for tag in hashtags):
        caption = f"{caption}\n\n{' '.join(hashtags)}"
    return {
        "projectId": project_id,
        "title": title[:100],
        "caption": caption[:2200],
        "hashtags": [str(tag).strip() for tag in hashtags if str(tag).strip().startswith("#")][:12],
        "coverFile": ((tiktok.get("delivery") or {}).get("coverFile") or "cover.jpg"),
        "isAigc": True,
        "brandedContent": False,
    }


def _tiktok_idempotency_key(uid: str, account_id: str, project_id: str, file_hash: str, scheduled_at: str) -> str:
    raw = "|".join([
        str(uid or "").strip(),
        str(account_id or "").strip(),
        str(project_id or "").strip(),
        str(file_hash or "").strip(),
        str(scheduled_at or "").strip(),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _tiktok_job_doc_id(idempotency_key: str) -> str:
    return f"tt_{idempotency_key[:40]}"


def _tiktok_scheduled_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid TikTok scheduledAt")


def _tiktok_build_publish_job_payload(uid: str, project_id: str, data: dict, account_id: str, payload: dict | None = None) -> dict:
    if data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="TikTok project is not completed")
    video_dir = _youtube_project_video_dir(data)
    video_file = _tiktok_final_video_file(video_dir)
    if not video_file:
        raise HTTPException(status_code=400, detail="FINAL_TIKTOK.mp4 not found")
    preflight = _tiktok_video_preflight(data)
    if not preflight.get("eligible"):
        raise HTTPException(status_code=400, detail=preflight.get("error") or "TikTok video is not eligible")
    scheduled_dt = _tiktok_scheduled_datetime((payload or {}).get("scheduledAt"))
    scheduled_at = scheduled_dt.isoformat() if scheduled_dt else ""
    file_hash = _tiktok_video_file_hash(video_file)
    idempotency_key = _tiktok_idempotency_key(uid, account_id, project_id, file_hash, scheduled_at)
    metadata = _tiktok_caption_pack(project_id, data, payload)
    cover = _tiktok_cover_file(video_dir)
    return {
        "idempotencyKey": idempotency_key,
        "uid": uid,
        "projectId": project_id,
        "accountId": account_id,
        "status": "queued",
        "type": "tiktok_inbox",
        "step": "Programado para enviar a TikTok Inbox" if scheduled_at else "En cola para enviar a TikTok Inbox",
        "scheduledAt": scheduled_at,
        "fileHash": file_hash,
        "video": {
            "path": str(video_file),
            "filename": video_file.name,
            "sizeBytes": video_file.stat().st_size,
            **preflight,
        },
        "cover": {
            "path": str(cover) if cover else "",
            "filename": cover.name if cover else "",
        },
        "metadata": metadata,
        "publishId": "",
        "uploadUrlReceived": False,
        "retryPolicy": {
            "autoRetryInitWithoutPublishId": False,
            "reason": "avoid duplicate TikTok inbox shares",
        },
    }


def _tiktok_job_is_due(job: dict, *, now: datetime | None = None) -> bool:
    scheduled = _tiktok_scheduled_datetime(job.get("scheduledAt"))
    if not scheduled:
        return True
    return scheduled <= (now or datetime.now(timezone.utc))


def _tiktok_create_or_get_job(db, firestore, job_payload: dict) -> tuple[str, dict, bool]:
    job_id = _tiktok_job_doc_id(job_payload["idempotencyKey"])
    job_ref = db.collection("tiktokPublishJobs").document(job_id)

    @firestore.transactional
    def _txn(transaction):
        snap = job_ref.get(transaction=transaction)
        if snap.exists:
            existing = snap.to_dict() or {}
            if existing.get("status") in _TIKTOK_ACTIVE_JOB_STATUSES:
                return job_id, existing, False
        transaction.set(job_ref, {
            **job_payload,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        return job_id, job_payload, True

    return _txn(db.transaction())


def _tiktok_count_recent_account_jobs(db, uid: str, account_id: str, statuses: set[str], *, hours: int = 24) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    docs = list(
        db.collection("tiktokPublishJobs")
        .where("uid", "==", uid)
        .where("accountId", "==", account_id)
        .limit(50)
        .stream()
    )
    count = 0
    for doc in docs:
        data = doc.to_dict() or {}
        if data.get("status") not in statuses:
            continue
        created = _youtube_datetime(_serialize_firestore_value(data.get("createdAt")))
        if not created or created >= cutoff:
            count += 1
    return count


def _tiktok_record_rate_event(db, firestore, uid: str, account_id: str) -> None:
    db.collection("users").document(uid).collection("tiktokAccounts").document(account_id).collection("rateLimitEvents").document().set({
        "createdAt": firestore.SERVER_TIMESTAMP,
    })


def _tiktok_rate_limit_count(db, uid: str, account_id: str) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    docs = list(
        db.collection("users").document(uid)
        .collection("tiktokAccounts").document(account_id)
        .collection("rateLimitEvents")
        .where("createdAt", ">=", cutoff)
        .limit(6)
        .stream()
    )
    return len(docs)


def _tiktok_refresh_account_token(db, firestore, uid: str, account_id: str) -> str:
    account_ref = db.collection("users").document(uid).collection("tiktokAccounts").document(account_id)
    snap = account_ref.get()
    if not snap.exists:
        raise RuntimeError("TikTok account not connected")
    account = snap.to_dict() or {}
    refresh_token = _tiktok_decrypt_token(account.get("refreshTokenEncrypted") or "")
    token_data = _tiktok_refresh_access_token(refresh_token)
    access_token = token_data.get("access_token") or ""
    next_refresh = token_data.get("refresh_token") or refresh_token
    if not access_token:
        raise RuntimeError("TikTok refresh did not return access token")
    account_ref.update({
        "accessTokenEncrypted": _tiktok_encrypt_token(access_token),
        "refreshTokenEncrypted": _tiktok_encrypt_token(next_refresh),
        "accessExpiresAt": datetime.now(timezone.utc) + timedelta(seconds=int(token_data.get("expires_in") or 86400)),
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    return access_token


def _tiktok_init_inbox_upload(access_token: str, video_file: Path) -> dict:
    import requests
    size = video_file.stat().st_size
    chunk_size = min(size, 64 * 1024 * 1024)
    total_chunks = max(1, (size + chunk_size - 1) // chunk_size)
    response = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        json={
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            }
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"tiktok inbox init failed: {response.text[:300]}")
    payload = response.json()
    data = payload.get("data") or {}
    publish_id = data.get("publish_id") or ""
    upload_url = data.get("upload_url") or ""
    if not publish_id or not upload_url:
        raise RuntimeError(f"tiktok inbox init missing publish_id/upload_url: {str(payload)[:300]}")
    return {"publishId": publish_id, "uploadUrl": upload_url, "chunkSize": chunk_size, "totalChunks": total_chunks}


def _tiktok_upload_file(upload_url: str, video_file: Path, chunk_size: int) -> None:
    import requests
    size = video_file.stat().st_size
    with video_file.open("rb") as fh:
        start = 0
        while start < size:
            data = fh.read(chunk_size)
            end = start + len(data) - 1
            response = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(data)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                },
                data=data,
                timeout=(30, 1800),
            )
            if response.status_code >= 400:
                raise RuntimeError(f"tiktok inbox upload failed: {response.text[:300]}")
            start = end + 1


def _tiktok_fetch_publish_status(access_token: str, publish_id: str) -> dict:
    import requests
    response = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        json={"publish_id": publish_id},
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"tiktok status fetch failed: {response.text[:300]}")
    return response.json().get("data") or {}


def _run_tiktok_publish_job(uid: str, job_id: str):
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    job_ref = db.collection("tiktokPublishJobs").document(job_id)
    project_ref = None
    try:
        snap = job_ref.get()
        if not snap.exists:
            raise RuntimeError("TikTok job not found")
        job = snap.to_dict() or {}
        if job.get("uid") != uid:
            raise RuntimeError("TikTok job access denied")
        if job.get("status") in {"completed", "cancelled"}:
            return
        if not _tiktok_job_is_due(job):
            return

        job_ref.update({
            "status": "leased",
            "step": "Validando video TikTok",
            "leasedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        project_id = job.get("projectId") or ""
        account_id = job.get("accountId") or ""
        project_ref = db.collection("projects").document(project_id)
        project_snap = project_ref.get()
        if not project_snap.exists:
            raise RuntimeError("project not found")
        project = project_snap.to_dict() or {}
        if project.get("userId") != uid:
            raise RuntimeError("project access denied")
        preflight = _tiktok_video_preflight(project)
        if not preflight.get("eligible"):
            raise RuntimeError(preflight.get("error") or "TikTok video is not eligible")

        pending_count = _tiktok_count_recent_account_jobs(db, uid, account_id, _TIKTOK_INBOX_PENDING_STATUSES)
        if pending_count > 5:
            raise RuntimeError("TikTok pending inbox share cap reached; review existing inbox uploads first")
        if _tiktok_rate_limit_count(db, uid, account_id) >= 6:
            raise RuntimeError("TikTok rate limit guard: wait before sending another upload")

        access_token = _tiktok_refresh_account_token(db, firestore, uid, account_id)
        _tiktok_record_rate_event(db, firestore, uid, account_id)

        video_file = Path((job.get("video") or {}).get("path") or "")
        if not video_file.is_file():
            raise RuntimeError("TikTok video file missing on worker")

        publish_id = job.get("publishId") or ""
        if publish_id:
            status_data = _tiktok_fetch_publish_status(access_token, publish_id)
            job_ref.update({
                "status": "needs_review",
                "step": "TikTok ya recibió el video; revisa el inbox antes de reintentar",
                "statusData": status_data,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            return

        job_ref.update({
            "status": "upload_initialized",
            "step": "Solicitando upload seguro a TikTok",
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        init_data = _tiktok_init_inbox_upload(access_token, video_file)
        publish_id = init_data["publishId"]
        job_ref.update({
            "publishId": publish_id,
            "uploadUrlReceived": True,
            "status": "uploading",
            "step": "Subiendo video a TikTok Inbox",
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        _tiktok_upload_file(init_data["uploadUrl"], video_file, int(init_data["chunkSize"]))
        completed_payload = {
            "status": "completed",
            "step": "Video enviado a TikTok Inbox; termina la publicacion desde TikTok",
            "completedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        job_ref.update(completed_payload)
        project_ref.update({
            "tiktok.publishing.status": "inbox_delivered",
            "tiktok.publishing.lastJobId": job_id,
            "tiktok.publishing.lastPublishId": publish_id,
            "tiktok.publishing.needsReview": True,
            "tiktok.publishing.updatedAt": firestore.SERVER_TIMESTAMP,
        })
    except Exception as exc:
        raw = str(exc)[:500]
        snap = job_ref.get()
        current = snap.to_dict() if snap.exists else {}
        has_publish_id = bool((current or {}).get("publishId"))
        uncertain_init = (not has_publish_id) and ("timeout" in raw.lower() or "timed out" in raw.lower())
        status = "needs_review" if uncertain_init or has_publish_id else "failed"
        step = (
            "No se puede confirmar si TikTok recibio el init; revisa antes de reintentar"
            if uncertain_init
            else "TikTok recibio un publish_id; revisa status antes de reintentar"
            if has_publish_id
            else "Error al enviar a TikTok Inbox"
        )
        job_ref.update({
            "status": status,
            "step": step,
            "error": raw,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })


def _enqueue_tiktok_publish_job(uid: str, job_id: str, background_tasks: BackgroundTasks) -> dict:
    try:
        from worker_tasks import publish_tiktok_inbox
        task = publish_tiktok_inbox.delay(uid, job_id)
        return {"queue": "celery", "taskId": task.id}
    except Exception as queue_err:
        try:
            log.warning("tiktok_publish_queue_unavailable", job_id=job_id, error=str(queue_err)[:200])
        except TypeError:
            log.warning(f"tiktok_publish_queue_unavailable job_id={job_id} error={str(queue_err)[:200]}")
        background_tasks.add_task(_run_tiktok_publish_job, uid, job_id)
        return {"queue": "api_background", "error": str(queue_err)[:200]}


def _youtube_split_tags(value) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,;\n]", str(value or ""))
    tags = []
    seen = set()
    for item in raw:
        tag = " ".join(str(item).strip().split())
        key = tag.lower()
        if not tag or key in seen:
            continue
        if sum(len(t) + 2 for t in tags + [tag]) > 500:
            break
        seen.add(key)
        tags.append(tag[:100])
    return tags


def _build_youtube_video_resource(project_id: str, data: dict, payload: dict | None = None) -> dict:
    payload = payload or {}
    pack = _build_youtube_publish_pack(project_id, data)
    title = " ".join(str(payload.get("title") or pack["title"]).split())[:100]
    description = str(payload.get("description") or pack["description"])[:5000]
    tags = _youtube_split_tags(payload.get("tags") or pack.get("tags") or pack.get("tags_csv"))
    privacy = str(payload.get("privacyStatus") or "private").strip().lower()
    if privacy not in {"private", "unlisted", "public"}:
        privacy = "private"
    publish_at = str(payload.get("publishAt") or "").strip()
    if publish_at:
        privacy = "private"

    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at:
        status["publishAt"] = publish_at

    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(payload.get("categoryId") or "22"),
        },
        "status": status,
    }


_YOUTUBE_SHORT_HASHTAGS = [
    "#Shorts",
    "#EstoNoEsAmor",
    "#ApegoEmocional",
    "#AmorPropio",
    "#Relaciones",
]

_YOUTUBE_SHORT_LABEL_COPY = {
    "hook": {
        "name": "Gancho",
        "title": "La señal que no debes ignorar",
        "description": "Un fragmento para reconocer cuándo la intensidad se parece más al apego que al amor.",
        "offsetHours": -24,
    },
    "mid": {
        "name": "Punto fuerte",
        "title": "La parte que más duele aceptar",
        "description": "Una idea central del episodio para mirar el patrón con más claridad.",
        "offsetHours": -3,
    },
    "end": {
        "name": "Cierre",
        "title": "Vuelve a elegirte",
        "description": "Un recordatorio final para soltar lo que no te elige y volver a ti.",
        "offsetHours": 24,
    },
    "closing": {
        "name": "Cierre",
        "title": "Vuelve a elegirte",
        "description": "Un recordatorio final para soltar lo que no te elige y volver a ti.",
        "offsetHours": 24,
    },
}


def _youtube_short_hashtags(data: dict, title: str) -> list[str]:
    if _is_podcast_project(data):
        return list(_YOUTUBE_SHORT_HASHTAGS)
    tags = ["#Shorts"]
    for item in _youtube_hashtags_for_project(data, title, _youtube_tags_for_project(data, title))[:4]:
        if item.lower() not in {tag.lower() for tag in tags}:
            tags.append(item)
    return tags[:5]


def _youtube_shorts_title(value: str, suffix: str = " #Shorts") -> str:
    title = " ".join(str(value or "").split()).replace("<", "").replace(">", "")
    if not title:
        title = "Short listo para publicar"
    if "#shorts" in title.lower():
        return title[:100].rstrip()
    room = 100 - len(suffix)
    if len(title) > room:
        title = title[: max(1, room - 1)].rstrip(" .,:;") + "..."
    return f"{title}{suffix}"[:100].rstrip()


def _build_youtube_short_metadata(project_id: str, data: dict, short: dict) -> dict:
    long_title = data.get("title") or (data.get("seo_metadata") or {}).get("title") or "Episodio listo"
    label = str(short.get("label") or "").strip().lower()
    label_copy = _YOUTUBE_SHORT_LABEL_COPY.get(label) or {
        "name": f"Clip {short.get('index') or ''}".strip(),
        "title": "Un momento clave del episodio",
        "description": "Un fragmento del episodio completo.",
        "offsetHours": 24,
    }
    hashtags = _youtube_short_hashtags(data, long_title)
    tags = _youtube_tags_for_project(data, long_title)
    for extra in ["shorts", "YouTube Shorts", label_copy["name"]]:
        if extra and extra.lower() not in {tag.lower() for tag in tags}:
            tags.append(extra)

    if _is_podcast_project(data):
        title = _youtube_shorts_title(f"Esto no es amor: {label_copy['title']}")
        description_parts = [
            f"Short del episodio completo: {long_title}.",
            label_copy["description"],
            "Mira el episodio completo en el canal y suscríbete para más conversaciones sobre apego emocional, amor propio, límites y relaciones.",
            "Déjame en comentarios si esto te sonó a amor o a apego.",
        ]
    else:
        title = _youtube_shorts_title(f"{long_title} - {label_copy['name']}")
        description_parts = [
            f"Short del video completo: {long_title}.",
            label_copy["description"],
            "Mira el video completo en el canal y suscríbete para más contenido.",
        ]

    long_video_id = ((data.get("youtube") or {}).get("lastVideoId") or "").strip()
    if long_video_id:
        description_parts.append(f"Episodio completo: https://youtu.be/{long_video_id}")

    description_parts.append(" ".join(hashtags))
    return {
        "projectId": project_id,
        "index": int(short.get("index") or 0),
        "label": label,
        "labelName": label_copy["name"],
        "title": title,
        "description": "\n\n".join(part for part in description_parts if part).strip()[:5000],
        "tags": tags[:30],
        "tagsCsv": ", ".join(tags[:30]),
        "hashtags": hashtags,
        "offsetHours": int(label_copy.get("offsetHours") or 24),
    }


def _build_youtube_shorts_publish_pack(project_id: str, data: dict) -> dict:
    shorts = []
    for short in data.get("shorts") or []:
        if not isinstance(short, dict):
            continue
        metadata = _build_youtube_short_metadata(project_id, data, short)
        shorts.append({
            **short,
            "metadata": metadata,
        })
    return {
        "projectId": project_id,
        "shorts": shorts,
        "hashtags": _youtube_short_hashtags(data, data.get("title") or ""),
        "scheduleOffsetsHours": [-24, -3, 24],
    }


def _youtube_short_resource(project_id: str, data: dict, short: dict, payload: dict | None = None) -> dict:
    payload = payload or {}
    metadata = _build_youtube_short_metadata(project_id, data, short)
    title = _youtube_shorts_title(payload.get("title") or metadata["title"])
    description = str(payload.get("description") or metadata["description"])[:5000]
    if "#shorts" not in description.lower():
        description = (description.rstrip() + "\n\n#Shorts")[:5000]
    tags = _youtube_split_tags(payload.get("tags") or metadata["tags"])
    privacy = str(payload.get("privacyStatus") or "private").strip().lower()
    if privacy not in {"private", "unlisted", "public"}:
        privacy = "private"
    publish_at = str(payload.get("publishAt") or "").strip()
    if publish_at:
        privacy = "private"

    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,
    }
    if publish_at:
        status["publishAt"] = publish_at

    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(payload.get("categoryId") or "22"),
        },
        "status": status,
        "paidProductPlacementDetails": {
            "hasPaidProductPlacement": bool(payload.get("hasPaidProductPlacement") or False),
        },
    }


def _youtube_public_channel_doc(snapshot) -> dict:
    data = snapshot.to_dict() or {}
    return {
        "id": snapshot.id,
        "channelId": data.get("channelId") or snapshot.id,
        "title": data.get("title") or "Canal conectado",
        "description": data.get("description") or "",
        "thumbnailUrl": data.get("thumbnailUrl"),
        "longUploadsStatus": data.get("longUploadsStatus"),
        "madeForKids": data.get("madeForKids"),
        "selfDeclaredMadeForKids": data.get("selfDeclaredMadeForKids"),
        "connectedAt": str(data.get("connectedAt") or ""),
        "updatedAt": str(data.get("updatedAt") or ""),
    }


def _youtube_datetime(value):
    if not value:
        return None
    if hasattr(value, "timestamp"):
        try:
            return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def _youtube_job_sort_value(job: dict) -> float:
    dt = _youtube_datetime(job.get("updatedAt") or job.get("createdAt"))
    return dt.timestamp() if dt else 0.0


def _youtube_latest_jobs_by_project(job_docs) -> dict:
    latest = {}
    for doc in job_docs:
        data = doc.to_dict() or {}
        project_id = data.get("projectId")
        if not project_id:
            continue
        kind = "shorts" if data.get("type") == "shorts" else "video"
        entry = {"id": doc.id, **data}
        project_jobs = latest.setdefault(project_id, {})
        previous = project_jobs.get(kind)
        if not previous or _youtube_job_sort_value(entry) >= _youtube_job_sort_value(previous):
            project_jobs[kind] = entry
    return latest


def _tiktok_latest_jobs_by_project(job_docs) -> dict:
    latest = {}
    for doc in job_docs:
        data = doc.to_dict() or {}
        project_id = data.get("projectId")
        if not project_id:
            continue
        entry = {"id": doc.id, **data}
        previous = latest.get(project_id)
        if not previous or _youtube_job_sort_value(entry) >= _youtube_job_sort_value(previous):
            latest[project_id] = entry
    return latest


def _youtube_video_publish_at_from_job(job: dict | None) -> str:
    metadata = (job or {}).get("metadata") or {}
    status = metadata.get("status") or {}
    return str(status.get("publishAt") or "").strip()


def _youtube_video_privacy_from_job(job: dict | None) -> str:
    metadata = (job or {}).get("metadata") or {}
    status = metadata.get("status") or {}
    return str(status.get("privacyStatus") or "").strip()


def _youtube_successful_short_uploads(value) -> list[dict]:
    uploads = value if isinstance(value, list) else []
    by_index = {}
    for item in uploads:
        if not isinstance(item, dict) or not item.get("youtubeVideoId"):
            continue
        try:
            index = int(item.get("index") or 0)
        except Exception:
            index = 0
        if index <= 0:
            continue
        existing = by_index.get(index)
        if not existing:
            by_index[index] = item
            continue
        old_dt = _youtube_datetime(existing.get("uploadedAt") or existing.get("publishAt"))
        new_dt = _youtube_datetime(item.get("uploadedAt") or item.get("publishAt"))
        if (new_dt and not old_dt) or (new_dt and old_dt and new_dt >= old_dt):
            by_index[index] = item
    return [by_index[index] for index in sorted(by_index)]


def _youtube_future_count(items: list[dict], *, now: datetime) -> int:
    count = 0
    for item in items:
        publish_at = _youtube_datetime(item.get("publishAt"))
        if publish_at and publish_at > now:
            count += 1
    return count


def _youtube_publication_overview_row(
    project_id: str,
    data: dict,
    *,
    latest_video_job: dict | None = None,
    latest_shorts_job: dict | None = None,
    latest_tiktok_job: dict | None = None,
    channel_titles: dict | None = None,
    tiktok_account_titles: dict | None = None,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    channel_titles = channel_titles or {}
    tiktok_account_titles = tiktok_account_titles or {}
    youtube = data.get("youtube") or {}
    project_completed = data.get("status") == "completed"
    if _is_tiktok_project(data):
        tiktok = data.get("tiktok") or {}
        latest_tiktok_job = latest_tiktok_job or {}
        job_status = latest_tiktok_job.get("status") or ((tiktok.get("publishing") or {}).get("status") or "")
        scheduled_at = str(latest_tiktok_job.get("scheduledAt") or "").strip()
        scheduled_dt = _youtube_datetime(scheduled_at)
        if not project_completed:
            publish_status = "not_ready"
        elif job_status in {"leased", "upload_initialized", "uploading"}:
            publish_status = "uploading"
        elif job_status == "queued" and scheduled_dt and scheduled_dt > now:
            publish_status = "scheduled"
        elif job_status in {"completed", "inbox_delivered"}:
            publish_status = "inbox_delivered"
        elif job_status == "needs_review":
            publish_status = "needs_review"
        elif job_status == "failed":
            publish_status = "error"
        else:
            publish_status = "ready"
        if not project_completed:
            next_action = {"kind": "wait", "label": "Esperar producción"}
        elif publish_status in {"ready", "error"}:
            next_action = {"kind": "publish_tiktok", "label": "Enviar a TikTok"}
        elif publish_status == "scheduled":
            next_action = {"kind": "scheduled", "label": "Programado"}
        elif publish_status in {"inbox_delivered", "needs_review"}:
            next_action = {"kind": "review_tiktok", "label": "Abrir TikTok"}
        else:
            next_action = {"kind": "wait", "label": "Procesando"}
        account_id = latest_tiktok_job.get("accountId") or ""
        video_status = "ready" if project_completed else "not_ready"
        return {
            "id": project_id,
            "platform": "tiktok",
            "title": data.get("title") or "Sin título",
            "agentId": data.get("agentId") or "",
            "format": data.get("format") or "",
            "status": data.get("status") or "",
            "createdAt": _serialize_firestore_value(data.get("createdAt")),
            "updatedAt": _serialize_firestore_value(data.get("updatedAt")),
            "completedAt": _serialize_firestore_value(data.get("productionCompletedAt") or data.get("completedAt")),
            "channel": {"id": account_id, "title": tiktok_account_titles.get(account_id, "TikTok")},
            "video": {
                "status": video_status,
                "youtubeVideoId": "",
                "youtubeStudioUrl": "",
                "privacyStatus": "",
                "publishAt": "",
                "jobId": latest_tiktok_job.get("id") or "",
                "jobStatus": job_status,
                "warning": "" if project_completed else "Producción pendiente",
                "error": "",
                "thumbnailUploaded": None,
            },
            "shorts": {
                "status": publish_status,
                "total": 0,
                "uploaded": 0,
                "scheduled": 1 if publish_status == "scheduled" else 0,
                "uploads": [],
                "jobId": latest_tiktok_job.get("id") or "",
                "jobStatus": job_status,
                "warning": "",
                "error": latest_tiktok_job.get("error") or "",
                "errors": [],
            },
            "nextAction": next_action,
            "tiktok": _serialize_firestore_value(tiktok),
        }

    video_id = youtube.get("lastVideoId") or (latest_video_job or {}).get("youtubeVideoId") or ""
    studio_url = youtube.get("lastStudioUrl") or (latest_video_job or {}).get("youtubeStudioUrl") or ""
    publish_at = str(
        youtube.get("lastScheduledPublishAt")
        or _youtube_video_publish_at_from_job(latest_video_job)
        or ""
    ).strip()
    publish_dt = _youtube_datetime(publish_at)
    video_job_status = (latest_video_job or {}).get("status") or ""
    video_warning = (latest_video_job or {}).get("warning") or ""
    privacy_status = _youtube_video_privacy_from_job(latest_video_job) or "private"

    if not project_completed:
        video_status = "not_ready"
    elif video_job_status in {"queued", "running"}:
        video_status = "uploading"
    elif video_job_status == "error" and not video_id:
        video_status = "error"
    elif video_id and publish_dt and publish_dt > now:
        video_status = "scheduled"
    elif video_id:
        video_status = "uploaded"
    else:
        video_status = "missing"

    shorts_source = data.get("shorts") if isinstance(data.get("shorts"), list) else []
    total_shorts = len(shorts_source)
    successful_shorts = _youtube_successful_short_uploads(youtube.get("shortsUploads"))
    uploaded_shorts = len(successful_shorts)
    scheduled_shorts = _youtube_future_count(successful_shorts, now=now)
    shorts_job_status = (latest_shorts_job or {}).get("status") or ""
    shorts_job_items = (latest_shorts_job or {}).get("items") or []
    shorts_errors = [
        item for item in shorts_job_items
        if isinstance(item, dict) and item.get("status") == "error"
    ]

    if not project_completed:
        shorts_status = "not_ready"
    elif total_shorts <= 0:
        shorts_status = "none"
    elif shorts_job_status in {"queued", "running"}:
        shorts_status = "uploading"
    elif uploaded_shorts >= total_shorts:
        shorts_status = "scheduled" if scheduled_shorts else "uploaded"
    elif shorts_job_status == "error" and uploaded_shorts == 0:
        shorts_status = "error"
    elif uploaded_shorts > 0:
        shorts_status = "partial"
    else:
        shorts_status = "missing"

    if not project_completed:
        next_action = {"kind": "wait", "label": "Esperar producción"}
    elif video_status in {"missing", "error"}:
        next_action = {"kind": "publish_video", "label": "Subir video largo"}
    elif total_shorts > 0 and uploaded_shorts < total_shorts:
        next_action = {"kind": "publish_shorts", "label": "Publicar Shorts"}
    elif video_warning or shorts_errors:
        next_action = {"kind": "review", "label": "Revisar advertencias"}
    else:
        next_action = {"kind": "complete", "label": "Completo"}

    channel_id = (
        (latest_video_job or {}).get("channelId")
        or (latest_shorts_job or {}).get("channelId")
        or ""
    )
    return {
        "id": project_id,
        "title": data.get("title") or "Sin título",
        "agentId": data.get("agentId") or "",
        "platform": "youtube",
        "format": data.get("format") or "",
        "status": data.get("status") or "",
        "createdAt": _serialize_firestore_value(data.get("createdAt")),
        "updatedAt": _serialize_firestore_value(data.get("updatedAt")),
        "completedAt": _serialize_firestore_value(data.get("productionCompletedAt") or data.get("completedAt")),
        "channel": {
            "id": channel_id,
            "title": channel_titles.get(channel_id, ""),
        },
        "video": {
            "status": video_status,
            "youtubeVideoId": video_id,
            "youtubeStudioUrl": studio_url,
            "privacyStatus": privacy_status,
            "publishAt": publish_at,
            "jobId": (latest_video_job or {}).get("id") or youtube.get("lastPublishJobId") or "",
            "jobStatus": video_job_status,
            "warning": video_warning,
            "error": (latest_video_job or {}).get("error") or "",
            "thumbnailUploaded": (latest_video_job or {}).get("thumbnailUploaded"),
        },
        "shorts": {
            "status": shorts_status,
            "total": total_shorts,
            "uploaded": uploaded_shorts,
            "scheduled": scheduled_shorts,
            "uploads": _serialize_firestore_value(successful_shorts),
            "jobId": (latest_shorts_job or {}).get("id") or youtube.get("shortsLastPublishJobId") or "",
            "jobStatus": shorts_job_status,
            "warning": (latest_shorts_job or {}).get("warning") or "",
            "error": (latest_shorts_job or {}).get("error") or "",
            "errors": _serialize_firestore_value(shorts_errors),
        },
        "nextAction": next_action,
    }


def _youtube_thumbnail_candidates(video_dir: Path) -> list[Path]:
    thumbs_dir = video_dir / "thumbnails"
    if not thumbs_dir.is_dir():
        return []
    return sorted(
        [
            p for p in thumbs_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ],
        key=lambda p: p.name,
    )


def _youtube_pick_thumbnail(video_dir: Path, index: int = 0) -> Path | None:
    thumbs = _youtube_thumbnail_candidates(video_dir)
    if not thumbs:
        return None
    index = max(0, min(index, len(thumbs) - 1))
    selected = thumbs[index]
    if selected.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("thumbnail exceeds YouTube 2MB limit")
    return selected


def _youtube_project_video_dir(data: dict) -> Path:
    folder = data.get("videoFolder") or ""
    if not folder:
        raise ValueError("project has no videoFolder")
    return Path(f"/app/output/videos/{folder}")


def _youtube_video_preflight(data: dict) -> dict:
    result = {
        "durationSeconds": None,
        "durationMinutes": None,
        "isLongerThanDefaultLimit": False,
        "defaultLimitSeconds": 15 * 60,
        "filename": None,
        "hasSubtitles": False,
    }
    try:
        video_dir = _youtube_project_video_dir(data)
        if not video_dir.is_dir():
            return {**result, "warning": "project output folder not found"}
        video_file, has_subs, invalid = _pick_valid_final_video(video_dir, min_duration_seconds=1)
        if not video_file:
            return {**result, "warning": "final video not found", "invalidCandidates": invalid[:3]}
        ok, duration, err = _validate_media_file(video_file, min_duration_seconds=1)
        if not ok:
            return {**result, "warning": err or "final video duration could not be read"}
        return {
            **result,
            "durationSeconds": round(duration, 2),
            "durationMinutes": round(duration / 60, 1),
            "isLongerThanDefaultLimit": duration > 15 * 60,
            "filename": video_file.name,
            "hasSubtitles": bool(has_subs),
        }
    except Exception as exc:
        return {**result, "warning": str(exc)[:200]}


def _youtube_video_dimensions(video_path: Path) -> tuple[int, int]:
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if out.returncode != 0:
            return 0, 0
        streams = (json.loads(out.stdout or "{}").get("streams") or [])
        first = streams[0] if streams else {}
        return int(first.get("width") or 0), int(first.get("height") or 0)
    except Exception:
        return 0, 0


def _youtube_short_file(video_dir: Path, short: dict) -> Path | None:
    shorts_dir = video_dir / "shorts"
    if not shorts_dir.is_dir():
        return None
    index = int(short.get("index") or 0)
    label = re.sub(r"[^A-Za-z0-9_-]+", "", str(short.get("label") or ""))
    candidates: list[Path] = []
    if index and label:
        candidates.append(shorts_dir / f"SHORT_{index:02d}_{label}.mp4")
    if index:
        candidates.extend(sorted(shorts_dir.glob(f"SHORT_{index:02d}_*.mp4")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _youtube_short_preflight(video_dir: Path, short: dict) -> dict:
    file_path = _youtube_short_file(video_dir, short)
    result = {
        "index": int(short.get("index") or 0),
        "label": short.get("label") or "",
        "filename": file_path.name if file_path else None,
        "durationSeconds": None,
        "width": None,
        "height": None,
        "eligible": False,
        "error": "",
    }
    if not file_path:
        return {**result, "error": "short file not found on disk"}
    ok, duration, err = _validate_media_file(file_path, min_duration_seconds=1)
    width, height = _youtube_video_dimensions(file_path)
    result.update({
        "durationSeconds": round(duration, 2),
        "width": width or None,
        "height": height or None,
    })
    if not ok:
        return {**result, "error": err or "short is not readable"}
    if duration > 180:
        return {**result, "error": "short exceeds 180 seconds"}
    if not width or not height:
        return {**result, "error": "short dimensions could not be read"}
    if height < width:
        return {**result, "error": "short must be vertical or square"}
    return {**result, "eligible": True}


def _youtube_upload_video(access_token: str, video_file: Path, resource: dict) -> str:
    import requests
    size = video_file.stat().st_size
    parts = ["snippet", "status"]
    if resource.get("paidProductPlacementDetails"):
        parts.append("paidProductPlacementDetails")
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": ",".join(parts)},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": "video/mp4",
        },
        json=resource,
        timeout=30,
    )
    if init.status_code >= 400:
        raise RuntimeError(f"youtube upload init failed: {init.text[:300]}")
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise RuntimeError("youtube upload init did not return upload URL")

    with video_file.open("rb") as fh:
        upload = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(size),
            },
            data=fh,
            timeout=(30, 1800),
        )
    if upload.status_code >= 400:
        raise RuntimeError(f"youtube upload failed: {upload.text[:300]}")
    return upload.json().get("id") or ""


def _youtube_upload_thumbnail(access_token: str, video_id: str, thumbnail_file: Path | None) -> bool:
    if not thumbnail_file:
        return False
    import requests
    mime = "image/png" if thumbnail_file.suffix.lower() == ".png" else "image/jpeg"
    with thumbnail_file.open("rb") as fh:
        response = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
            params={"videoId": video_id, "uploadType": "media"},
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": mime},
            data=fh,
            timeout=120,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"youtube thumbnail upload failed: {response.text[:300]}")
    return True


def _youtube_thumbnail_warning(exc: Exception | str) -> str:
    raw = str(exc)
    lowered = raw.lower()
    if "thumbnail" in lowered and ("permission" in lowered or "403" in lowered or "forbidden" in lowered):
        return (
            "El video sí se subió, pero YouTube no permitió subir la miniatura personalizada. "
            "Esto suele pasar cuando el canal aún no tiene permisos de miniaturas personalizadas; "
            "verifícalo en YouTube Studio o súbela manualmente ahí."
        )
    if "thumbnail exceeds" in lowered or "2mb" in lowered:
        return "El video sí se subió, pero la miniatura pesa más de 2 MB. Usa una variante más ligera o súbela manualmente en YouTube Studio."
    return "El video sí se subió, pero no se pudo aplicar la miniatura personalizada. Revísala manualmente en YouTube Studio."


def _run_youtube_publish_job(uid: str, project_id: str, job_id: str, payload: dict):
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        job_ref = db.collection("youtubePublishJobs").document(job_id)
        job_ref.update({
            "status": "running",
            "step": "Preparando video y metadata",
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        project_ref = db.collection("projects").document(project_id)
        project_snap = project_ref.get()
        if not project_snap.exists:
            raise RuntimeError("project not found")
        project = project_snap.to_dict() or {}
        if project.get("userId") != uid:
            raise RuntimeError("project access denied")

        channel_id = str(payload.get("channelId") or "").strip()
        if not channel_id:
            raise RuntimeError("missing channelId")
        channel_ref = db.collection("users").document(uid).collection("youtubeChannels").document(channel_id)
        channel_snap = channel_ref.get()
        if not channel_snap.exists:
            raise RuntimeError("YouTube channel is not connected")
        channel = channel_snap.to_dict() or {}
        refresh_token = _youtube_decrypt_token(channel.get("refreshTokenEncrypted") or "")
        access = _youtube_refresh_access_token(refresh_token).get("access_token")
        if not access:
            raise RuntimeError("youtube refresh did not return access token")

        video_dir = _youtube_project_video_dir(project)
        if not video_dir.is_dir():
            raise RuntimeError("project output folder not found")
        video_file, _has_subs, _invalid = _pick_valid_final_video(video_dir, min_duration_seconds=1)
        if not video_file:
            raise RuntimeError("final video not found")
        thumb = _youtube_pick_thumbnail(video_dir, int(payload.get("thumbnailIndex") or 0))
        resource = _build_youtube_video_resource(project_id, project, payload)

        job_ref.update({
            "step": "Subiendo video a YouTube",
            "metadata": resource,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        video_id = _youtube_upload_video(access, video_file, resource)
        if not video_id:
            raise RuntimeError("YouTube did not return video id")

        thumbnail_uploaded = False
        thumbnail_warning = ""
        if thumb:
            job_ref.update({
                "step": "Subiendo miniatura",
                "youtubeVideoId": video_id,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            try:
                thumbnail_uploaded = _youtube_upload_thumbnail(access, video_id, thumb)
            except Exception as thumb_exc:
                # New YouTube channels may reject custom thumbnails until the
                # channel is verified. The upload itself is still useful, so do
                # not turn a thumbnail problem into a failed publication.
                thumbnail_warning = _youtube_thumbnail_warning(thumb_exc)[:500]

        youtube_url = f"https://studio.youtube.com/video/{video_id}/edit"
        job_ref.update({
            "status": "completed",
            "step": "Listo para revisión en YouTube Studio"
            if not thumbnail_warning
            else "Video subido; revisa la miniatura en YouTube Studio",
            "youtubeVideoId": video_id,
            "youtubeStudioUrl": youtube_url,
            "thumbnailUploaded": thumbnail_uploaded,
            "warning": thumbnail_warning,
            "completedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        project_update = {
            "youtube.lastPublishJobId": job_id,
            "youtube.lastVideoId": video_id,
            "youtube.lastStudioUrl": youtube_url,
            "youtube.lastPublishedAt": firestore.SERVER_TIMESTAMP,
        }
        if payload.get("publishAt"):
            project_update["youtube.lastScheduledPublishAt"] = payload.get("publishAt")
        project_ref.update(project_update)
    except Exception as exc:
        try:
            _ensure_firebase_initialized()
            from firebase_admin import firestore
            firestore.client().collection("youtubePublishJobs").document(job_id).update({
                "status": "error",
                "step": "Error al publicar",
                "error": str(exc)[:500],
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
        except Exception:
            pass


def _run_youtube_shorts_publish_job(uid: str, project_id: str, job_id: str, payload: dict):
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        job_ref = db.collection("youtubePublishJobs").document(job_id)
        job_ref.update({
            "status": "running",
            "step": "Preparando Shorts y metadata",
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        project_ref = db.collection("projects").document(project_id)
        project_snap = project_ref.get()
        if not project_snap.exists:
            raise RuntimeError("project not found")
        project = project_snap.to_dict() or {}
        if project.get("userId") != uid:
            raise RuntimeError("project access denied")
        if project.get("status") != "completed":
            raise RuntimeError("project is not completed")

        channel_id = str(payload.get("channelId") or "").strip()
        if not channel_id:
            raise RuntimeError("missing channelId")
        channel_ref = db.collection("users").document(uid).collection("youtubeChannels").document(channel_id)
        channel_snap = channel_ref.get()
        if not channel_snap.exists:
            raise RuntimeError("YouTube channel is not connected")
        channel = channel_snap.to_dict() or {}
        refresh_token = _youtube_decrypt_token(channel.get("refreshTokenEncrypted") or "")
        access = _youtube_refresh_access_token(refresh_token).get("access_token")
        if not access:
            raise RuntimeError("youtube refresh did not return access token")

        video_dir = _youtube_project_video_dir(project)
        if not video_dir.is_dir():
            raise RuntimeError("project output folder not found")

        selected = payload.get("shorts") if isinstance(payload.get("shorts"), list) else []
        by_index = {
            int(short.get("index") or 0): short
            for short in (project.get("shorts") or [])
            if isinstance(short, dict)
        }
        successes = []
        errors = []
        total = len(selected)
        for position, short_payload in enumerate(selected, 1):
            try:
                index = int(short_payload.get("index") or 0)
                source_short = by_index.get(index)
                if not source_short:
                    raise RuntimeError(f"short {index} not found in project")
                preflight = _youtube_short_preflight(video_dir, source_short)
                if not preflight.get("eligible"):
                    raise RuntimeError(preflight.get("error") or f"short {index} is not eligible")
                short_file = _youtube_short_file(video_dir, source_short)
                if not short_file:
                    raise RuntimeError(f"short {index} file not found")

                resource = _youtube_short_resource(project_id, project, source_short, short_payload)
                job_ref.update({
                    "step": f"Subiendo Short {position}/{total}",
                    "currentShortIndex": index,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                })
                video_id = _youtube_upload_video(access, short_file, resource)
                if not video_id:
                    raise RuntimeError("YouTube did not return video id")
                item = {
                    "index": index,
                    "label": source_short.get("label") or "",
                    "youtubeVideoId": video_id,
                    "youtubeStudioUrl": f"https://studio.youtube.com/video/{video_id}/edit",
                    "title": resource["snippet"]["title"],
                    "privacyStatus": resource["status"]["privacyStatus"],
                    "publishAt": resource["status"].get("publishAt") or "",
                    "uploadedAt": datetime.now(timezone.utc).isoformat(),
                }
                successes.append(item)
                job_ref.update({
                    "items": successes + errors,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                })
            except Exception as item_exc:
                error_item = {
                    "index": int(short_payload.get("index") or 0) if isinstance(short_payload, dict) else 0,
                    "status": "error",
                    "error": str(item_exc)[:300],
                }
                errors.append(error_item)
                job_ref.update({
                    "items": successes + errors,
                    "warning": f"{len(errors)} Short(s) con error",
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                })

        if not successes:
            detail = "; ".join(item.get("error", "") for item in errors) or "no Shorts uploaded"
            raise RuntimeError(detail[:500])

        warning = ""
        if errors:
            warning = f"Se subieron {len(successes)} de {total} Shorts. Revisa los errores antes de reintentar."

        job_ref.update({
            "status": "completed",
            "step": "Shorts listos para revisión en YouTube Studio",
            "items": successes + errors,
            "warning": warning,
            "completedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        project_ref.update({
            "youtube.shortsLastPublishJobId": job_id,
            "youtube.shortsLastPublishedAt": firestore.SERVER_TIMESTAMP,
            "youtube.shortsUploads": firestore.ArrayUnion(successes),
        })
    except Exception as exc:
        try:
            _ensure_firebase_initialized()
            from firebase_admin import firestore
            firestore.client().collection("youtubePublishJobs").document(job_id).update({
                "status": "error",
                "step": "Error al publicar Shorts",
                "error": str(exc)[:500],
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
        except Exception:
            pass


@app.get("/youtube/config")
def youtube_config(request: Request):
    _require_principal(request, allow_admin=True)
    return _youtube_config_status()


@app.get("/youtube/oauth/status")
def youtube_oauth_status():
    status = _youtube_config_status()
    return {
        "configured": status["configured"],
        "missing": status["missing"],
        "redirectUri": status.get("redirectUri"),
        "scopes": status["scopes"],
    }


@app.get("/youtube/oauth/start")
def youtube_oauth_start(request: Request, returnTo: str = "/dashboard"):
    principal = _require_principal(request)
    status = _youtube_config_status()
    if not status["configured"]:
        return JSONResponse(status_code=503, content={"error": "youtube_oauth_not_configured", **status})
    return {
        "authorizationUrl": _youtube_authorization_url(principal["uid"], returnTo),
        "redirectUri": status["redirectUri"],
        "scopes": status["scopes"],
    }


@app.get("/youtube/oauth/callback")
def youtube_oauth_callback(code: str = "", state: str = ""):
    payload = _youtube_verify_state(state)
    uid = payload["uid"]
    return_to = _safe_youtube_return_path(payload.get("returnTo"))
    tokens = _youtube_request_tokens(code)
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="youtube oauth did not return access token")
    refresh_token = tokens.get("refresh_token")
    channels = _youtube_fetch_channels(access_token)

    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    for channel in channels:
        ref = db.collection("users").document(uid).collection("youtubeChannels").document(channel["channelId"])
        existing = ref.get()
        encrypted_refresh = None
        if refresh_token:
            encrypted_refresh = _youtube_encrypt_token(refresh_token)
        elif existing.exists:
            encrypted_refresh = (existing.to_dict() or {}).get("refreshTokenEncrypted")
        if not encrypted_refresh:
            raise HTTPException(status_code=400, detail="youtube oauth did not return refresh token")
        ref.set({
            **channel,
            "refreshTokenEncrypted": encrypted_refresh,
            "scopes": list(_YOUTUBE_SCOPES),
            "connectedAt": firestore.SERVER_TIMESTAMP if not existing.exists else (existing.to_dict() or {}).get("connectedAt", firestore.SERVER_TIMESTAMP),
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    separator = "&" if "?" in return_to else "?"
    return RedirectResponse(f"{_YOUTUBE_WEB_URL}{return_to}{separator}youtube=connected")


@app.get("/youtube/channels")
def youtube_channels(request: Request):
    principal = _require_principal(request)
    status = _youtube_config_status()
    if not status["configured"]:
        return {"configured": False, "channels": [], "missing": status["missing"], "redirectUri": status.get("redirectUri")}
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    channels_ref = db.collection("users").document(principal["uid"]).collection("youtubeChannels")
    docs = list(channels_ref.stream())
    refreshed = {}
    for doc in docs:
        stored = doc.to_dict() or {}
        encrypted_refresh = stored.get("refreshTokenEncrypted")
        if not encrypted_refresh:
            continue
        try:
            access = _youtube_refresh_access_token(_youtube_decrypt_token(encrypted_refresh)).get("access_token")
            if not access:
                continue
            for channel in _youtube_fetch_channels(access):
                channel_ref = channels_ref.document(channel["channelId"])
                existing = channel_ref.get()
                channel_ref.set({
                    **channel,
                    "refreshTokenEncrypted": (
                        (existing.to_dict() or {}).get("refreshTokenEncrypted")
                        if existing.exists
                        else encrypted_refresh
                    ),
                    "connectedAt": (
                        (existing.to_dict() or {}).get("connectedAt")
                        if existing.exists
                        else firestore.SERVER_TIMESTAMP
                    ),
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }, merge=True)
                refreshed[channel["channelId"]] = channel
        except Exception as exc:
            try:
                log.warning("youtube_channel_refresh_failed", uid=principal["uid"], channel_id=doc.id, error=str(exc)[:200])
            except TypeError:
                log.warning(f"youtube_channel_refresh_failed uid={principal['uid']} channel_id={doc.id} error={str(exc)[:200]}")
    docs = list(channels_ref.stream()) if refreshed else docs
    return {"configured": True, "channels": [_youtube_public_channel_doc(doc) for doc in docs]}


@app.get("/tiktok/config")
def tiktok_config(request: Request):
    _require_principal(request, allow_admin=True)
    return _tiktok_config_status()


@app.get("/tiktok/oauth/status")
def tiktok_oauth_status():
    status = _tiktok_config_status()
    return {
        "configured": status["configured"],
        "missing": status["missing"],
        "redirectUri": status.get("redirectUri"),
        "scopes": status["scopes"],
    }


@app.get("/tiktok/oauth/start")
def tiktok_oauth_start(request: Request, returnTo: str = "/dashboard"):
    principal = _require_principal(request)
    status = _tiktok_config_status()
    if not status["configured"]:
        return JSONResponse(status_code=503, content={"error": "tiktok_oauth_not_configured", **status})
    return {
        "authorizationUrl": _tiktok_authorization_url(principal["uid"], returnTo),
        "redirectUri": status["redirectUri"],
        "scopes": status["scopes"],
    }


@app.get("/tiktok/oauth/callback")
def tiktok_oauth_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"{_TIKTOK_WEB_URL}/dashboard?tiktok=denied")
    payload = _tiktok_verify_state(state)
    uid = payload["uid"]
    return_to = _safe_tiktok_return_path(payload.get("returnTo"))
    tokens = _tiktok_request_tokens(code)
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="tiktok oauth did not return access token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="tiktok oauth did not return refresh token")
    account = _tiktok_fetch_user(access_token)
    open_id = account.get("openId") or tokens.get("open_id")
    if not open_id:
        raise HTTPException(status_code=400, detail="tiktok user lookup did not return open_id")

    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    ref = db.collection("users").document(uid).collection("tiktokAccounts").document(open_id)
    existing = ref.get()
    ref.set({
        **account,
        "openId": open_id,
        "accessTokenEncrypted": _tiktok_encrypt_token(access_token),
        "refreshTokenEncrypted": _tiktok_encrypt_token(refresh_token),
        "accessExpiresAt": datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in") or 86400)),
        "refreshExpiresAt": datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("refresh_expires_in") or 31536000)),
        "scopes": list(_TIKTOK_SCOPES),
        "connectedAt": firestore.SERVER_TIMESTAMP if not existing.exists else (existing.to_dict() or {}).get("connectedAt", firestore.SERVER_TIMESTAMP),
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)

    separator = "&" if "?" in return_to else "?"
    return RedirectResponse(f"{_TIKTOK_WEB_URL}{return_to}{separator}tiktok=connected")


@app.get("/tiktok/accounts")
def tiktok_accounts(request: Request):
    principal = _require_principal(request)
    status = _tiktok_config_status()
    if not status["configured"]:
        return {"configured": False, "accounts": [], "missing": status["missing"], "redirectUri": status.get("redirectUri")}
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    docs = list(
        firestore.client()
        .collection("users")
        .document(principal["uid"])
        .collection("tiktokAccounts")
        .stream()
    )
    return {"configured": True, "accounts": [_tiktok_public_account_doc(doc) for doc in docs]}


@app.get("/youtube/publications")
def youtube_publications(request: Request, limit: int = 120):
    principal = _require_principal(request)
    _ensure_firebase_initialized()
    from firebase_admin import firestore

    limit = max(1, min(int(limit or 120), 250))
    db = firestore.client()
    uid = principal["uid"]

    channel_docs = list(db.collection("users").document(uid).collection("youtubeChannels").stream())
    channels = [_youtube_public_channel_doc(doc) for doc in channel_docs]
    channel_titles = {
        channel["channelId"]: channel.get("title") or ""
        for channel in channels
    }
    tiktok_account_docs = list(db.collection("users").document(uid).collection("tiktokAccounts").stream())
    tiktok_accounts = [_tiktok_public_account_doc(doc) for doc in tiktok_account_docs]
    tiktok_account_titles = {
        account["accountId"]: account.get("displayName") or "TikTok"
        for account in tiktok_accounts
    }

    project_docs = list(
        db.collection("projects")
        .where("userId", "==", uid)
        .limit(limit)
        .stream()
    )
    job_docs = list(
        db.collection("youtubePublishJobs")
        .where("uid", "==", uid)
        .limit(500)
        .stream()
    )
    latest_jobs = _youtube_latest_jobs_by_project(job_docs)
    tiktok_job_docs = list(
        db.collection("tiktokPublishJobs")
        .where("uid", "==", uid)
        .limit(500)
        .stream()
    )
    latest_tiktok_jobs = _tiktok_latest_jobs_by_project(tiktok_job_docs)

    rows = []
    now = datetime.now(timezone.utc)
    for doc in project_docs:
        data = doc.to_dict() or {}
        project_jobs = latest_jobs.get(doc.id, {})
        rows.append(_youtube_publication_overview_row(
            doc.id,
            data,
            latest_video_job=project_jobs.get("video"),
            latest_shorts_job=project_jobs.get("shorts"),
            latest_tiktok_job=latest_tiktok_jobs.get(doc.id),
            channel_titles=channel_titles,
            tiktok_account_titles=tiktok_account_titles,
            now=now,
        ))

    rows.sort(
        key=lambda row: (
            _youtube_datetime(row.get("updatedAt")) or
            _youtube_datetime(row.get("createdAt")) or
            datetime.fromtimestamp(0, tz=timezone.utc)
        ),
        reverse=True,
    )

    summary = {
        "total": len(rows),
        "completed": sum(1 for row in rows if row.get("status") == "completed"),
        "needsVideo": sum(1 for row in rows if row.get("video", {}).get("status") in {"missing", "error"}),
        "needsShorts": sum(1 for row in rows if row.get("shorts", {}).get("status") in {"missing", "partial", "error"}),
        "scheduled": sum(
            1 for row in rows
            if row.get("video", {}).get("status") == "scheduled"
            or int(row.get("shorts", {}).get("scheduled") or 0) > 0
        ),
        "complete": sum(1 for row in rows if row.get("nextAction", {}).get("kind") == "complete"),
    }
    return {
        "configured": _youtube_config_status()["configured"],
        "channels": channels,
        "summary": summary,
        "items": rows,
        "tiktokAccounts": tiktok_accounts,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/youtube/publish/preview/{project_id}")
def youtube_publish_preview(project_id: str, request: Request):
    _require_project_access(request, project_id)
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    snap = firestore.client().collection("projects").document(project_id).get()
    if not snap.exists:
        return JSONResponse(status_code=404, content={"error": "project not found"})
    data = snap.to_dict() or {}
    pack = _build_youtube_publish_pack(project_id, data)
    thumbnails = data.get("thumbnails") or []
    return {
        "projectId": project_id,
        "configured": _youtube_config_status()["configured"],
        "metadata": {
            "title": pack["title"],
            "description": pack["description"],
            "tags": pack["tags"],
            "tagsCsv": pack["tags_csv"],
            "hashtags": pack["hashtags"],
            "pinnedComment": pack["pinned_comment"],
            "chapters": pack["chapters"],
        },
        "video": _youtube_video_preflight(data),
        "thumbnails": thumbnails,
        "defaults": {"privacyStatus": "private", "categoryId": "22"},
    }


@app.get("/youtube/shorts/preview/{project_id}")
def youtube_shorts_publish_preview(project_id: str, request: Request):
    principal = _require_project_access(request, project_id)
    data = principal.get("project") or {}
    pack = _build_youtube_shorts_publish_pack(project_id, data)
    preflight_by_index = {}
    try:
        video_dir = _youtube_project_video_dir(data)
        for short in data.get("shorts") or []:
            if isinstance(short, dict):
                preflight_by_index[int(short.get("index") or 0)] = _youtube_short_preflight(video_dir, short)
    except Exception as exc:
        error = str(exc)[:200]
        preflight_by_index = {
            int(short.get("index") or 0): {
                "index": int(short.get("index") or 0),
                "label": short.get("label") or "",
                "eligible": False,
                "error": error,
            }
            for short in (data.get("shorts") or [])
            if isinstance(short, dict)
        }

    shorts = []
    for short in pack["shorts"]:
        index = int(short.get("index") or 0)
        shorts.append({
            "index": index,
            "label": short.get("label") or "",
            "duration": short.get("duration"),
            "sizeMb": short.get("size_mb"),
            "signedUrl": short.get("signed_url"),
            "metadata": short.get("metadata") or {},
            "preflight": preflight_by_index.get(index, {}),
        })

    return {
        "projectId": project_id,
        "configured": _youtube_config_status()["configured"],
        "shorts": shorts,
        "defaults": {
            "privacyStatus": "private",
            "categoryId": "22",
            "scheduleOffsetsHours": pack["scheduleOffsetsHours"],
            "basePublishAt": ((data.get("youtube") or {}).get("lastScheduledPublishAt") or ""),
        },
    }


@app.get("/tiktok/publish/preview/{project_id}")
def tiktok_publish_preview(project_id: str, request: Request):
    principal = _require_project_access(request, project_id)
    data = principal.get("project") or {}
    if not _is_tiktok_project(data):
        return JSONResponse(status_code=400, content={"error": "project is not a TikTok project"})
    status = _tiktok_config_status()
    video_dir = None
    cover_url = ""
    try:
        video_dir = _youtube_project_video_dir(data)
    except Exception:
        pass
    if video_dir:
        tiktok_delivery = ((data.get("tiktok") or {}).get("delivery") or {})
        cover_url = tiktok_delivery.get("coverUrl") or ""
    return {
        "projectId": project_id,
        "configured": status["configured"],
        "missing": status["missing"],
        "redirectUri": status.get("redirectUri"),
        "metadata": _tiktok_caption_pack(project_id, data),
        "video": _tiktok_video_preflight(data),
        "cover": {
            "filename": "cover.jpg",
            "signedUrl": cover_url,
            "exists": bool(video_dir and _tiktok_cover_file(video_dir)),
        },
        "defaults": {
            "mode": "inbox_upload",
            "requiresUserReviewInTikTok": True,
            "isAigc": True,
            "brandedContent": False,
            "maxPendingSharesPer24h": 5,
        },
    }


@app.post("/tiktok/publish/schedule/{project_id}")
async def tiktok_publish_schedule(project_id: str, request: Request, background_tasks: BackgroundTasks):
    principal = _require_project_access(request, project_id)
    status = _tiktok_config_status()
    if not status["configured"]:
        return JSONResponse(status_code=503, content={"error": "tiktok_oauth_not_configured", **status})
    payload = await request.json()
    account_id = str(payload.get("accountId") or payload.get("account_id") or "").strip()
    if not account_id:
        return JSONResponse(status_code=400, content={"error": "select a TikTok account"})

    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    account_ref = db.collection("users").document(principal["uid"]).collection("tiktokAccounts").document(account_id)
    if not account_ref.get().exists:
        return JSONResponse(status_code=404, content={"error": "TikTok account not connected"})

    job_payload = _tiktok_build_publish_job_payload(
        principal["uid"],
        project_id,
        principal.get("project") or {},
        account_id,
        payload,
    )
    job_id, job_data, created = _tiktok_create_or_get_job(db, firestore, job_payload)
    dispatch = None
    if created and _tiktok_job_is_due(job_payload):
        dispatch = _enqueue_tiktok_publish_job(principal["uid"], job_id, background_tasks)
    return {
        "jobId": job_id,
        "status": job_data.get("status") or "queued",
        "created": created,
        "idempotencyKey": job_payload["idempotencyKey"],
        "scheduledAt": job_payload.get("scheduledAt") or "",
        "metadata": job_payload["metadata"],
        "dispatch": dispatch,
    }


@app.get("/tiktok/publish/jobs/{job_id}")
def tiktok_publish_job(job_id: str, request: Request):
    principal = _require_principal(request, allow_admin=True)
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    snap = firestore.client().collection("tiktokPublishJobs").document(job_id).get()
    if not snap.exists:
        return JSONResponse(status_code=404, content={"error": "job not found"})
    data = snap.to_dict() or {}
    if not principal.get("admin") and data.get("uid") != principal["uid"]:
        raise HTTPException(status_code=403, detail="job access denied")
    return {"id": snap.id, "jobId": snap.id, **_serialize_firestore_value(data)}


@app.post("/tiktok/publish/run-due")
def tiktok_publish_run_due(request: Request, background_tasks: BackgroundTasks, limit: int = 5):
    principal = _require_principal(request, allow_admin=True, allow_local=True)
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    now = datetime.now(timezone.utc)
    docs = list(
        db.collection("tiktokPublishJobs")
        .where("status", "==", "queued")
        .limit(max(1, min(int(limit or 5), 20)))
        .stream()
    )
    launched = []
    for doc in docs:
        data = doc.to_dict() or {}
        if not principal.get("admin") and data.get("uid") != principal.get("uid"):
            continue
        if not _tiktok_job_is_due(data, now=now):
            continue
        dispatch = _enqueue_tiktok_publish_job(data.get("uid"), doc.id, background_tasks)
        launched.append({"jobId": doc.id, "dispatch": dispatch})
    return {"launched": launched, "count": len(launched)}


@app.post("/youtube/publish/{project_id}")
async def youtube_publish(project_id: str, request: Request, background_tasks: BackgroundTasks):
    principal = _require_project_access(request, project_id)
    status = _youtube_config_status()
    if not status["configured"]:
        return JSONResponse(status_code=503, content={"error": "youtube_oauth_not_configured", **status})
    payload = await request.json()
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    job_ref = db.collection("youtubePublishJobs").document()
    resource_preview = _build_youtube_video_resource(project_id, db.collection("projects").document(project_id).get().to_dict() or {}, payload)
    job_ref.set({
        "uid": principal["uid"],
        "projectId": project_id,
        "channelId": payload.get("channelId"),
        "status": "queued",
        "step": "En cola para subir a YouTube",
        "metadata": resource_preview,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    background_tasks.add_task(_run_youtube_publish_job, principal["uid"], project_id, job_ref.id, payload)
    return {"jobId": job_ref.id, "status": "queued", "metadata": resource_preview}


@app.post("/youtube/shorts/publish/{project_id}")
async def youtube_shorts_publish(project_id: str, request: Request, background_tasks: BackgroundTasks):
    principal = _require_project_access(request, project_id)
    status = _youtube_config_status()
    if not status["configured"]:
        return JSONResponse(status_code=503, content={"error": "youtube_oauth_not_configured", **status})
    payload = await request.json()
    selected = payload.get("shorts") if isinstance(payload.get("shorts"), list) else []
    if not selected:
        return JSONResponse(status_code=400, content={"error": "select at least one Short"})

    data = principal.get("project") or {}
    shorts_by_index = {
        int(short.get("index") or 0): short
        for short in (data.get("shorts") or [])
        if isinstance(short, dict)
    }
    preview_resources = []
    for item in selected:
        if not isinstance(item, dict):
            continue
        source = shorts_by_index.get(int(item.get("index") or 0))
        if source:
            preview_resources.append({
                "index": int(item.get("index") or 0),
                "resource": _youtube_short_resource(project_id, data, source, item),
            })
    if not preview_resources:
        return JSONResponse(status_code=400, content={"error": "selected Shorts are not available"})

    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    job_ref = db.collection("youtubePublishJobs").document()
    job_ref.set({
        "uid": principal["uid"],
        "projectId": project_id,
        "channelId": payload.get("channelId"),
        "type": "shorts",
        "status": "queued",
        "step": "En cola para subir Shorts",
        "items": [],
        "metadata": {"shorts": preview_resources},
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    background_tasks.add_task(_run_youtube_shorts_publish_job, principal["uid"], project_id, job_ref.id, payload)
    return {"jobId": job_ref.id, "status": "queued", "metadata": {"shorts": preview_resources}}


@app.get("/youtube/publish/jobs/{job_id}")
def youtube_publish_job(job_id: str, request: Request):
    principal = _require_principal(request, allow_admin=True)
    _ensure_firebase_initialized()
    from firebase_admin import firestore
    snap = firestore.client().collection("youtubePublishJobs").document(job_id).get()
    if not snap.exists:
        return JSONResponse(status_code=404, content={"error": "job not found"})
    data = snap.to_dict() or {}
    if not principal.get("admin") and data.get("uid") != principal["uid"]:
        raise HTTPException(status_code=403, detail="job access denied")
    return {"id": snap.id, **data}


@app.get("/download/all/{project_id}")
def download_all(project_id: str, request: Request):
    """
    Streamea un ZIP con el paquete listo para publicacion:
    video/, shorts/, thumbnails/, audio/, images/ + carpetas youtube/ y tiktok/.

    Usa zipstream-ng para construir el ZIP on-the-fly (no en memoria),
    critico cuando el video final pesa 100MB+.
    """
    _require_project_access(request, project_id, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        from zipstream import ZipStream

        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()

        folder = data.get("videoFolder") or ""
        title = data.get("title") or "proyecto"
        if not folder:
            return JSONResponse(status_code=404, content={"error": "project has no videoFolder"})

        video_dir = Path(f"/app/output/videos/{folder}")
        if not video_dir.is_dir():
            return JSONResponse(
                status_code=404,
                content={"error": f"folder {folder} not found on disk"},
            )

        zs = ZipStream(sized=True)

        def add_glob(directory: Path, pattern: str, archive_subdir: str):
            if not directory.is_dir():
                return
            for f in sorted(directory.glob(pattern)):
                if f.is_file():
                    zs.add_path(str(f), arcname=f"{folder}/{archive_subdir}/{f.name}")

        def add_if(file_path: Path, arcname_rel: str):
            if file_path.is_file():
                zs.add_path(str(file_path), arcname=f"{folder}/{arcname_rel}")

        # Videos finales (con y sin subtítulos)
        for mp4 in sorted(video_dir.glob("FINAL_*.mp4")):
            zs.add_path(str(mp4), arcname=f"{folder}/video/{mp4.name}")

        # Audio final. Las narraciones individuales y clips intermedios se omiten:
        # hacen el paquete enorme y no son necesarios para publicar en YouTube.
        add_if(video_dir / "master_audio.mp3", "audio/master.mp3")

        # Imágenes
        add_glob(video_dir / "images", "*.png", "images")
        add_glob(video_dir / "images", "*.jpg", "images")

        # Material de publicación
        add_glob(video_dir / "shorts", "*.mp4", "shorts")
        add_glob(video_dir / "thumbnails", "*.jpg", "thumbnails")
        add_glob(video_dir / "thumbnails", "*.png", "thumbnails")
        add_glob(video_dir / "tiktok", "*.json", "tiktok")
        add_glob(video_dir / "tiktok", "*.txt", "tiktok")
        add_glob(video_dir / "tiktok", "*.jpg", "tiktok")

        # Otros activos sueltos del root del folder
        add_if(video_dir / "subtitles.ass", "subtitulos.ass")
        add_if(video_dir / "subtitles_tiktok.ass", "subtitulos_tiktok.ass")
        add_if(video_dir / "transcript.json", "transcripcion.json")

        # Guión desde Firestore (no está en disco como .txt)
        script_text = (data.get("script") or {}).get("plain") or ""
        if script_text:
            zs.add(script_text.encode("utf-8"), arcname=f"{folder}/guion.txt")

        publish_pack = _build_youtube_publish_pack(project_id, data)
        youtube_files = {
            "youtube/titulo.txt": publish_pack["title"],
            "youtube/descripcion.txt": publish_pack["description"],
            "youtube/hashtags.txt": " ".join(publish_pack["hashtags"]),
            "youtube/tags.txt": publish_pack["tags_csv"],
            "youtube/comentario_fijado.txt": publish_pack["pinned_comment"],
            "youtube/checklist_publicacion.md": publish_pack["checklist"],
            "youtube/metadata_youtube.json": json.dumps(
                publish_pack,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
        }
        if publish_pack.get("chapters"):
            youtube_files["youtube/capitulos.txt"] = "\n".join(publish_pack["chapters"])
        for rel_path, content in youtube_files.items():
            zs.add(str(content).encode("utf-8"), arcname=f"{folder}/{rel_path}")

        # Metadata del proyecto en JSON
        meta = {
            "id": project_id,
            "title": title,
            "agentId": data.get("agentId"),
            "platform": data.get("platform") or "youtube",
            "format": data.get("format"),
            "createdAt": str(data.get("createdAt")),
            "completedAt": str(data.get("completedAt")),
            "hasSubtitles": data.get("hasSubtitles"),
            "videoFolder": folder,
            "videoSizeMB": data.get("videoSizeMB"),
            "viralityScore": data.get("viralityScore"),
            "seo_metadata": data.get("seo_metadata"),
            "youtube": publish_pack,
            "tiktok": data.get("tiktok") or {},
            "scenesCount": len(data.get("scenes") or []),
            "downloadedAt": datetime.now(timezone.utc).isoformat(),
        }
        zs.add(
            json.dumps(meta, indent=2, default=str).encode("utf-8"),
            arcname=f"{folder}/proyecto.json",
        )

        # Sanitizar nombre del archivo descargado
        safe_filename = "".join(c if (c.isalnum() or c in "_-") else "_" for c in folder)[:100]

        return StreamingResponse(
            iter(zs),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}.zip"',
                "Content-Length": str(len(zs)),
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:300]})


@app.get("/download/video/{project}")
def download_video(project: str, request: Request):
    """Descarga el video final ensamblado."""
    _require_project_access(request, project, allow_admin=True)
    video_dir = Path(f"/app/output/videos/{project}")
    video_file, _has_subs, invalid_candidates = _pick_valid_final_video(video_dir, min_duration_seconds=1)
    if not video_file:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Valid final video not found in {video_dir}",
                "invalid_candidates": invalid_candidates[:5],
            },
        )
    
    file_size = video_file.stat().st_size
    safe_name = video_file.name.encode('ascii', 'ignore').decode('ascii') or "video.mp4"
    return FileResponse(
        video_file,
        media_type="video/mp4",
        filename=safe_name,
        headers={
            "Content-Length": str(file_size),
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        }
    )

@app.get("/download/images/{project}")
def download_images_zip(project: str, request: Request):
    """Descarga todas las imágenes del proyecto como ZIP."""
    _require_project_access(request, project, allow_admin=True)
    import zipfile
    images_dir = Path(f"/app/output/videos/{project}/images")
    if not images_dir.exists():
        return {"error": "Images not found"}
    
    zip_path = Path(f"/tmp/{project}_images.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for img in sorted(images_dir.glob("scene_*.png")):
            zf.write(img, img.name)
    
    file_size = zip_path.stat().st_size
    safe_name = f"{project}_imagenes.zip".encode('ascii', 'ignore').decode('ascii')
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=safe_name,
        headers={
            "Content-Length": str(file_size),
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "no-cache",
        }
    )

@app.get("/")
def health_check():
    return {"status": "online", "service": "Content Factory API"}


@app.get("/queue/status/{task_id}")
def queue_status(task_id: str, request: Request):
    """
    Estado de un job en la cola Celery. Útil para debug y para que
    el frontend pueda confirmar que un job sigue vivo.
    """
    _require_admin(request)
    try:
        from worker_app import celery_app
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "state": result.state,        # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": str(result.result) if result.ready() else None,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.get("/queue/health")
def queue_health(request: Request):
    """Verifica que el broker (Redis) esté accesible y haya workers conectados."""
    _require_admin(request)
    try:
        from worker_app import celery_app
        i = celery_app.control.inspect(timeout=2)
        active = i.active() or {}
        scheduled = i.scheduled() or {}
        registered = i.registered() or {}
        worker_count = len(active)
        return {
            "broker_connected": worker_count > 0 or registered != {},
            "workers": worker_count,
            "active_tasks": sum(len(v) for v in active.values()),
            "scheduled_tasks": sum(len(v) for v in scheduled.values()),
            "worker_names": list(active.keys()) if active else list(registered.keys()),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.get("/metrics")
def metrics(request: Request):
    """
    Snapshot operacional del sistema. Pensado para chequeo rápido del operador
    (curl o dashboard interno futuro), no expuesto al usuario final.

    Devuelve:
      - jobs.active: proyectos en producción ahora mismo
      - jobs.completed_24h: producciones exitosas últimas 24h
      - jobs.errored_24h: producciones con error últimas 24h
      - sizes.total_storage_mb: suma de videoSizeMB de todos los completados
      - api_uptime_seconds: cuánto lleva corriendo este worker
    """
    _require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        # Solo agregamos métricas baratas (sin scan completo de la colección).
        # En producción a escala, esto debe migrar a contadores agregados o cache.
        all_projects = list(db.collection("projects").stream())

        completed_24h = 0
        errored_24h = 0
        total_size_mb = 0.0
        capacity = _production_capacity_snapshot(db)

        for p in all_projects:
            d = p.to_dict() or {}
            status = d.get("status", "")
            size = d.get("videoSizeMB")
            if isinstance(size, (int, float)):
                total_size_mb += size
            completed_at = d.get("completedAt")
            if completed_at and hasattr(completed_at, "timestamp"):
                if datetime.fromtimestamp(completed_at.timestamp(), tz=timezone.utc) >= cutoff:
                    if status == "completed":
                        completed_24h += 1
                    elif status == "error":
                        errored_24h += 1

        uptime = (datetime.now(timezone.utc) - _STARTED_AT).total_seconds()

        return {
            "jobs": {
                "active": capacity["active"],
                "started_24h": capacity["started_24h"],
                "completed_24h": completed_24h,
                "errored_24h": errored_24h,
                "total_known": len(all_projects),
                "limits": {
                    "paused": capacity["paused"],
                    "max_active": capacity["max_active"],
                    "max_24h": capacity["max_24h"],
                },
            },
            "storage": {
                "total_video_mb": round(total_size_mb, 1),
            },
            "api": {
                "uptime_seconds": int(uptime),
                "uptime_human": _humanize_seconds(uptime),
                "started_at": _STARTED_AT.isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/credits/request")
async def request_credit_activation(request: Request):
    """Registra una solicitud de activación de créditos para revisión admin."""
    principal = _require_principal(request)
    uid = principal["uid"]
    token = principal.get("token") or {}

    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        user_ref = db.collection("users").document(uid)
        snap = user_ref.get()
        base = {}
        if not snap.exists:
            email = token.get("email") or ""
            base = {
                "uid": uid,
                "email": email,
                "displayName": token.get("name") or (email.split("@")[0] if email else "Usuario"),
                "photoURL": token.get("picture"),
                "plan": "free",
                "credits": {"included": 1, "used": 0, "extra": 0},
                "totalVideosCreated": 0,
                "createdAt": firestore.SERVER_TIMESTAMP,
            }

        user_ref.set({
            **base,
            "lastActive": firestore.SERVER_TIMESTAMP,
            "creditRequest": {
                "status": "pending",
                "requestedAt": firestore.SERVER_TIMESTAMP,
            },
        }, merge=True)
        return {"ok": True, "status": "pending"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.get("/admin/users")
def admin_users(request: Request):
    """Vista operacional de usuarios, créditos y producciones activas."""
    _require_admin(request)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()

        project_counts = {}
        for project in db.collection("projects").stream():
            data = project.to_dict() or {}
            uid = data.get("userId") or "unknown"
            item = project_counts.setdefault(uid, {"total": 0, "active": 0, "completed": 0, "error": 0})
            item["total"] += 1
            status = data.get("status")
            if status == "producing":
                item["active"] += 1
            elif status == "completed":
                item["completed"] += 1
            elif status == "error":
                item["error"] += 1

        users = []
        for doc in db.collection("users").stream():
            data = doc.to_dict() or {}
            counts = _credits_remaining(data)
            users.append({
                "uid": doc.id,
                "email": data.get("email") or "",
                "displayName": data.get("displayName") or "",
                "plan": data.get("plan") or "free",
                "credits": counts,
                "rawCredits": _serialize_firestore_value(data.get("credits") or {}),
                "creditRequest": _serialize_firestore_value(data.get("creditRequest") or {}),
                "lastActive": _serialize_firestore_value(data.get("lastActive")),
                "createdAt": _serialize_firestore_value(data.get("createdAt")),
                "projects": project_counts.get(doc.id, {"total": 0, "active": 0, "completed": 0, "error": 0}),
            })

        users.sort(
            key=lambda u: (
                0 if (u.get("creditRequest") or {}).get("status") == "pending" else 1,
                u.get("lastActive") or "",
            ),
            reverse=False,
        )
        return {"ok": True, "users": users[:250]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.get("/admin/credit-ledger")
def admin_credit_ledger(request: Request, limit: int = 50):
    """Últimos movimientos de créditos para auditoría operacional."""
    _require_admin(request)
    limit = max(1, min(200, _safe_int(limit, 50)))
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()

        query = (
            db.collection("creditLedger")
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        entries = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            data["id"] = doc.id
            entries.append(_serialize_firestore_value(data))
        return {"ok": True, "entries": entries}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/admin/users/{uid}/credits")
async def admin_grant_user_credits(uid: str, request: Request):
    """Concede créditos extra. Solo admin; los usuarios no pueden autootorgarse saldo."""
    principal = _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    amount = _safe_int(body.get("amount"), 1)
    if amount < 1 or amount > 25:
        raise HTTPException(status_code=400, detail="amount must be between 1 and 25")

    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        user_ref = db.collection("users").document(uid)
        admin_email = ((principal.get("token") or {}).get("email") or principal.get("uid") or "admin")

        @firestore.transactional
        def _txn(transaction):
            snap = user_ref.get(transaction=transaction)
            if not snap.exists:
                raise HTTPException(status_code=404, detail="user not found")
            before = _credits_remaining(snap.to_dict() or {})
            extra_increment = _extra_increment_for_grant(before, amount)
            after = _balance_after_delta(before, extra_delta=extra_increment)
            transaction.update(user_ref, {
                "credits.extra": firestore.Increment(extra_increment),
                "creditRequest.status": "approved",
                "creditRequest.approvedAt": firestore.SERVER_TIMESTAMP,
                "creditRequest.approvedBy": admin_email,
                "lastActive": firestore.SERVER_TIMESTAMP,
            })
            _write_credit_ledger(
                db,
                firestore,
                uid=uid,
                entry_type="grant",
                amount=amount,
                reason="admin_credit_grant",
                actor=admin_email,
                balance_before=before,
                balance_after=after,
                metadata={
                    "extraIncrement": extra_increment,
                    "debtCovered": max(0, extra_increment - amount),
                },
                transaction=transaction,
            )

        _txn(db.transaction())
        updated = user_ref.get().to_dict() or {}
        return {
            "ok": True,
            "uid": uid,
            "credits": _credits_remaining(updated),
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


_STARTED_AT = datetime.now(timezone.utc)


def _humanize_seconds(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    h = s // 3600
    return f"{h}h {(s % 3600) // 60}m"


def _create_project_with_credit(
    *,
    principal: dict,
    payload: dict,
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    project_extra: dict | None = None,
    credit_metadata: dict | None = None,
    ledger_reason: str = "project_create",
) -> dict:
    uid = principal["uid"]
    token = principal.get("token") or {}

    _ensure_firebase_initialized()
    from firebase_admin import firestore
    db = firestore.client()
    user_ref = db.collection("users").document(uid)
    project_ref = db.collection("projects").document()

    if dry_run:
        user_snap = user_ref.get()
        if user_snap.exists:
            counts = _credits_remaining(user_snap.to_dict() or {})
        else:
            counts = _credits_remaining({
                "credits": {"included": 1, "used": 0, "extra": 0},
            })
        if counts["remaining"] <= 0:
            raise HTTPException(status_code=402, detail="insufficient credits")
        return {
            "ok": True,
            "dryRun": True,
            "wouldCreateProject": True,
            "wouldChargeCredits": 1,
            "creditsRemaining": max(0, counts["remaining"] - 1),
            "agentId": payload["agent_id"],
            "agentFile": payload["agent_file"],
            "platform": payload.get("platform") or "youtube",
            "format": payload.get("format") or "",
            "tiktok": payload.get("tiktok") or {},
            "brandProfileId": payload.get("brand_profile_id") or "",
            "brandProfile": payload.get("brand_profile_snapshot") or {},
            "personalization": payload.get("personalization") or {},
            "generationOptions": payload.get("generation_options") or {},
        }

    @firestore.transactional
    def _txn(transaction):
        user_snap = user_ref.get(transaction=transaction)
        if user_snap.exists:
            profile = user_snap.to_dict() or {}
            counts = _credits_remaining(profile)
            if counts["remaining"] <= 0:
                raise HTTPException(status_code=402, detail="insufficient credits")
            after_counts = _balance_after_delta(counts, used_delta=1)
            transaction.update(user_ref, {
                "credits.used": firestore.Increment(1),
                "lastActive": firestore.SERVER_TIMESTAMP,
            })
        else:
            email = token.get("email") or ""
            display_name = token.get("name") or (email.split("@")[0] if email else "Usuario")
            profile = {
                "uid": uid,
                "email": email,
                "displayName": display_name,
                "photoURL": token.get("picture"),
                "plan": "free",
                "credits": {"included": 1, "used": 0, "extra": 0},
                "totalVideosCreated": 0,
            }
            counts = _credits_remaining(profile)
            if counts["remaining"] <= 0:
                raise HTTPException(status_code=402, detail="insufficient credits")
            after_counts = _balance_after_delta(counts, used_delta=1)
            transaction.set(user_ref, {
                **profile,
                "credits": {"included": 1, "used": 1, "extra": 0},
                "createdAt": firestore.SERVER_TIMESTAMP,
                "lastActive": firestore.SERVER_TIMESTAMP,
            })

        metadata = {"agentId": payload["agent_id"]}
        if credit_metadata:
            metadata.update(credit_metadata)
        _write_credit_ledger(
            db,
            firestore,
            uid=uid,
            entry_type="consume",
            amount=-1,
            reason=ledger_reason,
            actor=uid,
            project_id=project_ref.id,
            balance_before=counts,
            balance_after=after_counts,
            metadata=metadata,
            transaction=transaction,
        )

        project_data = {
            "userId": uid,
            "title": payload["title"],
            "agentId": payload["agent_id"],
            "agentFile": payload["agent_file"],
            "platform": payload.get("platform") or "youtube",
            "format": payload.get("format") or "",
            "status": "draft",
            "progress": {
                "currentStep": 0,
                "totalSteps": 6,
                "stepName": "Preparando tu proyecto...",
                "percent": 5,
            },
            "script": {
                "plain": "",
                "tagged": "",
                "wordCount": 0,
                "estimatedMinutes": 0,
                "approved": False,
            },
            "scenes": [],
            "voice": {"style": "narrative", "speed": 1.0, "pitch": 0},
            "output": {},
            "seo": {},
            "tiktok": payload.get("tiktok") or {},
            "brandProfileId": payload.get("brand_profile_id") or "",
            "brandProfile": payload.get("brand_profile_snapshot") or {},
            "costs": {"creditCost": 1},
            "personalization": payload.get("personalization") or {},
            "generationOptions": payload.get("generation_options") or {},
            "creditCharged": True,
            "creditChargedAt": firestore.SERVER_TIMESTAMP,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "completedAt": None,
        }
        if project_extra:
            project_data.update(project_extra)
        transaction.set(project_ref, project_data)
        return counts

    counts = _txn(db.transaction())
    background_tasks.add_task(
        run_script,
        payload["title"],
        payload["agent_file"],
        project_ref.id,
        payload.get("generation_options") or {},
    )
    return {
        "ok": True,
        "projectId": project_ref.id,
        "creditsRemaining": max(0, counts["remaining"] - 1),
    }


@app.post("/projects/create")
async def create_project(request: Request, background_tasks: BackgroundTasks):
    """
    Crea un proyecto y descuenta 1 crédito en una transacción atómica.
    El cliente solo muestra disponibilidad; la autoridad económica vive aquí.
    """
    principal = _require_principal(request)
    body = await request.json()
    payload = _validate_project_payload(body)
    dry_run = bool(body.get("dryRun")) or request.query_params.get("dryRun", "").lower() in {
        "1",
        "true",
        "yes",
    }

    try:
        return _create_project_with_credit(
            principal=principal,
            payload=payload,
            background_tasks=background_tasks,
            dry_run=dry_run,
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.delete("/projects/{project_id}")
def delete_project(project_id: str, request: Request):
    """
    Elimina un proyecto y devuelve el crédito solo si no se generó guion.
    El reembolso es transaccional e idempotente: sin documento no hay doble refund.
    """
    principal = _require_principal(request, allow_admin=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        project_ref = db.collection("projects").document(project_id)

        @firestore.transactional
        def _txn(transaction):
            snap = project_ref.get(transaction=transaction)
            if not snap.exists:
                raise HTTPException(status_code=404, detail="project not found")
            project = snap.to_dict() or {}
            owner_uid = project.get("userId")
            if not principal.get("admin") and owner_uid != principal["uid"]:
                raise HTTPException(status_code=403, detail="project access denied")

            script = project.get("script") or {}
            has_script = bool(_safe_int(script.get("wordCount"), 0) > 0 or script.get("plain"))
            refunded = False
            next_used = None

            if not has_script and owner_uid:
                user_ref = db.collection("users").document(owner_uid)
                user_snap = user_ref.get(transaction=transaction)
                if user_snap.exists:
                    counts = _credits_remaining(user_snap.to_dict() or {})
                    after_counts = _balance_after_delta(counts, used_delta=-1)
                    next_used = after_counts["used"]
                    transaction.update(user_ref, {
                        "credits.used": next_used,
                        "lastActive": firestore.SERVER_TIMESTAMP,
                    })
                    refunded = counts["used"] > next_used
                    if refunded:
                        _write_credit_ledger(
                            db,
                            firestore,
                            uid=owner_uid,
                            entry_type="refund",
                            amount=1,
                            reason="project_deleted_before_script",
                            actor=principal.get("uid", "admin"),
                            project_id=project_id,
                            balance_before=counts,
                            balance_after=after_counts,
                            transaction=transaction,
                        )

            transaction.delete(project_ref)
            return {"refunded": refunded, "hasScript": has_script, "creditsUsed": next_used}

        result = _txn(db.transaction())
        return {"ok": True, "projectId": project_id, **result}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.post("/generate")
async def trigger_generation(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    topic = data.get("topic")
    agent_file = data.get("agentFile", "agent_erotico_historico.md")
    project_id = data.get("projectId")
    generation_options = data.get("generationOptions") or data.get("generation_options") or {}
    
    if not topic:
        return {"status": "error", "message": "Missing 'topic' in request body"}

    principal = _require_principal(request, allow_admin=True)
    if project_id and not principal.get("admin"):
        _require_project_access(request, project_id)
    elif not project_id and not principal.get("admin"):
        raise HTTPException(status_code=403, detail="projectId required")

    # Ejecutar en segundo plano para no dejar colgada la petición HTTP a n8n
    background_tasks.add_task(run_script, topic, agent_file, project_id, generation_options)
    
    return {
        "status": "accepted", 
        "message": f"Generation started for '{topic}' with agent '{agent_file}' (Project: {project_id})"
    }

@app.post("/produce")
async def trigger_production(request: Request, background_tasks: BackgroundTasks):
    """
    Encola la producción del video en la cola Celery.
    Devuelve inmediato con un task_id (no bloquea esperando que termine).
    Workers paralelos pickan el job y lo ejecutan; si uno muere, otro retoma.

    Antes de encolar verifica el gate de moderacion: si el guion tiene
    flags CRITICOS y el usuario no envio overrideModeration:true, bloquea.
    """
    data = await request.json()
    project_id = data.get("projectId")
    override_moderation = bool(data.get("overrideModeration", False))
    script_plain = data.get("scriptPlain")
    if isinstance(script_plain, str):
        script_plain = script_plain.strip()
        if len(script_plain) > 250_000:
            raise HTTPException(status_code=400, detail="script too long")
    else:
        script_plain = None

    if not project_id:
        return {"status": "error", "message": "Missing 'projectId'"}

    _require_project_access(request, project_id)

    # Moderation gate — solo bloquea si hay critical_blocks Y no hay override
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if doc.exists:
            mod = (doc.to_dict() or {}).get("moderation") or {}
            critical = mod.get("critical_blocks") or []
            if critical and not override_moderation:
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "blocked",
                        "reason": "content_moderation",
                        "critical_blocks": critical,
                        "message": "El contenido tiene flags críticos. Revisa y reenvía con overrideModeration:true para forzar.",
                    },
                )
    except Exception as gate_err:
        # Si el gate falla, no bloquees produccion. Solo loggea + Sentry.
        print(f"[API] moderation gate check failed (non-blocking): {gate_err}", flush=True)
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(gate_err)
        except Exception:
            pass

    # Idempotency lock: previene encolado duplicado por doble click o race UI.
    # Si ya hay un job vigente (<5min) para este project_id, devuelve el
    # task original sin encolar otro. Un job que realmente murió libera el
    # lock al finalizar (o expira a los 5min para no bloquear retries reales).
    lock_result = _try_acquire_production_lock(project_id)
    if not lock_result.get("acquired"):
        existing = lock_result.get("existing_lock_id", "unknown")
        age = lock_result.get("age_sec", 0)
        print(f"[API] /produce duplicate detected for {project_id}; existing lock {existing[:8]}... age={age}s")
        return {
            "status": "queued",
            "task_id": existing,
            "project_id": project_id,
            "moderation_overridden": override_moderation,
            "duplicate_blocked": True,
            "message": f"Production already in progress (started {age}s ago)",
        }

    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        _assert_production_capacity(db)
    except HTTPException:
        _release_production_lock(project_id, lock_result.get("lock_id"))
        raise
    except Exception as capacity_err:
        _release_production_lock(project_id, lock_result.get("lock_id"))
        raise HTTPException(status_code=503, detail=f"production capacity check failed: {str(capacity_err)[:120]}")

    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()
        update_data = {
            "script.approved": True,
            "status": "producing",
            "progress.percent": 2,
            "progress.stepName": "Iniciando producción...",
        }
        if script_plain:
            update_data["script.plain"] = script_plain
        db.collection("projects").document(project_id).update(update_data)
    except Exception as update_err:
        _release_production_lock(project_id, lock_result.get("lock_id"))
        raise HTTPException(status_code=500, detail=f"project update failed: {str(update_err)[:120]}")

    try:
        from worker_tasks import produce_video
        task = produce_video.delay(project_id)
        return {
            "status": "queued",
            "task_id": task.id,
            "project_id": project_id,
            "moderation_overridden": override_moderation,
            "message": f"Production enqueued for project {project_id}",
        }
    except Exception as queue_err:
        # Fallback defensivo: si Redis/Celery no está disponible (worker container
        # caído, network down), corremos inline como antes para no romper UX.
        # Sentry captura el problema; el operador debe revisar.
        print(f"[API] queue unavailable, falling back to inline: {queue_err}", flush=True)
        # Liberar lock antes de fallback inline (run_production lo re-toma o lo
        # dejará al final de su propio flujo)
        _release_production_lock(project_id, lock_result.get("lock_id"))
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(queue_err)
        except Exception:
            pass
        background_tasks.add_task(run_production, project_id)
        return {
            "status": "accepted",
            "fallback": "inline",
            "message": f"Production started inline for project {project_id} (queue unavailable)",
        }

@app.post("/retry")
async def retry_production(request: Request, background_tasks: BackgroundTasks):
    """Resetea estado de un proyecto con error y re-lanza producción."""
    data = await request.json()
    project_id = data.get("projectId")
    
    if not project_id:
        return {"status": "error", "message": "Missing 'projectId'"}

    _require_project_access(request, project_id)
    
    # Resetear estado en Firebase
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        try:
            firebase_admin.get_app()
        except ValueError:
            cred_path = "/app/firebase-admin.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return {"status": "error", "message": "Project not found"}
        
        # Idempotency lock antes de resetear status (evita doble retry).
        lock_result = _try_acquire_production_lock(project_id)
        if not lock_result.get("acquired"):
            existing = lock_result.get("existing_lock_id", "unknown")
            age = lock_result.get("age_sec", 0)
            print(f"[API] /retry duplicate detected for {project_id}; existing lock {existing[:8]}... age={age}s")
            return {
                "status": "queued",
                "task_id": existing,
                "project_id": project_id,
                "duplicate_blocked": True,
                "message": f"Retry already in progress (started {age}s ago)",
            }

        try:
            _assert_production_capacity(db)
        except HTTPException:
            _release_production_lock(project_id, lock_result.get("lock_id"))
            raise

        # Resetear a estado "produced" para re-lanzar
        doc_ref.update({
            "status": "producing",
            "progress.percent": 5,
            "progress.stepName": "Reiniciando producción...",
        })

        # Encolar via Celery (mismo patron que /produce)
        try:
            from worker_tasks import produce_video
            task = produce_video.delay(project_id)
            return {
                "status": "queued",
                "task_id": task.id,
                "project_id": project_id,
                "message": f"Retry enqueued for project {project_id}",
            }
        except Exception as queue_err:
            print(f"[API] queue unavailable on retry, falling back to inline: {queue_err}", flush=True)
            _release_production_lock(project_id, lock_result.get("lock_id"))
            background_tasks.add_task(run_production, project_id)
            return {
                "status": "accepted",
                "fallback": "inline",
                "message": f"Retry started inline for project {project_id}",
            }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/reset-status")
async def reset_project_status(request: Request):
    """Resetea el estado de un proyecto para permitir re-producción desde la UI."""
    data = await request.json()
    project_id = data.get("projectId")
    new_status = data.get("status", "produced")
    
    if not project_id:
        return {"status": "error", "message": "Missing 'projectId'"}

    _require_project_access(request, project_id, allow_admin=True)
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        try:
            firebase_admin.get_app()
        except ValueError:
            cred_path = "/app/firebase-admin.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc_ref.update({
            "status": new_status,
            "progress.percent": 0,
            "progress.stepName": "",
        })
        
        return {"status": "ok", "message": f"Project reset to '{new_status}'"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/recover-from-disk/{project_id}")
async def recover_from_disk(project_id: str, request: Request):
    """
    Recupera un proyecto cuyo video FINAL_SUB_*.mp4 quedó en disco del VPS
    pero NO subió a Storage ni se completó en Firestore. Esto pasa cuando el
    padre Python (run_production) muere por SoftTimeLimit o subprocess timeout
    pero el subprocess de factory.py sigue corriendo y termina el video.

    Acción:
      1. Lee el proyecto y busca el folder real de producción.
      2. Busca FINAL_SUB_*.mp4 (preferido) o FINAL_*.mp4 en disco.
      3. Sube a Firebase Storage (videos/{project_id}/{filename}).
      4. Actualiza Firestore con status=completed + videoUrl + videoFolder + etc.

    Retorna {ok, video_url, message}. NO hay costo en APIs externas.
    """
    _require_project_access(request, project_id, allow_admin=True, allow_local=True)
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore

        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})

        data = doc.to_dict() or {}
        title = data.get("title") or ""
        if not title:
            return JSONResponse(status_code=400, content={"error": "project has no title"})

        folders_checked = _candidate_video_folders(
            title,
            project_id,
            stored_folder=data.get("videoFolder"),
        )
        video_dir = None
        safe_title = None
        for folder in folders_checked:
            candidate_dir = Path(f"/app/output/videos/{folder}")
            if candidate_dir.is_dir():
                video_dir = candidate_dir
                safe_title = folder
                break

        if not video_dir or not safe_title:
            return JSONResponse(
                status_code=404,
                content={"error": "production folder not on disk", "folders_checked": folders_checked},
            )

        # Preferir versión con subtítulos
        candidates = sorted(video_dir.glob("FINAL_SUB_*.mp4"))
        if not candidates:
            candidates = sorted(video_dir.glob("FINAL_*.mp4"))
        if not candidates:
            candidates = []

        # Tomar el más reciente válido por mtime. Antes se tomaba cualquier MP4,
        # incluso si FFmpeg murió antes de escribir el moov atom.
        final_path = None
        invalid_candidates = []
        for candidate in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
            ok, duration, err = _is_valid_media_file(candidate, min_duration_seconds=30)
            if ok:
                final_path = candidate
                break
            invalid_candidates.append({
                "name": candidate.name,
                "size_mb": round(candidate.stat().st_size / (1024 * 1024), 1),
                "duration": round(duration, 3),
                "error": err,
            })

        recovery_info = {"used": False}
        if final_path is None:
            final_path, recovery_info = _remux_recovered_final(video_dir, safe_title)
        if final_path is None:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "no valid FINAL_*.mp4 found and remux from masters failed",
                    "invalid_candidates": invalid_candidates,
                    "recovery": recovery_info,
                },
            )

        has_subs = "FINAL_SUB_" in final_path.name

        print(f"🔧 [RECOVER] Subiendo {final_path.name} ({final_path.stat().st_size // (1024*1024)} MB) para {project_id}")
        storage_info = _upload_video_to_storage(final_path, project_id)
        if not storage_info:
            return JSONResponse(status_code=500, content={"error": "Storage upload failed"})

        valid_final, final_duration, final_error = _is_valid_media_file(final_path, min_duration_seconds=30)
        if not valid_final:
            return JSONResponse(
                status_code=500,
                content={"error": f"validated final became invalid after upload candidate selection: {final_error}"},
            )

        update_payload = {
            "status": "completed",
            "progress.percent": 100,
            "progress.stepName": "Entrega recuperada correctamente",
            "videoPath": str(final_path),
            "videoFolder": safe_title,
            "hasSubtitles": has_subs,
            "videoDurationSeconds": round(final_duration, 1),
            "videoSizeMB": round(final_path.stat().st_size / (1024 * 1024), 1),
            "videoStoragePath": storage_info["gs_path"],
            "videoUrl": storage_info["signed_url"],
            "videoUrlExpiresAt": firestore.SERVER_TIMESTAMP,
            "recoveredFromDisk": True,
            "recoveryInfo": recovery_info,
            # Limpiar lock viejo (si quedó de un job que murió sin liberar)
            "productionLockId": firestore.DELETE_FIELD,
            "productionLockedAt": firestore.DELETE_FIELD,
        }
        doc_ref.update(update_payload)

        return {
            "ok": True,
            "video_url": storage_info["signed_url"],
            "video_folder": safe_title,
            "size_mb": round(final_path.stat().st_size / (1024 * 1024), 1),
            "duration_seconds": round(final_duration, 1),
            "has_subtitles": has_subs,
            "recovery": recovery_info,
            "invalid_candidates": invalid_candidates,
            "message": f"Project {project_id} recovered from disk (no API costs)",
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:300]})


def run_script(topic, agent_file, project_id, generation_options=None):
    print(f"🚀 [API] Starting background job for '{topic}' with '{agent_file}' (Project: {project_id})...", flush=True)
    try:
        generation_options = generation_options or {}
        if not generation_options and project_id:
            try:
                _ensure_firebase_initialized()
                from firebase_admin import firestore
                snap = firestore.client().collection("projects").document(project_id).get()
                if snap.exists:
                    project_data = snap.to_dict() or {}
                    generation_options = project_data.get("generationOptions") or {}
                    if (
                        project_data.get("personalization")
                        and not generation_options.get("personalization")
                    ):
                        generation_options = {
                            **generation_options,
                            "personalization": project_data.get("personalization"),
                        }
                    if (
                        project_data.get("brandProfileId")
                        and not generation_options.get("brand_profile_id")
                    ):
                        generation_options = {
                            **generation_options,
                            "brand_profile_id": project_data.get("brandProfileId"),
                            "brand_profile_snapshot": project_data.get("brandProfile") or {},
                        }
            except Exception as options_err:
                print(f"   ⚠️ generationOptions lookup skipped: {options_err}", flush=True)
        # Import directo — sin subprocess, para que los errores aparezcan en logs
        import sys
        sys.path.insert(0, "/app")
        from scripts.generate_content import run_full_pipeline
        result = run_full_pipeline(topic, agent_file, project_id, generation_options=generation_options)
        if result:
            print(f"✅ [API] Pipeline completed successfully for '{topic}'", flush=True)
            # Moderation gate — corre justo despues de generar el guion para
            # que el usuario vea el verdict antes de aprobar a produccion.
            try:
                _ensure_firebase_initialized()
                from firebase_admin import firestore
                db = firestore.client()
                doc = db.collection("projects").document(project_id).get()
                if doc.exists:
                    script_text = (doc.to_dict().get("script") or {}).get("plain") or ""
                    if script_text:
                        mod = check_content_moderation(script_text)
                        db.collection("projects").document(project_id).update({
                            "moderation": mod,
                        })
                        print(f"   🛡️ Moderation: {mod['verdict']} | crit={len(mod['critical_blocks'])} | warn={len(mod['warnings'])}", flush=True)

                        # Fact-checking en paralelo conceptual (despues de moderation)
                        try:
                            fc = fact_check_script(script_text, topic_hint=topic)
                            db.collection("projects").document(project_id).update({
                                "factCheck": fc,
                            })
                            s = fc["summary"]
                            print(f"   📚 FactCheck: {s['total']} claims | alta={s['high']} media={s['medium']} baja={s['low']}", flush=True)
                        except Exception as fc_err:
                            print(f"   ⚠️ Fact-check failed (no bloqueante): {fc_err}", flush=True)
            except Exception as mod_err:
                print(f"   ⚠️ Moderation/FactCheck failed (no bloqueante): {mod_err}", flush=True)
        else:
            print(f"⚠️ [API] Pipeline returned None for '{topic}' — check Firebase for error status", flush=True)
    except Exception as e:
        import traceback
        print(f"❌ [API] Error running script: {e}", flush=True)
        traceback.print_exc()
        # Reportar error a Firebase
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            try:
                firebase_admin.get_app()
            except ValueError:
                cred_path = "/app/firebase-admin.json"
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
            db = firestore.client()
            db.collection("projects").document(project_id).update({
                "status": "error",
                "progress.stepName": f"Error: {str(e)[:150]}",
                "progress.percent": 0,
            })
        except Exception as fb_err:
            print(f"❌ [API] Also failed to report error to Firebase: {fb_err}", flush=True)

def run_production(project_id):
    """Ejecuta el pipeline cinemático: FLUX → ElevenLabs → Luma → Ken Burns → Ensamblaje."""
    _tag_sentry_project(project_id, pipeline="production")
    import firebase_admin
    from firebase_admin import credentials, firestore
    from pathlib import Path
    import threading
    import time
    # Importar lazy: si celery no está instalado (script standalone), no romper.
    try:
        from celery.exceptions import SoftTimeLimitExceeded
    except ImportError:
        class SoftTimeLimitExceeded(Exception):
            pass

    print(f"🏭 [PRODUCE] Starting CINEMATIC production for project {project_id}...")
    
    # Inicializar Firebase con storageBucket (necesario para upload del video final)
    try:
        _ensure_firebase_initialized()
    except Exception as init_err:
        print(f"❌ [PRODUCE] firebase init failed: {init_err}")
        return

    db = firestore.client()
    doc_ref = db.collection("projects").document(project_id)
    
    def update_progress(percent, step_name, status="producing"):
        # Compare-and-swap: NUNCA sobreescribir un proyecto ya completado con
        # un status intermedio. Threads monitor zombies (que sobreviven a
        # excepciones del proceso padre) escriben en bucle y rompen la UX al
        # regresar un proyecto "completed" a "producing 85%". Solo permitimos
        # transiciones desde estados intermedios o desde error.
        try:
            current = doc_ref.get().to_dict() or {}
            current_status = current.get("status")
            if current_status == "completed" and status != "completed":
                # Drop silencioso: no spammear logs por cada tick del monitor zombie
                return
            current_percent = (current.get("progress") or {}).get("percent") or 0
            if status != "error" and current_status != "script_ready" and percent < current_percent:
                return
        except Exception:
            pass  # Si la lectura falla, dejar pasar la escritura (defensivo)

        doc_ref.update({
            "status": status,
            "progress.percent": percent,
            "progress.stepName": step_name,
        })
        print(f"   [{percent}%] {step_name}")
    
    try:
        # Leer datos del proyecto desde Firebase
        project = doc_ref.get().to_dict()
        if not project:
            print("❌ [PRODUCE] Project not found in Firebase")
            return
        production_start = time.time()

        # Idempotencia: si Celery re-encola un job ya completado (ej. worker
        # muere después de escribir status=completed pero antes del ACK por
        # acks_late + reject_on_worker_lost), no re-correr el pipeline. Para
        # forzar regeneración real, usar /retry — que sí resetea status.
        if _completed_project_has_valid_delivery(project):
            print(f"⏭️  [PRODUCE] Project {project_id} ya está completed (videoUrl presente). Skipping retry idempotente.")
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"Idempotency guard hit: re-run skipped for {project_id}",
                    level="warning",
                )
            except Exception:
                pass
            return
        if project.get("status") == "completed" and project.get("videoUrl"):
            print(
                f"⚠️ [PRODUCE] Project {project_id} estaba completed pero sin duración válida; "
                "continuando para reparar entrega.",
                flush=True,
            )
        doc_ref.update({
            "productionStartedAt": firestore.SERVER_TIMESTAMP,
            "productionStartedFromStatus": project.get("status"),
        })

        title = project.get("title", "video_sin_titulo")
        scenes = project.get("scenes", [])
        agent_id = project.get("agentId", "")
        project_format = project.get("format") or ""
        is_tiktok_project = _is_tiktok_project(project)

        if not scenes:
            update_progress(0, "Error: No hay escenas visuales", "error")
            return
        
        # Crear JSON compatible con factory.py.
        # El folder incluye project_id para evitar cache cruzado entre videos
        # con el mismo título; factory.py recibe el mismo output_folder.
        safe_title = _project_output_slug(title, project_id)
        doc_ref.update({"videoFolder": safe_title})
        
        # Detectar formatos especiales. Podcast necesita dialogue_blocks para
        # dual TTS; autohipnosis necesita preservar su etiqueta de formato para
        # visuales y filename.
        is_podcast_project = (
            project_format in {"podcast", "tiktok_podcast"}
            or (agent_id or "").startswith("agent_podcast_")
        )
        is_autohypnosis_project = (
            project_format == "autohipnosis"
            or agent_id == "agent_autohipnosis"
        )
        is_long_meditation_project = (
            project_format == "meditacion_larga"
            or agent_id == "agent_meditacion_larga"
        )

        # Mapear scenes de Firestore al formato factory.py
        factory_scenes = []
        for s in scenes:
            scene_dict = {
                "scene_number": s.get("scene_number", s.get("sceneNumber", 0)),
                "prompt": s.get("prompt", ""),
                "narration": s.get("narration_text", s.get("narration", "")),
            }
            target_duration = s.get("target_duration_seconds", s.get("targetDurationSeconds"))
            if target_duration:
                scene_dict["target_duration_seconds"] = target_duration
            for visual_key in (
                "public_figure_subject",
                "public_figure_visual_context",
                "visual_source",
                "visualSource",
                "archive_reference_id",
                "archiveReference",
                "archive_image_local_path",
                "archiveImageLocalPath",
            ):
                if visual_key in s:
                    scene_dict[visual_key] = s[visual_key]
            # Para podcast, propagar dialogue_blocks (los necesita la dual TTS)
            if is_podcast_project and s.get("dialogue_blocks"):
                scene_dict["dialogue_blocks"] = s["dialogue_blocks"]
                scene_dict["narration_text"] = s.get("narration_text", "")
            factory_scenes.append(scene_dict)

        temp_json = {
            "topic": title,
            "project_id": project_id,
            "output_folder": safe_title,
            "agent": agent_id,
            "platform": "tiktok" if is_tiktok_project else "youtube",
            "video_scenes": factory_scenes,
            "seo_metadata": project.get("seo_metadata", {"title": title}),
            "brandProfileId": project.get("brandProfileId") or "",
            "brandProfile": project.get("brandProfile") or {},
            "publicFigureVisuals": project.get("publicFigureVisuals") or {},
        }
        if is_tiktok_project:
            temp_json["format"] = project_format
            temp_json["tiktok"] = project.get("tiktok") or {}
            if project_format == "tiktok_podcast":
                temp_json["podcast"] = project.get("podcast", {
                    "show_name": "Esto no es amor",
                    "host_a": {"name": "Mateo", "voice": "Will"},
                    "host_b": {"name": "Lucía", "voice": "Lina"},
                    "platform": "tiktok",
                })
            elif project_format in {"tiktok_autohypnosis", "tiktok_meditation"}:
                temp_json["autohipnosis"] = project.get("autohipnosis") or {}
        elif is_podcast_project:
            temp_json["format"] = "podcast"
            # Reusa la podcast config persistida en Firestore (host_a/host_b voices, etc.)
            # Defaults actualizados 2026-05-03: Will + Lina (eleven_v3 con audio
            # tags). Salvatore + Serafina quedan para documentales (eleven v2).
            temp_json["podcast"] = project.get("podcast", {
                "show_name": "Esto no es amor",
                "host_a": {"name": "Mateo", "voice": "Will"},
                "host_b": {"name": "Lucía", "voice": "Lina"},
            })
        elif is_autohypnosis_project:
            temp_json["format"] = "autohipnosis"
            temp_json["autohipnosis"] = project.get("autohipnosis") or {}
        elif is_long_meditation_project:
            temp_json["format"] = "meditacion_larga"
            temp_json["longMeditation"] = project.get("longMeditation") or {}
        temp_path = f"/app/output/scripts/PRODUCE_{safe_title}.json"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(temp_json, f, ensure_ascii=False, indent=2)
        
        # ═══════════════════════════════════════════
        # Directorios del proyecto
        # ═══════════════════════════════════════════
        images_dir = Path(f"/app/output/videos/{safe_title}/images")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # ═══════════════════════════════════════════
        # PASO 1: Generar visuales base (5% → 35%)
        # ═══════════════════════════════════════════
        
        # Detectar imágenes existentes para evitar regenerar
        existing_numbers = _valid_scene_image_numbers(images_dir)
        expected_numbers = {
            _scene_number_from_payload(scene)
            for scene in scenes
            if _scene_number_from_payload(scene)
        }
        existing_count = len(existing_numbers.intersection(expected_numbers))
        
        if existing_count >= len(scenes):
            print(f"   ✅ {existing_count}/{len(scenes)} imágenes ya existen — reutilizando")
            image_sync = _sync_scene_image_urls(doc_ref, scenes, safe_title, images_dir)
            update_progress(35, f"{image_sync['ready']} visuales preparados", "imaging")
        else:
            update_progress(5, f"Creando {len(scenes)} visuales... ({existing_count} preparados)", "imaging")
            
            # Monitorear progreso de imágenes
            stop_monitoring = threading.Event()
            
            def monitor_images():
                vps_base = os.environ.get("VPS_PUBLIC_URL", "http://100.99.207.113:8085")
                reported = set()
                while not stop_monitoring.is_set():
                    time.sleep(8)
                    existing = sorted(images_dir.glob("scene_*.png"))
                    for img in existing:
                        if img.name not in reported and img.name.count(".") == 1 and img.stat().st_size > 1000:
                            reported.add(img.name)
                            try:
                                num = int(img.stem.split("_")[1])
                                image_url = f"{vps_base}/images/{safe_title}/{img.name}"
                                updated_scenes = doc_ref.get().to_dict().get("scenes", [])
                                for s in updated_scenes:
                                    sn = s.get("scene_number", s.get("sceneNumber", 0))
                                    if sn == num:
                                        s["imageUrl"] = image_url
                                        break
                                doc_ref.update({"scenes": updated_scenes})
                                pct = 5 + int((len(reported) / len(scenes)) * 30)
                                update_progress(pct, f"Visual {len(reported)}/{len(scenes)} listo", "imaging")
                            except Exception as e:
                                print(f"   ⚠️ Monitor error: {e}")
            
            monitor_thread = threading.Thread(target=monitor_images, daemon=True)
            monitor_thread.start()

            # factory.py con --images-only en process group propio +
            # finally que mata subprocess + monitor thread aunque haya
            # excepción (SoftTimeLimitExceeded, KeyboardInterrupt, etc.).
            returncode, stderr_tail = _run_factory_subprocess(
                ["python", "scripts/factory.py", temp_path, "--mode", "narrativa" if is_tiktok_project else "cinematico", "--images-only"],
                monitor_thread=monitor_thread,
                stop_event=stop_monitoring,
                timeout=7200,
                log_label="factory-images",
            )

            if returncode != 0:
                update_progress(0, f"Error creando visuales", "error")
                print(f"STDERR: {stderr_tail}")
                return

            image_sync = _sync_scene_image_urls(doc_ref, scenes, safe_title, images_dir)
            if image_sync["missing"]:
                doc_ref.update({
                    "status": "error",
                    "progress.percent": 35,
                    "progress.stepName": "Error: visuales incompletos",
                    "visuals.recoveryRequired": True,
                    "visuals.missing": image_sync["missing"],
                })
                try:
                    import sentry_sdk
                    sentry_sdk.capture_message(
                        f"Image stage incomplete for {project_id}: {image_sync['missing']}",
                        level="error",
                    )
                except Exception:
                    pass
                return

            update_progress(35, f"{image_sync['ready']} visuales base listos", "imaging")
        
        # ═══════════════════════════════════════════
        # PASO 2-4: Voz + movimiento + montaje (35% → 94%)
        # ═══════════════════════════════════════════
        update_progress(42, "Grabando voces...", "voicing")
        
        # Ejecutar factory.py completo (skip-images ya que las tenemos)
        # Monitorear progreso por pasos
        def monitor_factory():
            """Monitorea los archivos generados para actualizar progreso."""
            audio_dir = Path(f"/app/output/videos/{safe_title}/audio")
            kb_dir = Path(f"/app/output/videos/{safe_title}/kenburns")
            luma_dir = Path(f"/app/output/videos/{safe_title}/luma_clips")
            master_audio = Path(f"/app/output/videos/{safe_title}/master_audio.mp3")
            master_visual = Path(f"/app/output/videos/{safe_title}/master_visual.mp4")
            
            while not stop_monitoring.is_set():
                time.sleep(5)
                try:
                    # Audio progress (42% → 60%)
                    audio_count = len(list(audio_dir.glob("narration_*.mp3"))) if audio_dir.exists() else 0
                    if audio_count > 0 and audio_count < len(scenes):
                        pct = 42 + int((audio_count / len(scenes)) * 18)
                        update_progress(pct, f"Voz {audio_count}/{len(scenes)}", "voicing")
                    elif audio_count >= len(scenes):
                        update_progress(60, "Voz completa", "voicing")
                        # Motion/visual render progress (60% → 80%)
                        kb_count = len(list(kb_dir.glob("scene_*.mp4"))) if kb_dir.exists() else 0
                        if kb_count > 0 and kb_count < len(scenes):
                            pct = 60 + int((kb_count / len(scenes)) * 18)
                            update_progress(pct, f"Movimiento {kb_count}/{len(scenes)}", "assembling")
                        elif kb_count >= len(scenes):
                            update_progress(80, "Montando la película final", "assembling")
                            luma_count = len(list(luma_dir.glob("luma_*.mp4"))) if luma_dir.exists() else 0
                            if luma_count > 0:
                                update_progress(82, f"Movimiento premium: {luma_count}", "assembling")
                    if master_audio.exists() and master_audio.stat().st_size > 0:
                        update_progress(62, "Mezcla de audio lista", "assembling")
                    if master_visual.exists() and master_visual.stat().st_size > 0:
                        update_progress(86, "Montaje final en curso", "assembling")
                    valid_final, _has_subs, _invalid = _pick_valid_final_video(
                        Path(f"/app/output/videos/{safe_title}"),
                        min_duration_seconds=30,
                    )
                    if valid_final:
                        update_progress(90, "Película final ensamblada", "assembling")
                except:
                    pass
        
        stop_monitoring = threading.Event()
        factory_monitor = threading.Thread(target=monitor_factory, daemon=True)
        factory_monitor.start()

        # factory.py completo en process group propio. El helper garantiza
        # que monitor_factory thread se DETIENE en el finally aunque haya
        # SoftTimeLimitExceeded, evitando el "thread monitor zombie" que
        # sobreescribía status=completed con producing 85%. Timeout subido
        # de 3600 → 7200 (cinematico con 99 escenas tarda hasta 1h25m).
        factory_cmd = [
            "python", "scripts/factory.py", temp_path,
            "--mode", "narrativa" if is_tiktok_project else "cinematico", "--skip-images",
        ]
        if not is_tiktok_project:
            factory_cmd.extend(["--luma-scenes", "8"])
        if is_long_meditation_project:
            factory_cmd.append("--skip-subs")
        returncode, stderr_tail = _run_factory_subprocess(
            factory_cmd,
            monitor_thread=factory_monitor,
            stop_event=stop_monitoring,
            timeout=10500,  # 175min — debajo del soft_time_limit Celery (180min)
            log_label="factory-full",
        )

        if returncode != 0:
            update_progress(35, f"Error durante el montaje final", "error")
            print(f"STDERR: {stderr_tail}")
            return
        
        # ═══════════════════════════════════════════
        # PASO EXTRA: Subtítulos explícitos (fallback)
        # ═══════════════════════════════════════════
        video_dir = Path(f"/app/output/videos/{safe_title}")
        final_candidate, candidate_has_subs, invalid_candidates = _pick_valid_final_video(video_dir)
        
        if not candidate_has_subs and not is_long_meditation_project:
            # factory.py no generó subtítulos — intentar directamente
            update_progress(92, "Generando subtítulos...", "assembling")
            
            if final_candidate:
                try:
                    sys.path.insert(0, "/app/scripts")
                    if is_tiktok_project:
                        from generate_subtitles import add_tiktok_subtitles_to_video as _add_subtitles
                    else:
                        from generate_subtitles import add_subtitles_to_video as _add_subtitles

                    master_audio = video_dir / "master_audio.mp3"
                    if not master_audio.exists():
                        master_audio = _build_master_audio(video_dir)

                    if master_audio is None or not master_audio.exists() or master_audio.stat().st_size == 0:
                        print("   ⚠️ Sin audio maestro válido — saltando subtítulos")
                    else:
                        print(f"   🎤 Audio maestro listo ({master_audio.stat().st_size // 1024} KB) → Whisper")
                        subtitled = _add_subtitles(
                            video_path=final_candidate,
                            audio_path=master_audio,
                        )
                        if subtitled:
                            final_candidate = subtitled
                            candidate_has_subs = True
                            print(f"   ✅ Subtítulos generados: {subtitled.name}")
                        else:
                            print("   ⚠️ Subtítulos fallaron — continuando sin subs")
                except Exception as sub_err:
                    print(f"   ⚠️ Error subtítulos: {sub_err}")
        
        # ═══════════════════════════════════════════
        # COMPLETADO
        # ═══════════════════════════════════════════
        # Refrescar selección después del paso de subtítulos y validar con ffprobe
        final_candidate, candidate_has_subs, invalid_candidates = _pick_valid_final_video(video_dir)
        if not final_candidate:
            print("   🔧 FINAL inválido o ausente; intentando remux automático desde masters", flush=True)
            remuxed, recovery_info = _remux_recovered_final(video_dir, safe_title)
            if remuxed:
                final_candidate = remuxed
                candidate_has_subs = False
                print(f"   ✅ Remux automático listo: {remuxed.name} ({recovery_info})", flush=True)

        if final_candidate:
            final_path = str(final_candidate)
            has_subs = candidate_has_subs
        else:
            if invalid_candidates:
                print(f"   ⚠️ No hay FINAL válido. Candidatos inválidos: {invalid_candidates[:5]}", flush=True)
            final_path = ""
            has_subs = False

        if not final_path:
            update_progress(0, "Error: no se pudo validar el video final", "error")
            return

        final_ok, final_duration, final_err = _is_valid_media_file(Path(final_path), min_duration_seconds=30)
        if not final_ok:
            print(f"   ⚠️ Video final inválido antes de entrega: {final_err}", flush=True)
            update_progress(0, "Error: no se pudo validar el video final", "error")
            return
        
        # Subir video final a Firebase Storage para entrega via CDN (sin pegar al VPS)
        storage_info = None
        if final_path:
            update_progress(96, "Preparando entrega...", "publishing")
            storage_info = _upload_video_to_storage(Path(final_path), project_id)
            if not storage_info:
                doc_ref.update({
                    "status": "error",
                    "progress.percent": 96,
                    "progress.stepName": "Error: no se pudo preparar la entrega",
                    "videoPath": final_path,
                    "videoFolder": safe_title,
                    "videoDurationSeconds": round(final_duration, 1),
                    "videoSizeMB": round(Path(final_path).stat().st_size / (1024 * 1024), 1),
                    "deliveryRecoverableFromDisk": True,
                    "deliveryError": "storage_upload_failed",
                    "videoStoragePath": firestore.DELETE_FIELD,
                    "videoUrl": firestore.DELETE_FIELD,
                    "videoUrlExpiresAt": firestore.DELETE_FIELD,
                })
                print(
                    f"   ⚠️ Video local válido, pero Storage falló. Proyecto marcado error recuperable: {final_path}",
                    flush=True,
                )
                try:
                    import sentry_sdk
                    sentry_sdk.capture_message(
                        f"Storage upload failed after valid render for {project_id}",
                        level="error",
                    )
                except Exception:
                    pass
                return

        # Generar shorts vertical 9:16 (3 momentos del video final)
        # No bloqueante: si falla, el video largo ya está completado.
        shorts_results = []
        if final_path and storage_info and not is_long_meditation_project and not is_tiktok_project:
            try:
                update_progress(97, "Creando versiones cortas...", "publishing")
                shorts_results = build_shorts_for_project(video_dir, project_id)
                print(f"   📱 Shorts generados: {len(shorts_results)}/3", flush=True)
            except Exception as shorts_err:
                print(f"   ⚠️ Shorts generation failed (no bloqueante): {shorts_err}", flush=True)
                try:
                    import sentry_sdk
                    sentry_sdk.capture_exception(shorts_err)
                except Exception:
                    pass

        # Generar thumbnails (3 variantes a partir de imágenes existentes)
        thumbnails_results = []
        if storage_info and not is_tiktok_project:
            try:
                update_progress(99, "Diseñando miniaturas...", "publishing")
                project_title = project.get("title", "")
                project_agent_id = project.get("agentId", "")
                thumbnails_results = build_thumbnails_for_project(
                    video_dir,
                    project_id,
                    project_title,
                    agent_id=project_agent_id,
                )
                print(f"   🖼️ Thumbnails generados: {len(thumbnails_results)}/3", flush=True)
            except Exception as thumb_err:
                print(f"   ⚠️ Thumbnails generation failed (no bloqueante): {thumb_err}", flush=True)
                try:
                    import sentry_sdk
                    sentry_sdk.capture_exception(thumb_err)
                except Exception:
                    pass

        tiktok_cover_file = video_dir / "tiktok" / "cover.jpg"
        tiktok_cover_result = None
        if storage_info and is_tiktok_project:
            if tiktok_cover_file.is_file():
                tiktok_cover_result = _upload_video_to_storage(
                    tiktok_cover_file,
                    f"{project_id}/tiktok",
                    content_type="image/jpeg",
                )
                if tiktok_cover_result:
                    print("   ✅ Portada TikTok subida a Storage", flush=True)
                else:
                    print("   ⚠️ Portada TikTok creada pero no se pudo subir a Storage", flush=True)

        if is_tiktok_project:
            status_msg = "Tu TikTok está listo"
        elif is_long_meditation_project:
            status_msg = "Tu sesión está lista"
        else:
            status_msg = "Tu video está listo" if not has_subs else "Tu video con subtítulos está listo"

        update_payload = {
            "status": "completed",
            "progress.percent": 100,
            "progress.stepName": status_msg,
            "videoPath": final_path,
            "videoFolder": safe_title,
            "hasSubtitles": has_subs,
            "productionCompletedAt": firestore.SERVER_TIMESTAMP,
            "productionDurationSeconds": round(time.time() - production_start, 1),
        }
        if storage_info:
            update_payload["videoStoragePath"] = storage_info["gs_path"]
            update_payload["videoUrl"] = storage_info["signed_url"]
            update_payload["videoUrlExpiresAt"] = firestore.SERVER_TIMESTAMP
            update_payload["videoSizeMB"] = round(Path(final_path).stat().st_size / (1024 * 1024), 1)
            update_payload["videoDurationSeconds"] = round(final_duration, 1)
        if shorts_results:
            update_payload["shorts"] = shorts_results
        if thumbnails_results:
            update_payload["thumbnails"] = thumbnails_results
        if is_tiktok_project:
            update_payload["platform"] = "tiktok"
            update_payload["format"] = project_format
            update_payload["tiktok.status"] = "ready"
            update_payload["tiktok.delivery.finalFile"] = Path(final_path).name
            if tiktok_cover_file.is_file():
                update_payload["tiktok.delivery.coverFile"] = "cover.jpg"
            if tiktok_cover_result:
                update_payload["tiktok.delivery.coverStoragePath"] = tiktok_cover_result["gs_path"]
                update_payload["tiktok.delivery.coverUrl"] = tiktok_cover_result["signed_url"]

        doc_ref.update(update_payload)

        print(f"🏆 [PRODUCE] Cinematic production complete! Subs: {has_subs} | Storage: {bool(storage_info)} | Shorts: {len(shorts_results)} | Thumbs: {len(thumbnails_results)} | {final_path}")

    except SoftTimeLimitExceeded:
        # Celery soft time limit. NO la atrapamos como error genérico — la
        # re-raiseamos para que worker_tasks.produce_video la propague y
        # Celery NO trate el task como completado exitosamente. De lo
        # contrario el except Exception de abajo escribiría status=error
        # pero retornaría sin re-raise → Celery hace ack normal pero
        # acks_late + reject_on_worker_lost terminan re-encolando el job.
        print(f"⏱️  [PRODUCE] SoftTimeLimitExceeded para {project_id}; propagando a Celery")
        try:
            doc_ref.update({
                "status": "error",
                "progress.percent": 0,
                "progress.stepName": "La producción tardó más de lo esperado",
            })
        except Exception:
            pass
        raise
    except Exception as e:
        update_progress(0, "Error: se detuvo la producción", "error")
        print(f"❌ [PRODUCE] Error: {e}")
    finally:
        # SIEMPRE liberar el lock de producción al terminar (éxito, error,
        # SoftTimeLimit). Sin esto, un retry legítimo posterior se bloquearía
        # como "duplicado" hasta que el lock expire (5min). El lock se
        # autolibera por TTL pero limpiar explícitamente es mejor UX.
        try:
            _release_production_lock(project_id)
        except Exception:
            pass


