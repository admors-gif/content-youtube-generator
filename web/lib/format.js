/**
 * Helpers de formato compartidos.
 */

const RTF = typeof Intl !== "undefined" && Intl.RelativeTimeFormat
  ? new Intl.RelativeTimeFormat("es", { numeric: "auto" })
  : null;

/**
 * Formatea una fecha como tiempo relativo en español ("hace 2 horas").
 * Acepta:
 *   - Date objeto
 *   - Firestore Timestamp ({ toDate: () => Date })
 *   - epoch ms (number)
 *   - string ISO
 *   - null/undefined → ""
 */
export function formatRelativeTime(input) {
  if (!input) return "";
  let date;
  try {
    if (input?.toDate) date = input.toDate();
    else if (input instanceof Date) date = input;
    else if (typeof input === "number") date = new Date(input);
    else if (typeof input === "string") date = new Date(input);
    else return "";
  } catch {
    return "";
  }
  if (!date || Number.isNaN(date.getTime())) return "";

  const diffSec = Math.round((date.getTime() - Date.now()) / 1000);
  const abs = Math.abs(diffSec);

  if (!RTF) {
    // Fallback simple
    if (abs < 60) return "hace un momento";
    if (abs < 3600) return `hace ${Math.floor(abs / 60)} min`;
    if (abs < 86400) return `hace ${Math.floor(abs / 3600)} h`;
    return `hace ${Math.floor(abs / 86400)} días`;
  }

  if (abs < 60) return RTF.format(diffSec, "second");
  if (abs < 3600) return RTF.format(Math.round(diffSec / 60), "minute");
  if (abs < 86400) return RTF.format(Math.round(diffSec / 3600), "hour");
  if (abs < 2592000) return RTF.format(Math.round(diffSec / 86400), "day");
  if (abs < 31536000) return RTF.format(Math.round(diffSec / 2592000), "month");
  return RTF.format(Math.round(diffSec / 31536000), "year");
}

/**
 * Mapea status legacy del backend a 4 buckets visuales del kit.
 */
export function getStatusBucket(status) {
  switch (status) {
    case "completed":
      return { label: "COMPLETADO", cls: "cf-badge--ok", animate: false };
    case "failed":
    case "error":
      return { label: "FALLÓ", cls: "cf-badge--bad", animate: false };
    case "draft":
    case "scripting":
    case "script_ready":
      return { label: "GUIONIZANDO", cls: "cf-badge--warn", animate: true };
    case "prompting":
    case "imaging":
    case "voicing":
    case "assembling":
    case "producing":
      return { label: "PRODUCIENDO", cls: "cf-badge--creator", animate: true };
    default:
      return { label: (status || "—").toUpperCase(), cls: "cf-badge--neutral", animate: false };
  }
}
