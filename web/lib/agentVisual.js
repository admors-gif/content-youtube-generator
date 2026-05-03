/**
 * Agent visual identity — monogramas curados + colores.
 *
 * Reemplaza emojis estructurales del legacy (lib/agents.js mantiene `emoji`
 * por compatibilidad con backend/Firestore, pero la UI nueva NO los usa).
 *
 * Monograma = 2 caracteres distintivos por agente, evitando colisiones.
 * Renderizado en Fraunces 700 italic dentro de un tile cuadrado con bg
 * tintado del color del agente al 12% y la letra al 100%.
 *
 * Uso:
 *   import { AgentMonogram, getMonogram } from "@/lib/agentVisual";
 *   <AgentMonogram agent={agent} size={48} />
 *
 * NO modificar el shape de SYSTEM_AGENTS (backend Python/n8n lo lee).
 * Los monogramas viven AQUÍ, paralelamente.
 */
import { SYSTEM_AGENTS } from "./agents";

/**
 * Monogramas curados para los 28 agentes.
 * Convención: 2 letras/símbolos seguros (compatibles con Fraunces).
 * Evitar caracteres exóticos (Φ, ψ, ⚔, †, Ω, ∞, ∴) por compatibilidad
 * cross-browser y filename safety.
 */
export const MONOGRAM_BY_AGENT_ID = {
  agent_horror:           "HH",
  agent_misterios:        "M?",
  agent_biografias:       "BÉ",
  agent_ciencia:          "Cn",
  agent_finanzas:         "F$",
  agent_filosofia:        "Fi",
  agent_erotico_historico: "Rh",
  agent_historico:        "Dh",
  agent_psicologia_oscura: "Po",
  agent_civilizaciones:   "Cv",
  agent_true_crime:       "TC",
  agent_mitologia:        "Mt",
  agent_conspiraciones:   "C!",
  agent_tecnologia:       "Tc",
  agent_guerras:          "Gw",
  agent_espionaje:        "Es",
  agent_apocalipsis:      "Ap",
  agent_religiones:       "Re",
  agent_metafisica:       "Mf",
  agent_imperios:         "Ip",
  agent_arte:             "Ar",
  agent_emprendimiento:   "E+",
  agent_negocios:         "N$",
  agent_liderazgo:        "Ld",
  agent_biblico:          "Bb",
  agent_viajes:           "Vj",
  agent_noticias_virales: "Nv",
  agent_podcast_general:  "Pc",
};

/**
 * Devuelve monograma curado del agente. Fallback: primera letra del name.
 */
export function getMonogram(agentId) {
  if (MONOGRAM_BY_AGENT_ID[agentId]) return MONOGRAM_BY_AGENT_ID[agentId];
  const agent = SYSTEM_AGENTS.find((a) => a.agentId === agentId);
  return agent?.name?.charAt(0)?.toUpperCase() || "·";
}

/**
 * Devuelve color hex del agente desde lib/agents.js. Fallback: ember.
 */
export function getAgentColor(agentId) {
  const agent = SYSTEM_AGENTS.find((a) => a.agentId === agentId);
  return agent?.color || "#E0533D";
}

/**
 * Devuelve agente completo por ID. Conveniencia.
 */
export function getAgent(agentId) {
  return SYSTEM_AGENTS.find((a) => a.agentId === agentId) || null;
}

/**
 * Tile del monograma del agente. Square con bg tintado + letra grande
 * en Fraunces italic 700, color del agente.
 *
 * Props:
 *   agent: objeto agent (con agentId + color) o solo agentId string
 *   size:  px del tile (default 48)
 *   variant: "default" | "compact" (compact = sin border, más pequeño)
 */
export function AgentMonogram({ agent, size = 48, variant = "default", style, ...rest }) {
  const agentId = typeof agent === "string" ? agent : agent?.agentId;
  if (!agentId) return null;
  const color = getAgentColor(agentId);
  const mono = getMonogram(agentId);
  const fontSize = Math.max(14, Math.round(size * 0.42));
  const radius = variant === "compact" ? 6 : 10;

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: `${color}1F`, // 12% opacity hex
        border: variant === "compact" ? "none" : `1px solid ${color}3D`, // 24% opacity
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        color,
        fontFamily: "var(--font-display)",
        fontStyle: "italic",
        fontWeight: 700,
        fontSize,
        lineHeight: 1,
        letterSpacing: "-0.02em",
        userSelect: "none",
        ...style,
      }}
      aria-hidden
      {...rest}
    >
      {mono}
    </div>
  );
}
