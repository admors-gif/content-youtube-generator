const LIVE_STATUSES = new Set([
  "draft",
  "researching",
  "scripting",
  "prompting",
  "producing",
  "imaging",
  "voicing",
  "assembling",
  "rendering",
  "subtitling",
  "publishing",
]);

const PROVIDER_PATTERNS = [
  [/Subiendo\s+a\s+Storage/gi, "Preparando entrega"],
  [/\bcon\s+FLUX\b/gi, ""],
  [/\bFLUX(?:\s+Krea\s+Dev)?\b/gi, "visuales"],
  [/\bcon\s+ElevenLabs\b|\bcon\s+Eleven Labs\b/gi, ""],
  [/\bElevenLabs\b|\bEleven Labs\b/gi, "voz"],
  [/\bClaude(?:\s+(?:Opus|Sonnet|Haiku|3\.5|4(?:\.5)?))?\b/gi, "el estudio"],
  [/\bAnthropic\b/gi, "el estudio"],
  [/\bGPT[-\w.]*\b|\bOpenAI\b/gi, "el estudio"],
  [/\bLuma(?:\s+AI)?\b/gi, "movimiento"],
  [/\bWhisper\b/gi, "subtítulos"],
  [/\bTavily\b|\bComfyUI?\b|\bFirebase\b|\bFirestore\b|\bStorage\b|\bVPS\b|\bn8n\b|\bAPI\b/gi, ""],
  [/\b(?:model|modelo)\s*[:=]\s*[-\w.]+/gi, ""],
];

export function clampProgressPercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(100, numeric));
}

export function isLiveProgressStatus(status) {
  return LIVE_STATUSES.has(status);
}

export function normalizeProgressPercent(project) {
  const status = project?.status;
  const raw = clampProgressPercent(project?.progress?.percent);

  if (status === "completed") return 100;
  if (status === "failed" || status === "error") return Math.min(raw, 99);
  if (!isLiveProgressStatus(status)) return Math.min(raw, 99);

  return Math.min(raw, 99);
}

export function sanitizeOperationalText(text = "") {
  let safe = String(text || "");
  for (const [pattern, replacement] of PROVIDER_PATTERNS) {
    safe = safe.replace(pattern, replacement);
  }
  return safe
    .replace(/[🎨🎙️🎬🎥🎞️📝☁️✂️🖼️🏆✅⚠️🔧🚀❌⏱️]/gu, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+\.\.\./g, "...")
    .replace(/\s+([,.])/g, "$1")
    .trim();
}

export function userDeliveryError(message = "") {
  const safe = sanitizeOperationalText(message).toLowerCase();
  if (!safe) return "La entrega aún no está disponible. Inténtalo de nuevo en un momento.";
  if (
    safe.includes("not found") ||
    safe.includes("no video") ||
    safe.includes("not available") ||
    safe.includes("no disponible")
  ) {
    return "La entrega final aún se está preparando. Inténtalo de nuevo en un momento.";
  }
  if (safe.includes("auth") || safe.includes("permission") || safe.includes("denied")) {
    return "Tu sesión no pudo autorizar esta acción. Vuelve a entrar e inténtalo otra vez.";
  }
  return sanitizeOperationalText(message);
}
