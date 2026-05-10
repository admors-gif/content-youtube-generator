export const RADAR_SCOPE_OPTIONS = [
  { id: "global", label: "Global" },
  { id: "news", label: "Noticias" },
  { id: "agent", label: "Por agente" },
];

export const RADAR_WINDOW_OPTIONS = [
  { id: "today", label: "Hoy" },
  { id: "week", label: "Semana" },
  { id: "evergreen", label: "Evergreen" },
];

export const RADAR_CATEGORY_OPTIONS = [
  { id: "all", label: "Todas" },
  { id: "news", label: "Noticias" },
  { id: "psychology", label: "Psicologia" },
  { id: "business", label: "Negocios" },
  { id: "science", label: "Ciencia" },
  { id: "history", label: "Historia" },
  { id: "wellness", label: "Wellness" },
  { id: "technology", label: "Tecnologia" },
];

export const RADAR_INTENT_OPTIONS = [
  { id: "viral_topics", label: "Temas virales" },
  { id: "audience_pain", label: "Dolores" },
  { id: "shorts_hooks", label: "Hooks" },
  { id: "evergreen", label: "Evergreen" },
  { id: "calendar_gaps", label: "Huecos" },
  { id: "news", label: "Noticias" },
];

export const RADAR_FORMAT_OPTIONS = [
  { id: "all", label: "Todos" },
  { id: "youtube_long", label: "YouTube largo" },
  { id: "tiktok", label: "TikTok" },
  { id: "both", label: "Multicanal" },
];

export function riskMeta(level) {
  const key = String(level || "low").toLowerCase();
  if (key === "high") {
    return { label: "Riesgo alto", badge: "cf-badge--bad", color: "var(--bad)" };
  }
  if (key === "medium") {
    return { label: "Riesgo medio", badge: "cf-badge--warn", color: "var(--warn)" };
  }
  return { label: "Riesgo bajo", badge: "cf-badge--ok", color: "var(--ok)" };
}

export function ideaStatusMeta(status) {
  const key = String(status || "suggested").toLowerCase();
  if (key === "project_created") return { label: "Proyecto", badge: "cf-badge--starter" };
  if (key === "produced") return { label: "Producido", badge: "cf-badge--ok" };
  if (key === "saved") return { label: "Guardado", badge: "cf-badge--creator" };
  if (key === "archived") return { label: "Archivado", badge: "cf-badge--neutral" };
  return { label: "Sugerido", badge: "cf-badge--neutral" };
}

export function projectStatusMeta(status) {
  const key = String(status || "draft").toLowerCase();
  if (key === "completed") return { label: "Completado", badge: "cf-badge--ok" };
  if (key === "failed" || key === "error") return { label: "Error", badge: "cf-badge--bad" };
  if (key === "draft") return { label: "Borrador", badge: "cf-badge--neutral" };
  if (key.includes("review")) return { label: "Revisar", badge: "cf-badge--warn" };
  return { label: "En curso", badge: "cf-badge--creator" };
}

export function formatRecommendation(value) {
  const key = String(value || "youtube_long").toLowerCase();
  if (key === "both") return "Multicanal";
  if (key === "tiktok") return "TikTok";
  if (key === "youtube_long") return "YouTube largo";
  return key.replace(/_/g, " ");
}

export function formatRadarIntent(value) {
  const key = String(value || "viral_topics").toLowerCase();
  const option = RADAR_INTENT_OPTIONS.find((item) => item.id === key);
  return option?.label || key.replace(/_/g, " ");
}

export function formatRadarDate(value) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function compactNumber(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: 0 }).format(number);
}

export function agentDisplayName(agentId, fallback, agents = []) {
  const agent = agents.find((item) => item.agentId === agentId);
  return agent?.name || fallback || String(agentId || "").replace("agent_", "").replace(/_/g, " ");
}
