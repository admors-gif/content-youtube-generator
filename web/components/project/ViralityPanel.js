"use client";
import { computeViralityScore } from "@/lib/virality";

/**
 * ViralityPanel (presentacional).
 *
 * Recibe del container:
 *   - text: string con el guión actual (typically `editedScript`)
 *
 * Internamente computa el score (memoizable en el container si fuera caro,
 * pero por ahora se ejecuta directo: O(N) sobre el texto, suficientemente
 * barato para textos de 5K-15K palabras).
 *
 * Si el texto es muy corto, computeViralityScore devuelve null y este
 * componente no renderiza nada.
 *
 * Fase 7.1: render IDÉNTICO. Fase 7.2 → cf-card + emoji-free labels.
 */
function ScoreBar({ label, value, emoji }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        fontSize: "12px",
      }}
    >
      <span style={{ width: "16px" }}>{emoji}</span>
      <span style={{ flex: 1, color: "var(--text-secondary)" }}>{label}</span>
      <div
        style={{
          width: "60px",
          height: "6px",
          background: "rgba(255,255,255,0.1)",
          borderRadius: "3px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${value}%`,
            height: "100%",
            background:
              value >= 75 ? "#4ade80" : value >= 50 ? "#facc15" : "#f87171",
            borderRadius: "3px",
            transition: "width 0.5s",
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "monospace",
          fontSize: "11px",
          width: "28px",
          textAlign: "right",
        }}
      >
        {value}
      </span>
    </div>
  );
}

export default function ViralityPanel({ text }) {
  const score = computeViralityScore(text);
  if (!score) return null;

  const scoreColor =
    score.overall >= 75 ? "#4ade80" : score.overall >= 50 ? "#facc15" : "#f87171";

  return (
    <div className="glass-card" style={{ padding: "20px" }}>
      <h4
        style={{
          fontWeight: "bold",
          margin: "0 0 12px 0",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        🔥 Viralidad
      </h4>
      {/* Overall score circle */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "16px",
          marginBottom: "16px",
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            background: `conic-gradient(${scoreColor} ${score.overall * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              background: "var(--bg-card)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "16px",
              fontWeight: "900",
              color: scoreColor,
            }}
          >
            {score.overall}
          </div>
        </div>
        <div>
          <div
            style={{ fontSize: "13px", fontWeight: "700", color: scoreColor }}
          >
            {score.overall >= 80
              ? "🚀 Viral"
              : score.overall >= 60
                ? "👍 Bueno"
                : score.overall >= 40
                  ? "⚡ Mejorable"
                  : "📝 Revisar"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            {score.hooks} hooks detectados
          </div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <ScoreBar label="Hooks" value={score.hookScore} emoji="🎣" />
        <ScoreBar label="Emoción" value={score.emotionScore} emoji="❤️" />
        <ScoreBar label="Ritmo" value={score.pacingScore} emoji="🥁" />
        <ScoreBar label="Estructura" value={score.structureScore} emoji="📐" />
        <ScoreBar label="Retención" value={score.retentionScore} emoji="🧲" />
      </div>
    </div>
  );
}
