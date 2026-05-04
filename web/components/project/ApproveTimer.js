"use client";
/**
 * ApproveTimer (presentacional).
 *
 * Conic-gradient countdown circular + botón pause/resume.
 *
 * Recibe del container:
 *   - seconds: segundos restantes (state)
 *   - totalSeconds: total para calcular el ratio del conic-gradient
 *   - paused: bool (state)
 *   - onTogglePause: callback que invierte el paused
 *
 * Fase 7.1: render IDÉNTICO. Fase 7.2 reemplazará botón por cf-btn ghost
 * con Icon pause/play.
 */
export default function ApproveTimer({
  seconds,
  totalSeconds,
  paused,
  onTogglePause,
}) {
  const ratio = (seconds / totalSeconds) * 360;
  const ringColor = paused ? "#facc15" : "var(--accent)";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <div
        style={{
          position: "relative",
          width: "38px",
          height: "38px",
          borderRadius: "50%",
          background: `conic-gradient(${ringColor} ${ratio}deg, rgba(255,255,255,0.1) 0deg)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: "30px",
            height: "30px",
            borderRadius: "50%",
            background: "var(--bg-card)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "11px",
            fontFamily: "monospace",
            fontWeight: "bold",
          }}
        >
          {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
        </div>
      </div>
      <button
        onClick={onTogglePause}
        style={{
          background: "none",
          border: "1px solid var(--border)",
          borderRadius: "6px",
          padding: "4px 10px",
          fontSize: "12px",
          cursor: "pointer",
          color: paused ? "#facc15" : "var(--text-secondary)",
        }}
      >
        {paused ? "▶️ Reanudar" : "⏸️ Pausar"}
      </button>
    </div>
  );
}
