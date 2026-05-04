"use client";
/**
 * ModerationAlert (presentacional).
 *
 * Recibe del container:
 *   - moderation: { verdict: "block"|"warn"|"ok", critical_blocks: [], warnings: [] }
 *
 * Si no hay moderation o el verdict es desconocido, no renderiza nada (null).
 *
 * Fase 7.1: render IDÉNTICO al legacy. Fase 7.2 lo migrará a cf-card con
 * paletas semánticas (ok/warn/bad) del kit.
 */
export default function ModerationAlert({ moderation }) {
  if (!moderation) return null;

  const verdict = moderation.verdict || "ok";
  const palette =
    verdict === "block"
      ? {
          bg: "rgba(220, 38, 38, 0.08)",
          border: "rgba(220, 38, 38, 0.4)",
          color: "#fca5a5",
          icon: "🚫",
          label: "Requiere tu revisión antes de continuar",
        }
      : verdict === "warn"
        ? {
            bg: "rgba(234, 179, 8, 0.08)",
            border: "rgba(234, 179, 8, 0.4)",
            color: "#fde68a",
            icon: "⚠️",
            label: "Contenido sensible detectado (esperado para este nicho)",
          }
        : {
            bg: "rgba(34, 197, 94, 0.08)",
            border: "rgba(34, 197, 94, 0.4)",
            color: "#86efac",
            icon: "✅",
            label: "Contenido apto",
          };

  const items =
    verdict === "block"
      ? moderation.critical_blocks || []
      : verdict === "warn"
        ? moderation.warnings || []
        : [];

  return (
    <div
      style={{
        marginBottom: "16px",
        padding: "16px",
        borderRadius: "10px",
        background: palette.bg,
        border: `1px solid ${palette.border}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginBottom: items.length ? "10px" : 0,
        }}
      >
        <span style={{ fontSize: "20px" }}>{palette.icon}</span>
        <span
          style={{
            color: palette.color,
            fontWeight: "bold",
            fontSize: "14px",
          }}
        >
          {palette.label}
        </span>
      </div>
      {items.length > 0 && (
        <ul
          style={{
            margin: 0,
            padding: "0 0 0 28px",
            color: palette.color,
            fontSize: "13px",
            lineHeight: 1.7,
          }}
        >
          {items.map((it) => (
            <li key={it.category}>
              <strong>{it.category}</strong>: intensidad{" "}
              {(it.score * 100).toFixed(0)}% (umbral:{" "}
              {(it.threshold * 100).toFixed(0)}%)
            </li>
          ))}
        </ul>
      )}
      {verdict === "block" && (
        <div
          style={{
            marginTop: "10px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          Si decides aprobar de todos modos, se te pedirá confirmación.
          Considera editar el guión para reducir el contenido marcado.
        </div>
      )}
    </div>
  );
}
