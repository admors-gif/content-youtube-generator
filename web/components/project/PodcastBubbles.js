"use client";
/**
 * PodcastBubbles (presentacional).
 *
 * Parser tolerante: separa el guión en turnos por speaker (regex
 * `/^\s*([A-ZÁÉÍÓÚÑ_]+)\s*:\s*(.+)$/`). Soporta nombres legacy
 * (MATEO/LUCÍA, HOST_A/HOST_B) y mapea cada uno a una paleta + lado.
 *
 * Renderiza burbujas tipo chat alternando left/right según el speaker.
 *
 * Recibe del container:
 *   - scriptText: string (typically `editedScript`)
 *
 * Si no detecta turnos, retorna null (la página seguirá mostrando el
 * textarea normal, sin la vista conversación).
 *
 * Fase 7.1: render IDÉNTICO al legacy.
 */
const SPEAKER_COLORS = {
  MATEO:  { bg: "rgba(59, 130, 246, 0.10)",  border: "rgba(59, 130, 246, 0.4)",  accent: "#60a5fa", side: "left"  },
  LUCÍA:  { bg: "rgba(244, 114, 182, 0.10)", border: "rgba(244, 114, 182, 0.4)", accent: "#f472b6", side: "right" },
  LUCIA:  { bg: "rgba(244, 114, 182, 0.10)", border: "rgba(244, 114, 182, 0.4)", accent: "#f472b6", side: "right" },
  HOST_A: { bg: "rgba(59, 130, 246, 0.10)",  border: "rgba(59, 130, 246, 0.4)",  accent: "#60a5fa", side: "left"  },
  HOST_B: { bg: "rgba(244, 114, 182, 0.10)", border: "rgba(244, 114, 182, 0.4)", accent: "#f472b6", side: "right" },
};

function parseTurns(text) {
  const lines = (text || "").split("\n");
  const turns = [];
  let lastIdx = -1;
  for (const line of lines) {
    const m = line.match(/^\s*([A-ZÁÉÍÓÚÑ_]+)\s*:\s*(.+)$/);
    if (m) {
      const speaker = m[1].toUpperCase();
      const turnText = m[2].trim();
      turns.push({ speaker, text: turnText });
      lastIdx = turns.length - 1;
    } else if (line.trim() && lastIdx >= 0) {
      // Continuación del último speaker
      turns[lastIdx].text = turns[lastIdx].text + " " + line.trim();
    }
  }
  return turns;
}

export default function PodcastBubbles({ scriptText }) {
  const turns = parseTurns(scriptText);
  if (turns.length === 0) return null;

  return (
    <div
      style={{
        marginBottom: "16px",
        padding: "16px",
        background: "rgba(20, 184, 166, 0.04)",
        borderRadius: "10px",
        border: "1px solid rgba(20, 184, 166, 0.25)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "12px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "13px",
            fontWeight: "bold",
            color: "#5eead4",
          }}
        >
          🎙️ Vista conversación ({turns.length} turnos)
        </div>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
          Editable abajo en texto crudo
        </span>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          maxHeight: "500px",
          overflowY: "auto",
          paddingRight: "8px",
        }}
      >
        {turns.map((t, i) => {
          const palette =
            SPEAKER_COLORS[t.speaker] || {
              bg: "rgba(148, 163, 184, 0.08)",
              border: "rgba(148, 163, 184, 0.3)",
              accent: "#94a3b8",
              side: "left",
            };
          const isRight = palette.side === "right";
          return (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: isRight ? "flex-end" : "flex-start",
              }}
            >
              <div
                style={{
                  maxWidth: "80%",
                  background: palette.bg,
                  border: `1px solid ${palette.border}`,
                  borderRadius: "12px",
                  padding: "10px 14px",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: "bold",
                    color: palette.accent,
                    marginBottom: "4px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  {t.speaker}
                </div>
                <div
                  style={{
                    fontSize: "14px",
                    color: "var(--text-primary)",
                    lineHeight: 1.5,
                  }}
                >
                  {t.text}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
