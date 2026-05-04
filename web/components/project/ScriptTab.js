"use client";
import Icon from "@/components/Icon";
import ModerationAlert from "./ModerationAlert";
import FactCheckPanel from "./FactCheckPanel";
import PodcastBubbles from "./PodcastBubbles";
import ApproveTimer from "./ApproveTimer";
import StatsPanel from "./StatsPanel";
import ViralityPanel from "./ViralityPanel";

/**
 * ScriptTab — Editorial Cinematic v2.
 *
 * Orquestador del tab de guión. Compone:
 *   - ModerationAlert (si hay project.moderation)
 *   - FactCheckPanel (si hay project.factCheck.claims)
 *   - cf-card guion editor con header eyebrow + h3 word count + acciones
 *     - estado "esperando IA": "El estudio está rodando" + Icon clapperboard
 *     - estado script disponible: PodcastBubbles si format=podcast +
 *       textarea Fraunces italic 18px + ApproveTimer + cf-btn "Aprobar y producir"
 *   - sidebar: StatsPanel + ViralityPanel
 *
 * Recibe del container TODA la state — no maneja nada interno propio.
 */
export default function ScriptTab({
  project,
  editedScript,
  setEditedScript,
  timerActive,
  timerSeconds,
  timerPaused,
  setTimerPaused,
  autoApproveSeconds,
  onApprove,
}) {
  const hasScript = !!project.script?.plain;
  const isProducing = project.status === "producing";
  const isApproved =
    project.script?.approved && project.status !== "script_ready";
  const wordCount = project.script?.wordCount || 0;
  const minutes = project.script?.estimatedMinutes || 0;

  return (
    <div
      className="cf-fade"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 320px",
        gap: "var(--s-5)",
      }}
    >
      <div>
        <ModerationAlert moderation={project.moderation} />
        <FactCheckPanel factCheck={project.factCheck} />

        <div className="cf-card" style={{ padding: "var(--s-5)" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: "var(--s-4)",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: isApproved ? "var(--ok)" : "var(--paper-mute)",
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                }}
              >
                {isApproved
                  ? "GUIÓN APROBADO"
                  : hasScript
                    ? "EN REVISIÓN"
                    : "EN ELABORACIÓN"}
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
                {hasScript
                  ? `${wordCount.toLocaleString("es")} palabras${minutes ? ` · ${minutes} min estimados` : ""}`
                  : "Guionizando…"}
              </div>
            </div>

            {hasScript &&
              (isProducing ? (
                <span className="cf-badge cf-badge--creator">
                  <span
                    className="dot"
                    style={{ animation: "cf-pulse 1.6s ease-in-out infinite" }}
                  />
                  PRODUCIENDO
                </span>
              ) : isApproved ? null : (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  {timerActive && (
                    <ApproveTimer
                      seconds={timerSeconds}
                      totalSeconds={autoApproveSeconds}
                      paused={timerPaused}
                      onTogglePause={() => setTimerPaused(!timerPaused)}
                    />
                  )}
                  <button
                    onClick={onApprove}
                    className="cf-btn cf-btn--primary"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <Icon name="check" size={14} />
                    Aprobar y producir
                  </button>
                </div>
              ))}
          </div>

          {hasScript ? (
            <>
              {project.format === "podcast" && (
                <PodcastBubbles scriptText={editedScript} />
              )}
              <textarea
                value={editedScript}
                onChange={(e) => setEditedScript(e.target.value)}
                disabled={isApproved || isProducing}
                placeholder="El guión aparecerá aquí…"
                style={{
                  width: "100%",
                  background: "var(--ink-0)",
                  color: "var(--paper)",
                  padding: "16px 18px",
                  borderRadius: "var(--r-2)",
                  border: "1px solid var(--rule-1)",
                  outline: "none",
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 400,
                  fontSize: 18,
                  lineHeight: 1.6,
                  resize: "vertical",
                  minHeight: 500,
                  letterSpacing: "-0.005em",
                  transition: "border-color var(--dur-base) var(--ease-out)",
                  cursor:
                    isApproved || isProducing ? "not-allowed" : "text",
                  opacity: isApproved || isProducing ? 0.85 : 1,
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "var(--ember)")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = "var(--rule-1)")
                }
              />
            </>
          ) : (
            <div
              style={{
                minHeight: 360,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                textAlign: "center",
                border: "1px dashed var(--rule-1)",
                borderRadius: "var(--r-2)",
                padding: "var(--s-6)",
                background: "var(--ink-0)",
                gap: 14,
              }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: "var(--r-2)",
                  background: "var(--ember-tint)",
                  color: "var(--ember)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  animation: "cf-pulse 2.4s ease-in-out infinite",
                }}
              >
                <Icon name="clapperboard" size={26} />
              </div>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--ember)",
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                }}
              >
                INVESTIGACIÓN EN CURSO
              </div>
              <h4
                style={{
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 700,
                  fontSize: 28,
                  margin: 0,
                  color: "var(--paper)",
                  letterSpacing: "-0.02em",
                }}
              >
                El estudio está rodando
              </h4>
              <p
                style={{
                  color: "var(--paper-dim)",
                  fontSize: 14,
                  maxWidth: 360,
                  margin: 0,
                  lineHeight: 1.5,
                }}
              >
                Estamos investigando el tema y escribiendo una narrativa
                cinematográfica. Suele tomar entre 1 y 2 minutos.
              </p>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-5)" }}>
        <StatsPanel
          wordCount={wordCount}
          estimatedMinutes={minutes}
          approved={!!project.script?.approved}
        />
        {editedScript && <ViralityPanel text={editedScript} />}
      </div>
    </div>
  );
}
