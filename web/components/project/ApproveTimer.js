"use client";
import Icon from "@/components/Icon";

/**
 * ApproveTimer — Editorial Cinematic v2.
 *
 * Conic-gradient ember countdown + botón pause/resume cf-btn ghost sm.
 *
 * Recibe del container:
 *   - seconds, totalSeconds, paused, onTogglePause
 */
export default function ApproveTimer({
  seconds,
  totalSeconds,
  paused,
  onTogglePause,
}) {
  const ratio = (seconds / totalSeconds) * 360;
  const ringColor = paused ? "var(--warn)" : "var(--ember)";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div
        style={{
          position: "relative",
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: `conic-gradient(${ringColor} ${ratio}deg, var(--ink-3) 0deg)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: paused ? "none" : "0 0 8px var(--ember)",
          transition: "box-shadow var(--dur-base) var(--ease-out)",
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "var(--ink-1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            font: "var(--t-mono-sm)",
            fontWeight: 700,
            color: ringColor,
          }}
        >
          {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
        </div>
      </div>
      <button
        onClick={onTogglePause}
        className="cf-btn cf-btn--ghost cf-btn--sm"
        aria-label={paused ? "Reanudar countdown" : "Pausar countdown"}
        style={{
          color: paused ? "var(--warn)" : "var(--paper-dim)",
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <Icon name={paused ? "play" : "pause"} size={12} />
        {paused ? "Reanudar" : "Pausar"}
      </button>
    </div>
  );
}
