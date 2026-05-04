"use client";

/**
 * StatsPanel — Editorial Cinematic v2.
 *
 * cf-card sidebar con eyebrow ESTADÍSTICAS + tres rows mono.
 */
export default function StatsPanel({
  wordCount = 0,
  estimatedMinutes = 0,
  approved = false,
}) {
  const rows = [
    { label: "PALABRAS", value: wordCount.toLocaleString("es") },
    {
      label: "DURACIÓN ESTIMADA",
      value: estimatedMinutes ? `${estimatedMinutes} min` : "—",
    },
    {
      label: "ESTADO",
      value: approved ? "APROBADO" : "BORRADOR",
      accent: approved ? "var(--ok)" : "var(--warn)",
    },
  ];

  return (
    <div className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div
        style={{
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          marginBottom: 16,
        }}
      >
        ESTADÍSTICAS
      </div>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {rows.map((r, i) => (
          <li
            key={r.label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              gap: 12,
              borderBottom:
                i < rows.length - 1 ? "1px solid var(--rule-1)" : "none",
              paddingBottom: i < rows.length - 1 ? 10 : 0,
            }}
          >
            <span
              style={{
                font: "var(--t-mono-sm)",
                color: "var(--paper-mute)",
                letterSpacing: "0.12em",
              }}
            >
              {r.label}
            </span>
            <span
              style={{
                font: "var(--t-mono)",
                fontFamily: "var(--font-mono)",
                color: r.accent || "var(--paper)",
                fontWeight: 600,
              }}
            >
              {r.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
