"use client";
import Icon from "@/components/Icon";

/**
 * ModerationAlert — Editorial Cinematic v2.
 *
 * cf-card con paleta semántica del kit (ok / warn / bad) según verdict.
 * Items en cf-mono uppercase con porcentaje.
 */
const VERDICT_PRESETS = {
  block: {
    label: "REQUIERE TU REVISIÓN ANTES DE CONTINUAR",
    badgeCls: "cf-badge--bad",
    iconName: "alert",
    iconColor: "var(--bad)",
    bg: "rgba(216, 98, 90, 0.06)",
    borderColor: "var(--bad)",
  },
  warn: {
    label: "CONTENIDO SENSIBLE DETECTADO",
    badgeCls: "cf-badge--warn",
    iconName: "alert",
    iconColor: "var(--warn)",
    bg: "rgba(212, 168, 87, 0.05)",
    borderColor: "var(--warn)",
  },
  ok: {
    label: "CONTENIDO APTO",
    badgeCls: "cf-badge--ok",
    iconName: "check",
    iconColor: "var(--ok)",
    bg: "rgba(111, 190, 142, 0.05)",
    borderColor: "var(--ok)",
  },
};

export default function ModerationAlert({ moderation }) {
  if (!moderation) return null;

  const verdict = moderation.verdict || "ok";
  const preset = VERDICT_PRESETS[verdict] || VERDICT_PRESETS.ok;
  const items =
    verdict === "block"
      ? moderation.critical_blocks || []
      : verdict === "warn"
        ? moderation.warnings || []
        : [];

  return (
    <div
      style={{
        marginBottom: "var(--s-4)",
        padding: "var(--s-4) var(--s-5)",
        borderRadius: "var(--r-2)",
        background: preset.bg,
        border: `1px solid ${preset.borderColor}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: items.length ? 10 : 0,
        }}
      >
        <span style={{ color: preset.iconColor, display: "flex" }}>
          <Icon name={preset.iconName} size={18} />
        </span>
        <span className={`cf-badge ${preset.badgeCls}`}>{preset.label}</span>
      </div>
      {items.length > 0 && (
        <ul
          style={{
            margin: 0,
            padding: "0 0 0 28px",
            color: "var(--paper)",
            fontSize: 13,
            lineHeight: 1.7,
          }}
        >
          {items.map((it) => (
            <li key={it.category} style={{ marginBottom: 4 }}>
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  marginRight: 8,
                }}
              >
                {it.category}
              </span>
              <span style={{ color: preset.iconColor, fontWeight: 600 }}>
                {(it.score * 100).toFixed(0)}%
              </span>
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-dim)",
                  marginLeft: 6,
                }}
              >
                · umbral {(it.threshold * 100).toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
      )}
      {verdict === "block" && (
        <div
          style={{
            marginTop: 10,
            font: "var(--t-caption)",
            color: "var(--paper-dim)",
          }}
        >
          Si decides aprobar de todos modos, se te pedirá confirmación.
          Considera editar el guión para reducir el contenido marcado.
        </div>
      )}
    </div>
  );
}
