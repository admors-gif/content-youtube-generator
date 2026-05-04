"use client";
import Icon from "@/components/Icon";

/**
 * VideoPlayer — Editorial Cinematic v2.
 *
 * cf-card con header eyebrow REPRODUCTOR + badges + acción.
 * Botón "Cargar reproductor" cf-btn primary con Icon play.
 * Errors en cf-card border bad con Icon alert.
 */
export default function VideoPlayer({ project, videoState, onLoad, onCopyUrl }) {
  return (
    <div
      className="cf-card cf-fade"
      style={{
        marginBottom: "var(--s-6)",
        padding: "var(--s-5)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: videoState.url || videoState.error ? "var(--s-4)" : "0",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            REPRODUCTOR
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginTop: 4,
              flexWrap: "wrap",
            }}
          >
            {project.hasSubtitles && (
              <span className="cf-badge cf-badge--ok">CON SUBTÍTULOS</span>
            )}
            {project.videoSizeMB && (
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-dim)",
                }}
              >
                {project.videoSizeMB} MB
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {!videoState.url && !videoState.loading && (
            <button
              onClick={onLoad}
              className="cf-btn cf-btn--primary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Icon name="play" size={16} /> Cargar reproductor
            </button>
          )}
          {videoState.loading && (
            <span
              style={{
                font: "var(--t-mono-sm)",
                color: "var(--paper-dim)",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <Icon name="refresh" size={14} /> Preparando…
            </span>
          )}
          {videoState.url && (
            <button
              onClick={onCopyUrl}
              className="cf-btn cf-btn--ghost cf-btn--sm"
              title="Copiar enlace al portapapeles"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <Icon name="copy" size={14} /> Copiar enlace
            </button>
          )}
        </div>
      </div>

      {videoState.error && (
        <div
          style={{
            padding: "12px 14px",
            background: "rgba(216, 98, 90, 0.08)",
            border: "1px solid var(--bad)",
            borderRadius: "var(--r-2)",
            color: "var(--bad)",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <Icon name="alert" size={18} />
          <div style={{ flex: 1 }}>{videoState.error}</div>
          <button
            onClick={onLoad}
            className="cf-btn cf-btn--ghost cf-btn--sm"
            style={{ color: "var(--bad)", borderColor: "var(--bad)" }}
          >
            Reintentar
          </button>
        </div>
      )}

      {videoState.url && (
        <video
          src={videoState.url}
          controls
          preload="metadata"
          style={{
            width: "100%",
            maxHeight: "70vh",
            background: "#000",
            borderRadius: "var(--r-2)",
            border: "1px solid var(--rule-1)",
            display: "block",
          }}
        >
          Tu navegador no soporta video HTML5.
        </video>
      )}
    </div>
  );
}
