"use client";
import Icon from "@/components/Icon";

/**
 * ShortsGrid — Editorial Cinematic v2.
 *
 * cf-card outer con eyebrow VERSIONES CORTAS · 9:16. Cada short en
 * card propia con video + label mono + size + botón descargar ghost sm.
 */
const SHORT_LABELS = {
  hook: "HOOK",
  mid: "PUNTO FUERTE",
  closing: "CIERRE",
};

export default function ShortsGrid({ shorts }) {
  if (!Array.isArray(shorts) || shorts.length === 0) return null;

  return (
    <div
      className="cf-card cf-fade"
      style={{
        marginBottom: "var(--s-6)",
        padding: "var(--s-5)",
      }}
    >
      <div style={{ marginBottom: "var(--s-4)" }}>
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          VERSIONES CORTAS · 9:16
        </div>
        <div
          style={{
            font: "var(--t-h3)",
            color: "var(--paper)",
            marginTop: 4,
            fontFamily: "var(--font-display)",
            fontWeight: 600,
          }}
        >
          {shorts.length} clip{shorts.length === 1 ? "" : "s"} listos para
          publicar
        </div>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "var(--s-4)",
        }}
      >
        {shorts.map((s) => (
          <div
            key={s.index}
            style={{
              background: "var(--ink-1)",
              borderRadius: "var(--r-2)",
              overflow: "hidden",
              border: "1px solid var(--rule-1)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <video
              src={s.signed_url}
              controls
              preload="metadata"
              style={{
                width: "100%",
                aspectRatio: "9/16",
                background: "#000",
                display: "block",
              }}
            />
            <div
              style={{
                padding: "10px 12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper)",
                  letterSpacing: "0.12em",
                }}
              >
                {SHORT_LABELS[s.label] || (s.label || "").toUpperCase()}
                <span style={{ color: "var(--paper-dim)" }}>
                  {" · "}
                  {Math.round(s.duration)}s
                </span>
              </span>
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                }}
              >
                {s.size_mb}MB
              </span>
            </div>
            <a
              href={s.signed_url}
              download
              className="cf-btn cf-btn--ghost cf-btn--sm"
              style={{
                margin: "0 12px 12px",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                textDecoration: "none",
              }}
            >
              <Icon name="download" size={14} /> Descargar
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
