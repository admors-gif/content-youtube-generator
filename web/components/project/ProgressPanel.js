"use client";
import Icon from "@/components/Icon";

/**
 * ProgressPanel — panel separado de "Producción en vivo" (Fase 7.2).
 *
 * Reemplaza la barra inline que vivía en el ProjectHeader legacy. Solo se
 * renderiza cuando isProcessing.
 *
 * Recibe del container:
 *   - displayPercent (smooth interpolated)
 *   - stepName (project.progress.stepName)
 *   - eta (string o null)
 *   - status (project.status — usado para mapear phases)
 *   - scenes (project.scenes — para contador de imágenes)
 *
 * Visual del kit: master bar ember con shimmer overlay + 5 phase rows con
 * dot circular (ok / current pulsando ember / pending) y sub mono.
 */

const PHASE_DEFS = [
  { id: "research", label: "Investigación" },
  { id: "script",   label: "Guión" },
  { id: "voice",    label: "Voz · ElevenLabs" },
  { id: "images",   label: "Imágenes" },
  { id: "assembly", label: "Montaje" },
];

/**
 * Mapea status legacy del backend a phases visuales.
 *
 * Backend statuses (pipeline):
 *   draft → scripting → script_ready → producing → prompting → imaging
 *   → voicing → assembling → completed
 *
 * Visual phases (5):
 *   Investigación + Guión + Voz + Imágenes + Montaje
 *
 * Convención: una phase está "ok" si ya pasamos por ella, "current" si es
 * la que está corriendo ahora, "pending" si aún no llegamos.
 */
function getPhasesFromStatus(status, scenes) {
  const totalScenes = scenes?.length || 0;
  const withImg = (scenes || []).filter((s) => s.imageUrl).length;

  // Por defecto todas pending
  let states = {
    research: "pending",
    script:   "pending",
    voice:    "pending",
    images:   "pending",
    assembly: "pending",
  };
  let imagesSub = totalScenes ? `${withImg}/${totalScenes}` : null;

  switch (status) {
    case "draft":
      states.research = "current";
      break;
    case "scripting":
      states.research = "ok";
      states.script = "current";
      break;
    case "script_ready":
      states.research = "ok";
      states.script = "ok";
      break;
    case "producing":
    case "prompting":
      states.research = "ok";
      states.script = "ok";
      states.voice = "current";
      break;
    case "voicing":
      states.research = "ok";
      states.script = "ok";
      states.voice = "current";
      break;
    case "imaging":
      states.research = "ok";
      states.script = "ok";
      states.voice = "ok";
      states.images = "current";
      break;
    case "assembling":
      states.research = "ok";
      states.script = "ok";
      states.voice = "ok";
      states.images = "ok";
      states.assembly = "current";
      break;
    case "completed":
      states = {
        research: "ok",
        script: "ok",
        voice: "ok",
        images: "ok",
        assembly: "ok",
      };
      imagesSub = totalScenes ? `${totalScenes}/${totalScenes}` : null;
      break;
    default:
      break;
  }

  return PHASE_DEFS.map((p) => ({
    ...p,
    state: states[p.id],
    sub: p.id === "images" ? imagesSub : null,
  }));
}

export default function ProgressPanel({
  displayPercent,
  stepName,
  eta,
  status,
  scenes,
}) {
  const phases = getPhasesFromStatus(status, scenes);
  const pct = Math.round(displayPercent);

  return (
    <div className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: "var(--s-4)",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--ember)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            PRODUCCIÓN EN VIVO
          </div>
          <div
            style={{
              font: "var(--t-h3)",
              color: "var(--paper)",
              marginTop: 4,
              fontFamily: "var(--font-display)",
              fontWeight: 600,
            }}
          >
            {pct}%
            {eta && (
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-dim)",
                  marginLeft: 12,
                  fontFamily: "var(--font-mono)",
                  fontWeight: 400,
                }}
              >
                · {eta}
              </span>
            )}
          </div>
          {stepName && (
            <div
              style={{
                font: "var(--t-caption)",
                color: "var(--paper-dim)",
                marginTop: 4,
              }}
            >
              {stepName}
            </div>
          )}
        </div>
      </div>

      {/* Master bar ember + shimmer */}
      <div
        style={{
          height: 4,
          background: "var(--ink-2)",
          borderRadius: 2,
          overflow: "hidden",
          marginBottom: "var(--s-5)",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            width: `${pct}%`,
            background: "var(--ember)",
            boxShadow: "0 0 12px var(--ember)",
            transition: "width 0.8s var(--ease-out)",
          }}
        />
        {pct < 100 && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: `${Math.max(0, pct - 5)}%`,
              width: "20%",
              height: "100%",
              background:
                "linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)",
              animation: "cf-shimmer 2s linear infinite",
            }}
          />
        )}
      </div>

      {/* Phase rows */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {phases.map((p) => {
          const isOk = p.state === "ok";
          const isCurrent = p.state === "current";
          return (
            <div
              key={p.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: isOk
                    ? "var(--ok)"
                    : isCurrent
                      ? "var(--ember)"
                      : "var(--ink-3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#0B0B0E",
                  flex: "none",
                  animation: isCurrent
                    ? "cf-pulse 1.6s ease-in-out infinite"
                    : "",
                  boxShadow: isCurrent
                    ? "0 0 8px var(--ember)"
                    : "none",
                }}
              >
                {isOk && <Icon name="check" size={11} stroke={2.5} />}
              </div>
              <div
                style={{
                  flex: 1,
                  fontSize: 14,
                  color:
                    p.state === "pending"
                      ? "var(--paper-mute)"
                      : "var(--paper)",
                  fontWeight: isCurrent ? 600 : 400,
                }}
              >
                {p.label}
              </div>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-dim)",
                  letterSpacing: "0.06em",
                }}
              >
                {p.sub
                  ? p.sub
                  : isOk
                    ? "100%"
                    : isCurrent
                      ? "EN CURSO"
                      : "—"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
