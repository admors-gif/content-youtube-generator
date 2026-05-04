"use client";
/**
 * ShortsGrid (presentacional).
 *
 * Recibe del container:
 *   - shorts: array de { index, signed_url, label, duration, size_mb }
 *
 * Fase 7.1: render IDÉNTICO. Fase 7.2 aplicará cf-card + iconos editoriales.
 */
export default function ShortsGrid({ shorts }) {
  if (!Array.isArray(shorts) || shorts.length === 0) return null;

  return (
    <div
      className="glass-card animate-fade-in"
      style={{ marginBottom: "32px", padding: "20px" }}
    >
      <h3
        style={{
          margin: "0 0 14px 0",
          fontSize: "16px",
          fontWeight: "bold",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        📱 Versiones cortas (9:16)
        <span
          style={{
            fontSize: "12px",
            color: "var(--text-muted)",
            fontWeight: "normal",
          }}
        >
          {shorts.length} clips listos para publicar
        </span>
      </h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
        }}
      >
        {shorts.map((s) => (
          <div
            key={s.index}
            style={{
              background: "var(--bg-dark)",
              borderRadius: "8px",
              overflow: "hidden",
              border: "1px solid var(--border)",
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
                fontSize: "12px",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>
                {s.label === "hook"
                  ? "🎯 Hook"
                  : s.label === "mid"
                    ? "🔥 Punto fuerte"
                    : "🏆 Cierre"}
                {" · "}
                {Math.round(s.duration)}s
              </span>
              <span style={{ color: "var(--text-muted)", fontFamily: "monospace" }}>
                {s.size_mb}MB
              </span>
            </div>
            <a
              href={s.signed_url}
              download
              className="btn-secondary"
              style={{
                margin: "0 12px 12px",
                padding: "6px 10px",
                fontSize: "12px",
                textAlign: "center",
                textDecoration: "none",
                display: "block",
              }}
            >
              ⬇ Descargar
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
