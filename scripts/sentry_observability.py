SENTRY_REDACTED = "[Filtered]"
SENTRY_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "token",
    "secret",
    "password",
    "private_key",
    "api_key",
    "apikey",
    "credential",
    "x-admin-token",
)


def sentry_key_is_sensitive(key: str) -> bool:
    key_l = str(key or "").lower().replace("-", "_")
    return any(part.replace("-", "_") in key_l for part in SENTRY_SENSITIVE_KEY_PARTS)


def scrub_sentry_payload(value, parent_key: str = ""):
    if sentry_key_is_sensitive(parent_key):
        return SENTRY_REDACTED
    if isinstance(value, dict):
        return {
            k: (SENTRY_REDACTED if sentry_key_is_sensitive(k) else scrub_sentry_payload(v, str(k)))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub_sentry_payload(item, parent_key) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_sentry_payload(item, parent_key) for item in value)
    if isinstance(value, str):
        parent_l = str(parent_key or "").lower()
        if parent_l == "query_string" and value:
            return SENTRY_REDACTED
        if parent_l == "url" and "?" in value:
            return value.split("?", 1)[0] + "?[Filtered]"
    return value


def sanitize_sentry_event(event, hint):
    if not isinstance(event, dict):
        return event
    for key in ("request", "extra", "contexts", "tags", "user"):
        if key in event:
            event[key] = scrub_sentry_payload(event[key], key)
    return event


def tag_sentry_project(project_id: str, **context) -> None:
    """Agrega contexto minimo de proyecto al scope actual de Sentry."""
    try:
        import sentry_sdk
        if project_id:
            sentry_sdk.set_tag("project_id", project_id)
        clean_context = {k: v for k, v in context.items() if v is not None}
        if clean_context:
            sentry_sdk.set_context("content_factory_project", clean_context)
    except Exception:
        pass
