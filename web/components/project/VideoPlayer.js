"use client";
/**
 * VideoPlayer (presentacional).
 *
 * Recibe del container:
 *   - project: necesario para hasSubtitles + videoSizeMB en el header
 *   - videoState: { url, loading, error }
 *   - onLoad: callback que dispara loadVideoPlayer (lazy fetch URL firmada)
 *   - onCopyUrl: callback que copia al clipboard
 *
 * Fase 7.1: render IDÉNTICO. Fase 7.2 aplicará cf-card.
 */
export default function VideoPlayer({ project, videoState, onLoad, onCopyUrl }) {
  return (
    <div
      className="glass-card animate-fade-in"
      style={{ marginBottom: "32px", padding: "20px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: videoState.url ? "16px" : "0",
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: "16px",
            fontWeight: "bold",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          🎬 Reproductor
          {project.hasSubtitles && (
            <span className="badge badge-free" style={{ fontSize: "10px" }}>
              Con subtítulos
            </span>
          )}
          {project.videoSizeMB && (
            <span
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                fontWeight: "normal",
              }}
            >
              {project.videoSizeMB} MB
            </span>
          )}
        </h3>
        {!videoState.url && !videoState.loading && (
          <button
            onClick={onLoad}
            className="btn-glow"
            style={{
              padding: "8px 16px",
              fontSize: "13px",
              border: "none",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            ▶️ Cargar reproductor
          </button>
        )}
        {videoState.loading && (
          <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
            Preparando reproductor…
          </span>
        )}
        {videoState.url && (
          <button
            onClick={onCopyUrl}
            className="btn-secondary"
            style={{ padding: "6px 12px", fontSize: "12px", cursor: "pointer" }}
            title="Copiar enlace al portapapeles"
          >
            📋 Copiar enlace
          </button>
        )}
      </div>

      {videoState.error && (
        <div
          style={{
            padding: "12px",
            background: "rgba(220, 38, 38, 0.1)",
            border: "1px solid rgba(220, 38, 38, 0.3)",
            borderRadius: "8px",
            color: "#fca5a5",
            fontSize: "13px",
          }}
        >
          ❌ {videoState.error}
          <button
            onClick={onLoad}
            style={{
              marginLeft: "12px",
              padding: "4px 10px",
              fontSize: "12px",
              background: "transparent",
              border: "1px solid currentColor",
              color: "inherit",
              borderRadius: "4px",
              cursor: "pointer",
            }}
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
            borderRadius: "8px",
            display: "block",
          }}
        >
          Tu navegador no soporta video HTML5.
        </video>
      )}
    </div>
  );
}
