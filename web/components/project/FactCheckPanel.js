"use client";
/**
 * FactCheckPanel (presentacional).
 *
 * Recibe del container:
 *   - factCheck: { claims: [...], summary: { total, high, medium, low } }
 *
 * Si no hay claims, no renderiza nada (null).
 *
 * Fase 7.1: render IDÉNTICO al legacy. Fase 7.2 → cf-card + chips mono.
 */
export default function FactCheckPanel({ factCheck }) {
  if (!factCheck?.claims || factCheck.claims.length === 0) return null;

  const summary = factCheck.summary || { total: 0, high: 0, medium: 0, low: 0 };
  const lowOrMedium = (factCheck.claims || []).filter(
    (c) => (c.confidence || "").toLowerCase() !== "alta",
  );

  return (
    <div
      style={{
        marginBottom: "16px",
        padding: "16px",
        borderRadius: "10px",
        background: "rgba(99, 102, 241, 0.06)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "20px" }}>📚</span>
          <span
            style={{ color: "#a5b4fc", fontWeight: "bold", fontSize: "14px" }}
          >
            Verificación de datos del guión
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px", fontSize: "12px" }}>
          <span style={{ color: "#86efac" }}>● {summary.high} altas</span>
          <span style={{ color: "#fde68a" }}>● {summary.medium} medias</span>
          <span style={{ color: "#fca5a5" }}>● {summary.low} bajas</span>
        </div>
      </div>
      {lowOrMedium.length > 0 ? (
        <div>
          <div
            style={{
              fontSize: "12px",
              color: "var(--text-muted)",
              marginBottom: "8px",
            }}
          >
            Datos que deberías revisar antes de publicar:
          </div>
          <ul
            style={{
              margin: 0,
              padding: "0 0 0 16px",
              fontSize: "13px",
              lineHeight: 1.6,
              color: "var(--text-secondary)",
            }}
          >
            {lowOrMedium.slice(0, 6).map((c, i) => (
              <li key={i} style={{ marginBottom: "6px" }}>
                <span
                  style={{
                    color:
                      (c.confidence || "").toLowerCase() === "media"
                        ? "#fde68a"
                        : "#fca5a5",
                  }}
                >
                  [{(c.confidence || "?").toUpperCase()}]
                </span>{" "}
                <span>{c.claim}</span>
                {c.verdict && (
                  <div
                    style={{
                      fontSize: "11px",
                      color: "var(--text-muted)",
                      marginLeft: "8px",
                    }}
                  >
                    {c.verdict}
                  </div>
                )}
                {c.source_url && (
                  <a
                    href={c.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: "11px",
                      color: "#a5b4fc",
                      marginLeft: "8px",
                    }}
                  >
                    fuente ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div style={{ fontSize: "13px", color: "#86efac" }}>
          Todos los datos verificables tienen evidencia sólida.
        </div>
      )}
    </div>
  );
}
