"use client";
import ModerationAlert from "./ModerationAlert";
import FactCheckPanel from "./FactCheckPanel";
import PodcastBubbles from "./PodcastBubbles";
import ApproveTimer from "./ApproveTimer";
import StatsPanel from "./StatsPanel";
import ViralityPanel from "./ViralityPanel";

/**
 * ScriptTab (orquestador presentacional).
 *
 * Compone los paneles de moderación + fact-check + editor de guión
 * (con podcast bubbles para format=podcast) + sidebar (stats + virality).
 *
 * Recibe del container TODA la state — no maneja nada interno propio.
 *
 *   - project, editedScript, setEditedScript
 *   - timerActive, timerSeconds, timerPaused, setTimerPaused
 *   - autoApproveSeconds (constante para el ratio del conic-gradient)
 *   - onApprove (callback handleSaveScript del container)
 *
 * Fase 7.1: render IDÉNTICO al legacy.
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

  return (
    <div
      className="animate-fade-in"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 300px",
        gap: "24px",
      }}
    >
      <div>
        <ModerationAlert moderation={project.moderation} />
        <FactCheckPanel factCheck={project.factCheck} />

        <div
          className="glass-card"
          style={{ padding: "24px", position: "relative" }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px",
            }}
          >
            <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>
              Edición de Guión
            </h3>

            {hasScript ? (
              isProducing ? (
                <span
                  className="badge badge-starter"
                  style={{ animation: "pulse 2s infinite" }}
                >
                  ⚙️ Produciendo...
                </span>
              ) : isApproved ? (
                <span className="badge badge-free">✅ Ya aprobado</span>
              ) : (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
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
                    className="btn-glow"
                    style={{ padding: "8px 16px", fontSize: "13px" }}
                  >
                    Aprobar y Producir 🚀
                  </button>
                </div>
              )
            ) : (
              <span
                className="badge badge-free"
                style={{ animation: "pulse 2s infinite" }}
              >
                Esperando a la IA...
              </span>
            )}
          </div>

          {hasScript ? (
            <>
              {/* Vista de conversación (solo para podcast) */}
              {project.format === "podcast" && (
                <PodcastBubbles scriptText={editedScript} />
              )}
              <textarea
                value={editedScript}
                onChange={(e) => setEditedScript(e.target.value)}
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.2)",
                  color: "white",
                  padding: "16px",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  outline: "none",
                  fontFamily: "serif",
                  fontSize: "18px",
                  lineHeight: "1.6",
                  resize: "vertical",
                  minHeight: "500px",
                }}
                placeholder="El guión aparecerá aquí..."
              />
            </>
          ) : (
            <div
              style={{
                height: "400px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                textAlign: "center",
                border: "2px dashed var(--border)",
                borderRadius: "12px",
              }}
            >
              <div
                style={{
                  fontSize: "48px",
                  marginBottom: "16px",
                  animation: "bounce 2s infinite",
                }}
              >
                🤖
              </div>
              <h4
                style={{
                  fontSize: "18px",
                  fontWeight: "bold",
                  margin: "0 0 8px 0",
                }}
              >
                El Chef está cocinando
              </h4>
              <p
                style={{
                  color: "var(--text-muted)",
                  fontSize: "14px",
                  maxWidth: "300px",
                  margin: 0,
                }}
              >
                El motor de IA está investigando el tema y escribiendo una
                narrativa cinematográfica. Esto toma de 1 a 2 minutos.
              </p>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <StatsPanel
          wordCount={project.script?.wordCount || 0}
          estimatedMinutes={project.script?.estimatedMinutes || 0}
          approved={!!project.script?.approved}
        />
        {editedScript && <ViralityPanel text={editedScript} />}
      </div>
    </div>
  );
}
