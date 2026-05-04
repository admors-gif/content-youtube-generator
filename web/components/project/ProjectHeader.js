"use client";
/**
 * Project header (presentacional).
 *
 * Recibe del container:
 *   - project, agent (objeto SYSTEM_AGENTS o undefined)
 *   - displayPercent (smooth interpolated)
 *   - eta (string o null)
 *   - isProcessing (bool)
 *   - id (projectId)
 *   - onDownloadVideo, onDownloadAll (callbacks)
 *
 * Fase 7.1: render IDÉNTICO al legacy (glass-card, badge, etc.).
 * Fase 7.2 reemplazará el visual por cf-card + iconos editoriales.
 */
export default function ProjectHeader({
  project,
  agent,
  displayPercent,
  eta,
  isProcessing,
  id,
  onDownloadVideo,
}) {
  return (
    <div
      className="glass-card"
      style={{
        marginBottom: "32px",
        padding: "24px",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "16px",
        borderLeft: `4px solid ${agent?.color || "var(--accent)"}`,
      }}
    >
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "8px",
          }}
        >
          <span style={{ fontSize: "32px" }}>{agent?.emoji}</span>
          <span className="badge badge-pro">{project.status.toUpperCase()}</span>
        </div>
        <h1 style={{ fontSize: "28px", fontWeight: "800", margin: "0 0 4px 0" }}>
          {project.title}
        </h1>
        <p
          style={{
            fontSize: "14px",
            color: "var(--text-secondary)",
            margin: 0,
          }}
        >
          Agente: {agent?.name || project.agentId} • Creado:{" "}
          {project.createdAt?.toDate?.().toLocaleDateString?.()}
        </p>
      </div>

      {/* Barra de Progreso Mágica — Smooth Interpolation */}
      <div
        style={{
          background: "var(--bg-card)",
          padding: "16px",
          borderRadius: "12px",
          border: "1px solid var(--border)",
          minWidth: "300px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            height: "4px",
            background:
              displayPercent >= 100
                ? "var(--success, #4ade80)"
                : "var(--accent)",
            transition: "width 0.8s ease-out",
            width: `${Math.round(displayPercent)}%`,
            boxShadow: isProcessing
              ? "0 0 12px var(--accent), 0 0 24px var(--accent)"
              : "0 0 10px var(--accent)",
          }}
        />
        {isProcessing && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: "4px",
              width: "100%",
              background:
                "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
              animation: "shimmer 2s infinite",
            }}
          />
        )}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "4px",
          }}
        >
          <span
            style={{
              fontSize: "11px",
              fontWeight: "bold",
              textTransform: "uppercase",
              letterSpacing: "1px",
              color:
                displayPercent >= 100
                  ? "var(--success, #4ade80)"
                  : "var(--accent)",
            }}
          >
            Progreso
          </span>
          <span style={{ fontSize: "12px", fontFamily: "monospace" }}>
            {Math.round(displayPercent)}%
          </span>
        </div>
        <p
          style={{
            fontSize: "14px",
            fontWeight: "500",
            margin: 0,
            animation: isProcessing ? "pulse 2s infinite" : "none",
          }}
        >
          {project.progress?.stepName || "Procesando..."}
        </p>
        {eta && (
          <p
            style={{
              fontSize: "11px",
              color: "var(--text-muted)",
              margin: "6px 0 0 0",
              fontFamily: "monospace",
            }}
          >
            ⏱️ {eta}
          </p>
        )}
      </div>

      {(project.status === "completed" || project.status === "producing") && (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {project.status === "completed" && (
            <>
              <button
                onClick={onDownloadVideo}
                className="btn-glow"
                style={{
                  padding: "10px 20px",
                  fontSize: "13px",
                  border: "none",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                📥 Descargar Video
              </button>
              <a
                href={`${process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com"}/download/all/${encodeURIComponent(id)}`}
                className="btn-secondary"
                style={{
                  padding: "10px 20px",
                  fontSize: "13px",
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                }}
                target="_blank"
                rel="noopener noreferrer"
                title="Todo el material del proyecto en un ZIP organizado"
              >
                📦 Descargar todo el material
              </a>
            </>
          )}
        </div>
      )}
    </div>
  );
}
