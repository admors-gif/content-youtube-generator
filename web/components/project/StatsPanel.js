"use client";
/**
 * StatsPanel (presentacional).
 *
 * Sidebar stats: palabras, minutos estimados, estado.
 *
 * Recibe del container:
 *   - wordCount, estimatedMinutes, approved (todos opcionales / safe defaults)
 *
 * Fase 7.1: render IDÉNTICO. Fase 7.2 → cf-card + eyebrow mono uppercase.
 */
export default function StatsPanel({
  wordCount = 0,
  estimatedMinutes = 0,
  approved = false,
}) {
  return (
    <div className="glass-card" style={{ padding: "20px" }}>
      <h4
        style={{
          fontWeight: "bold",
          margin: "0 0 16px 0",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        📊 Estadísticas
      </h4>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          fontSize: "14px",
        }}
      >
        <li
          style={{
            display: "flex",
            justifyContent: "space-between",
            borderBottom: "1px solid var(--border)",
            paddingBottom: "8px",
          }}
        >
          <span style={{ color: "var(--text-secondary)" }}>Palabras:</span>
          <span style={{ fontFamily: "monospace" }}>{wordCount}</span>
        </li>
        <li
          style={{
            display: "flex",
            justifyContent: "space-between",
            borderBottom: "1px solid var(--border)",
            paddingBottom: "8px",
          }}
        >
          <span style={{ color: "var(--text-secondary)" }}>Minutos est:</span>
          <span style={{ fontFamily: "monospace" }}>
            {estimatedMinutes} min
          </span>
        </li>
        <li
          style={{
            display: "flex",
            justifyContent: "space-between",
            paddingBottom: "8px",
          }}
        >
          <span style={{ color: "var(--text-secondary)" }}>Estado:</span>
          <span
            style={{
              color: approved ? "#4ade80" : "#facc15",
              fontWeight: "bold",
            }}
          >
            {approved ? "Aprobado" : "Borrador"}
          </span>
        </li>
      </ul>
    </div>
  );
}
