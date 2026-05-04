"use client";
import Icon from "@/components/Icon";

/**
 * PodcastBubbles — Editorial Cinematic v2.
 *
 * Parser tolerante: separa el guión en turnos por speaker. Soporta
 * MATEO/LUCÍA y HOST_A/HOST_B legacy. Renderiza burbujas tipo chat
 * con el speaker en eyebrow ember y el texto en cf-body.
 *
 * Si no detecta turnos, devuelve null.
 */
const SPEAKER_PRESETS = {
  MATEO:  { side: "left",  accent: "#7A9CC6", bg: "rgba(122, 156, 198, 0.08)" },
  LUCÍA:  { side: "right", accent: "#E0533D", bg: "rgba(224, 83, 61, 0.08)" },
  LUCIA:  { side: "right", accent: "#E0533D", bg: "rgba(224, 83, 61, 0.08)" },
  HOST_A: { side: "left",  accent: "#7A9CC6", bg: "rgba(122, 156, 198, 0.08)" },
  HOST_B: { side: "right", accent: "#E0533D", bg: "rgba(224, 83, 61, 0.08)" },
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
        marginBottom: "var(--s-4)",
        padding: "var(--s-4)",
        background: "var(--ink-0)",
        borderRadius: "var(--r-2)",
        border: "1px solid var(--rule-1)",
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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          <Icon name="user" size={14} />
          VISTA CONVERSACIÓN · {turns.length} TURNOS
        </div>
        <span
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-dim)",
            letterSpacing: "0.06em",
          }}
        >
          Editable abajo en texto crudo
        </span>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          maxHeight: 500,
          overflowY: "auto",
          paddingRight: 8,
        }}
      >
        {turns.map((t, i) => {
          const preset = SPEAKER_PRESETS[t.speaker] || {
            side: "left",
            accent: "var(--paper-dim)",
            bg: "var(--ink-2)",
          };
          const isRight = preset.side === "right";
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
                  background: preset.bg,
                  border: `1px solid ${preset.accent}3D`,
                  borderRadius: "var(--r-2)",
                  padding: "10px 14px",
                }}
              >
                <div
                  style={{
                    font: "var(--t-mono-sm)",
                    color: preset.accent,
                    marginBottom: 4,
                    letterSpacing: "0.16em",
                    fontWeight: 700,
                  }}
                >
                  {t.speaker}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-display)",
                    fontStyle: "italic",
                    fontWeight: 400,
                    fontSize: 16,
                    lineHeight: 1.55,
                    color: "var(--paper)",
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
