"use client";
import Link from "next/link";
import Icon from "@/components/Icon";
import { getMonogram } from "@/lib/agentVisual";
import { formatRelativeTime } from "@/lib/format";

/**
 * ProjectHeader — Editorial Cinematic v2.
 *
 * Header limpio: back link + eyebrow agente (color del agente) +
 * fecha relativa + título Fraunces italic + acciones download.
 *
 * La barra de progreso ya NO vive aquí (sale a ProgressPanel separado
 * cuando isProcessing) — ver `web/components/project/ProgressPanel.js`.
 *
 * Recibe:
 *   - project, agent (objeto SYSTEM_AGENTS)
 *   - id (projectId)
 *   - onDownloadVideo (fetch URL firmada y open)
 */
export default function ProjectHeader({
  project,
  agent,
  id,
  onDownloadVideo,
}) {
  const color = agent?.color || "var(--ember)";
  const mono = getMonogram(project.agentId);
  const created = formatRelativeTime(project.createdAt);
  const isCompleted = project.status === "completed";

  return (
    <header className="cf-fade" style={{ marginBottom: "var(--s-6)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <Link
          href="/dashboard"
          style={{
            color: "var(--paper-mute)",
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            font: "var(--t-mono-sm)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            transition: "color var(--dur-base) var(--ease-out)",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--paper)")}
          onMouseLeave={(e) =>
            (e.currentTarget.style.color = "var(--paper-mute)")
          }
        >
          <Icon name="arrowLeft" size={14} /> DASHBOARD
        </Link>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", gap: 16, flex: 1, minWidth: 0 }}>
          {/* Tile monograma del agente */}
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "var(--r-2)",
              background: `${color}22`,
              color,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 800,
              fontSize: 24,
              lineHeight: 1,
              flex: "none",
              border: `1px solid ${color}3D`,
            }}
          >
            {mono}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                font: "var(--t-mono-sm)",
                color: "var(--paper-dim)",
                marginBottom: 8,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                flexWrap: "wrap",
              }}
            >
              <span style={{ color, fontWeight: 600 }}>
                {agent?.name?.toUpperCase() || project.agentId}
              </span>
              {created && (
                <>
                  <span aria-hidden>·</span>
                  <span>CREADO {created.toUpperCase()}</span>
                </>
              )}
            </div>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontStyle: "italic",
                fontWeight: 700,
                fontSize: "clamp(28px, 4vw, 44px)",
                lineHeight: 1.05,
                letterSpacing: "-0.02em",
                color: "var(--paper)",
                margin: 0,
              }}
            >
              {project.title}
            </h1>
          </div>
        </div>

        {isCompleted && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={onDownloadVideo}
              className="cf-btn cf-btn--secondary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Icon name="download" size={16} /> Descargar video
            </button>
            <a
              href={`${process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com"}/download/all/${encodeURIComponent(id)}`}
              className="cf-btn cf-btn--ghost"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                textDecoration: "none",
              }}
              target="_blank"
              rel="noopener noreferrer"
              title="Todo el material del proyecto en un ZIP organizado"
            >
              <Icon name="package" size={16} /> Material completo
            </a>
          </div>
        )}
      </div>
    </header>
  );
}
