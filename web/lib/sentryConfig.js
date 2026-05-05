const REDACTED = "[Filtered]";
const SENSITIVE_KEY_PARTS = [
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
];

function keyIsSensitive(key) {
  const normalized = String(key || "").toLowerCase().replaceAll("-", "_");
  return SENSITIVE_KEY_PARTS.some((part) => normalized.includes(part.replaceAll("-", "_")));
}

function scrubValue(value, parentKey = "") {
  if (keyIsSensitive(parentKey)) return REDACTED;

  if (Array.isArray(value)) {
    return value.map((item) => scrubValue(item, parentKey));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        keyIsSensitive(key) ? REDACTED : scrubValue(item, key),
      ])
    );
  }

  if (typeof value === "string") {
    const parent = String(parentKey || "").toLowerCase();
    if (parent === "query_string" && value) return REDACTED;
    if (parent === "url" && value.includes("?")) {
      return `${value.split("?", 1)[0]}?[Filtered]`;
    }
  }

  return value;
}

export function getSentryDsn() {
  return process.env.NEXT_PUBLIC_SENTRY_DSN || "";
}

export function getSentryEnvironment() {
  return process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.VERCEL_ENV || process.env.NODE_ENV;
}

export function sanitizeSentryEvent(event) {
  if (!event || typeof event !== "object") return event;

  for (const key of ["request", "extra", "contexts", "tags", "user"]) {
    if (event[key]) {
      event[key] = scrubValue(event[key], key);
    }
  }

  return event;
}

export function sanitizeSentryBreadcrumb(breadcrumb) {
  if (!breadcrumb || typeof breadcrumb !== "object") return breadcrumb;
  if (breadcrumb.category === "console") return null;
  if (breadcrumb.data) {
    breadcrumb.data = scrubValue(breadcrumb.data, "data");
  }
  return breadcrumb;
}

export function getSentryBaseOptions() {
  return {
    dsn: getSentryDsn(),
    environment: getSentryEnvironment(),
    sendDefaultPii: false,
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.05 : 0,
    beforeSend: sanitizeSentryEvent,
    beforeBreadcrumb: sanitizeSentryBreadcrumb,
    ignoreErrors: [
      "ResizeObserver loop completed with undelivered notifications.",
      "ResizeObserver loop limit exceeded",
    ],
  };
}
