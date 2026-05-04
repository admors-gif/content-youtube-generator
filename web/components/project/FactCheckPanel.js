"use client";
import Icon from "@/components/Icon";

/**
 * FactCheckPanel — Editorial Cinematic v2.
 *
 * cf-card con eyebrow VERIFICACIÓN DE DATOS + 3 chips contadores
 * (alta/media/baja) + lista de claims con border-left según confidence.
 */
export default function FactCheckPanel({ factCheck }) {
  if (!factCheck?.claims || factCheck.claims.length === 0) return null;

  const summary = factCheck.summary || { total: 0, high: 0, medium: 0, low: 0 };
  const lowOrMedium = (factCheck.claims || []).filter(
    (c) => (c.confidence || "").toLowerCase() !== "alta",
  );

  return (
    <div
      className="cf-card"
      style={{
        marginBottom: "var(--s-4)",
        padding: "var(--s-4) var(--s-5)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon name="bookOpen" size={16} style={{ color: "var(--info)" }} />
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            VERIFICACIÓN DE DATOS
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <span className="cf-badge cf-badge--ok">{summary.high} ALTAS</span>
          <span className="cf-badge cf-badge--warn">
            {summary.medium} MEDIAS
          </span>
          <span className="cf-badge cf-badge--bad">{summary.low} BAJAS</span>
        </div>
      </div>

      {lowOrMedium.length > 0 ? (
        <>
          <div
            style={{
              font: "var(--t-caption)",
              color: "var(--paper-dim)",
              marginBottom: 10,
            }}
          >
            Datos que deberías revisar antes de publicar:
          </div>
          <ul
            style={{
              margin: 0,
              padding: 0,
              listStyle: "none",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            {lowOrMedium.slice(0, 6).map((c, i) => {
              const isLow = (c.confidence || "").toLowerCase() === "baja";
              const accentColor = isLow ? "var(--bad)" : "var(--warn)";
              return (
                <li
                  key={i}
                  style={{
                    paddingLeft: 12,
                    borderLeft: `2px solid ${accentColor}`,
                    fontSize: 13,
                    lineHeight: 1.5,
                    color: "var(--paper)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        font: "var(--t-mono-sm)",
                        color: accentColor,
                        letterSpacing: "0.16em",
                        fontWeight: 600,
                      }}
                    >
                      [{(c.confidence || "?").toUpperCase()}]
                    </span>
                  </div>
                  <div>{c.claim}</div>
                  {c.verdict && (
                    <div
                      style={{
                        font: "var(--t-caption)",
                        color: "var(--paper-dim)",
                        marginTop: 4,
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
                        font: "var(--t-mono-sm)",
                        color: "var(--ember)",
                        textDecoration: "none",
                        marginTop: 4,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      FUENTE <Icon name="arrowRight" size={12} />
                    </a>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            font: "var(--t-caption)",
            color: "var(--ok)",
          }}
        >
          <Icon name="check" size={14} />
          Todos los datos verificables tienen evidencia sólida.
        </div>
      )}
    </div>
  );
}
