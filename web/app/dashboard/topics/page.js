"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import Icon from "@/components/Icon";
import { AgentMonogram } from "@/lib/agentVisual";
import { isAdminUser } from "@/lib/admin";
import { authedFetch, getApiBase } from "@/lib/apiClient";
import { SYSTEM_AGENTS } from "@/lib/agents";
import { useAuth } from "@/context/AuthContext";
import {
  RADAR_FORMAT_OPTIONS,
  agentDisplayName,
  compactNumber,
  formatRadarDate,
  formatRecommendation,
  ideaStatusMeta,
  projectStatusMeta,
  riskMeta,
} from "@/lib/radarUi";

const TYPE_FILTERS = [
  { id: "all", label: "Todo" },
  { id: "idea", label: "Ideas" },
  { id: "project", label: "Proyectos" },
];

const STATUS_FILTERS = [
  { id: "all", label: "Todos" },
  { id: "saved", label: "Guardado" },
  { id: "project_created", label: "Con proyecto" },
  { id: "completed", label: "Completado" },
  { id: "in_progress", label: "En curso" },
  { id: "failed", label: "Fallidos" },
  { id: "archived", label: "Archivado" },
];

function buttonStyle(selected) {
  return {
    borderColor: selected ? "var(--ember)" : "var(--rule-1)",
    background: selected ? "var(--ember-tint)" : "var(--ink-1)",
    color: selected ? "var(--ember)" : "var(--paper-dim)",
  };
}

function normalizeStatus(value) {
  const status = String(value || "").toLowerCase();
  if (["failed", "error"].includes(status)) return "failed";
  if (status === "completed") return "completed";
  if (status === "saved") return "saved";
  if (status === "project_created") return "project_created";
  if (status === "archived") return "archived";
  if (status && !["draft", "suggested"].includes(status)) return "in_progress";
  return status || "draft";
}

function rowStatusMeta(row) {
  if (row.type === "idea") return ideaStatusMeta(row.status);
  return projectStatusMeta(row.status);
}

function csvCell(value) {
  const clean = String(value ?? "").replace(/\r?\n/g, " ").replace(/\s+/g, " ").trim();
  return `"${clean.replace(/"/g, '""')}"`;
}

function downloadRowsAsCsv(rows) {
  const headers = [
    "Tipo",
    "Estado",
    "Agente",
    "Tema",
    "Formato",
    "Score editorial",
    "Viralidad",
    "Retencion",
    "Riesgo",
    "Proyecto ID",
    "Video",
    "Shorts",
    "Actualizado",
    "Creado",
    "Fuente",
  ];
  const lines = [
    headers,
    ...rows.map((row) => [
      row.typeLabel,
      row.statusLabel,
      row.agentName,
      row.topic,
      row.formatLabel,
      row.editorialScore,
      row.viralScore,
      row.retentionScore,
      row.riskLabel,
      row.projectId,
      row.hasVideo ? "si" : "no",
      row.shortsCount || 0,
      row.updatedAt || "",
      row.createdAt || "",
      row.sourceLabel || "",
    ]),
  ]
    .map((line) => line.map(csvCell).join(";"))
    .join("\n");
  const blob = new Blob([`\uFEFF${lines}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `content-factory-temas-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function buildPreparedProjectUrl(row) {
  const params = new URLSearchParams({
    agentId: row.agentId || "",
    topic: row.topic || "",
    from: "topics",
  });
  if (row.candidateHash) params.set("candidateHash", row.candidateHash);
  if (row.durationProfile) params.set("durationProfile", row.durationProfile);
  return `/dashboard/new?${params.toString()}`;
}

function flattenGroups(groups) {
  const rows = [];
  for (const group of groups || []) {
    const agentName = agentDisplayName(group.agentId, group.name, SYSTEM_AGENTS);
    for (const item of group.ideas || []) {
      const scores = item.scores || {};
      const titleLab = item.titleLab || {};
      const status = item.status || "suggested";
      rows.push({
        id: item.itemId || item.candidateHash,
        type: "idea",
        typeLabel: "Idea",
        status,
        statusKey: normalizeStatus(status),
        statusLabel: ideaStatusMeta(status).label,
        agentId: item.agentId || group.agentId,
        agentName,
        topic: item.seoTitle || item.angle || item.title || "Sin titulo",
        summary: item.summary || "",
        format: item.recommendedFormat || "youtube_long",
        formatLabel: formatRecommendation(item.recommendedFormat),
        editorialScore: Number(item.editorialScore || scores.overall || 0),
        viralScore: Number(titleLab.viralScore || scores.viral || item.viralScore || 0),
        retentionScore: Number(titleLab.retentionScore || scores.retention || item.retentionScore || 0),
        riskLevel: item.riskLevel || "low",
        riskLabel: riskMeta(item.riskLevel).label,
        projectId: item.projectId || "",
        candidateHash: item.candidateHash || "",
        durationProfile: item.durationProfile || "",
        hasVideo: false,
        shortsCount: 0,
        createdAt: item.createdAt || "",
        updatedAt: item.updatedAt || "",
        sourceLabel: item.seriesName || item.searchIntent || item.intent || "Biblioteca",
      });
    }
    for (const item of group.projects || []) {
      const status = item.status || "draft";
      rows.push({
        id: item.projectId,
        type: "project",
        typeLabel: "Proyecto",
        status,
        statusKey: normalizeStatus(status),
        statusLabel: projectStatusMeta(status).label,
        agentId: item.agentId || group.agentId,
        agentName,
        topic: item.title || "Sin titulo",
        summary: "",
        format: item.format || item.platform || "youtube",
        formatLabel: item.format || item.platform || "youtube",
        editorialScore: 0,
        viralScore: 0,
        retentionScore: 0,
        riskLevel: "low",
        riskLabel: "Riesgo bajo",
        projectId: item.projectId || "",
        candidateHash: "",
        durationProfile: "",
        hasVideo: Boolean(item.hasVideo || item.videoUrl),
        shortsCount: Number(item.shortsCount || 0),
        createdAt: item.createdAt || "",
        updatedAt: item.updatedAt || item.createdAt || "",
        sourceLabel: "Proyecto",
      });
    }
  }
  return rows.sort((a, b) => new Date(b.updatedAt || b.createdAt || 0) - new Date(a.updatedAt || a.createdAt || 0));
}

function matchesRow(row, query) {
  const text = query.trim().toLowerCase();
  if (!text) return true;
  return [
    row.topic,
    row.agentName,
    row.statusLabel,
    row.typeLabel,
    row.formatLabel,
    row.riskLabel,
    row.summary,
    row.sourceLabel,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(text);
}

export default function TopicsPage() {
  const { user, profile, loading: authLoading } = useAuth();
  const admin = isAdminUser(user, profile);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    type: "all",
    status: "all",
    agentId: "all",
    format: "all",
  });

  const fetchTopics = useCallback(async () => {
    const res = await authedFetch(user, `${getApiBase()}/library/agents`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron cargar los temas.");
    return data.agents || [];
  }, [user]);

  const loadTopics = useCallback(async () => {
    if (!user || !admin) return;
    setLoading(true);
    setError("");
    try {
      setGroups(await fetchTopics());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [admin, fetchTopics, user]);

  useEffect(() => {
    if (authLoading || !user || !admin) return;
    let cancelled = false;
    const loadInitial = async () => {
      setLoading(true);
      setError("");
      try {
        const nextGroups = await fetchTopics();
        if (!cancelled) setGroups(nextGroups);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadInitial();
    return () => {
      cancelled = true;
    };
  }, [admin, authLoading, fetchTopics, user]);

  const rows = useMemo(() => flattenGroups(groups), [groups]);
  const visibleRows = useMemo(() => {
    return rows.filter((row) => {
      if (filters.type !== "all" && row.type !== filters.type) return false;
      if (filters.status !== "all" && row.statusKey !== filters.status) return false;
      if (filters.agentId !== "all" && row.agentId !== filters.agentId) return false;
      if (filters.format !== "all" && row.format !== filters.format) return false;
      return matchesRow(row, query);
    });
  }, [filters, query, rows]);

  const totals = useMemo(() => {
    return {
      all: rows.length,
      ideas: rows.filter((row) => row.type === "idea").length,
      projects: rows.filter((row) => row.type === "project").length,
      completed: rows.filter((row) => row.statusKey === "completed").length,
    };
  }, [rows]);

  if (!authLoading && !admin) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
        <Icon name="lock" size={30} style={{ margin: "0 auto 16px", color: "var(--paper-mute)" }} />
        <h1 className="cf-h2" style={{ margin: 0 }}>Acceso admin</h1>
      </div>
    );
  }

  return (
    <div>
      <header className="cf-fade" style={{ marginBottom: "var(--s-6)" }}>
        <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 10 }}>
          REGISTRO EDITORIAL
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
          <div>
            <h1 className="cf-h1" style={{ margin: 0 }}>Temas y estados</h1>
            <p className="cf-body" style={{ margin: "12px 0 0", maxWidth: 760 }}>
              Lista operativa de ideas guardadas, proyectos creados y material completado por agente.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="cf-btn cf-btn--secondary" onClick={loadTopics} disabled={loading} type="button">
              <Icon name="refresh" size={16} />
              {loading ? "Cargando" : "Actualizar"}
            </button>
            <button
              className="cf-btn cf-btn--primary"
              onClick={() => downloadRowsAsCsv(visibleRows)}
              disabled={!visibleRows.length}
              type="button"
            >
              <Icon name="download" size={16} />
              Descargar Excel
            </button>
          </div>
        </div>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 14, marginBottom: "var(--s-5)" }}>
        {[
          ["Total", totals.all],
          ["Ideas", totals.ideas],
          ["Proyectos", totals.projects],
          ["Completados", totals.completed],
        ].map(([label, value]) => (
          <div className="cf-card" key={label} style={{ padding: "var(--s-4)" }}>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>{label}</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 34, fontWeight: 800, lineHeight: 1 }}>
              {compactNumber(value)}
            </div>
          </div>
        ))}
      </section>

      <section className="cf-card cf-fade cf-fade--1" style={{ padding: "var(--s-5)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Buscar</div>
            <input
              className="cf-input"
              value={query}
              placeholder="Tema, agente, estado"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Agente</div>
            <select
              className="cf-input"
              value={filters.agentId}
              onChange={(event) => setFilters((current) => ({ ...current, agentId: event.target.value }))}
            >
              <option value="all">Todos</option>
              {SYSTEM_AGENTS.map((agent) => (
                <option key={agent.agentId} value={agent.agentId}>{agent.name}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Formato</div>
            <select
              className="cf-input"
              value={filters.format}
              onChange={(event) => setFilters((current) => ({ ...current, format: event.target.value }))}
            >
              {RADAR_FORMAT_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
              <option value="youtube">YouTube</option>
              <option value="podcast">Podcast</option>
            </select>
          </label>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
          {TYPE_FILTERS.map((option) => (
            <button
              key={option.id}
              className="cf-btn cf-btn--sm"
              style={buttonStyle(filters.type === option.id)}
              onClick={() => setFilters((current) => ({ ...current, type: option.id }))}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          {STATUS_FILTERS.map((option) => (
            <button
              key={option.id}
              className="cf-btn cf-btn--sm"
              style={buttonStyle(filters.status === option.id)}
              onClick={() => setFilters((current) => ({ ...current, status: option.id }))}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="cf-card" style={{ padding: "var(--s-4)", marginBottom: "var(--s-5)", borderColor: "var(--bad)", color: "var(--bad)" }}>
          {error}
        </div>
      )}

      <section className="cf-card cf-fade cf-fade--2" style={{ overflow: "hidden" }}>
        <div style={{ padding: "var(--s-4)", borderBottom: "1px solid var(--rule-1)", display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div className="cf-mono-sm">LISTA</div>
            <div className="cf-caption">{visibleRows.length} tema(s) visibles</div>
          </div>
          <div className="cf-caption">La descarga respeta los filtros actuales.</div>
        </div>

        {loading ? (
          <div style={{ padding: "var(--s-7)", textAlign: "center" }}>
            <Icon name="refresh" size={24} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
            <div className="cf-body">Cargando temas.</div>
          </div>
        ) : visibleRows.length === 0 ? (
          <div style={{ padding: "var(--s-7)", textAlign: "center" }}>
            <Icon name="fileText" size={28} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
            <h2 className="cf-h3" style={{ margin: 0 }}>Sin temas para estos filtros</h2>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 1080 }}>
              <thead>
                <tr>
                  {["Tema", "Agente", "Tipo", "Estado", "Formato", "Score", "Riesgo", "Material", "Actualizado"].map((header) => (
                    <th
                      key={header}
                      className="cf-mono-sm"
                      style={{
                        textAlign: "left",
                        padding: "14px 16px",
                        borderBottom: "1px solid var(--rule-1)",
                        color: "var(--paper-mute)",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => {
                  const status = rowStatusMeta(row);
                  const risk = riskMeta(row.riskLevel);
                  return (
                    <tr key={`${row.type}-${row.id}`} style={{ borderBottom: "1px solid var(--rule-1)" }}>
                      <td style={{ padding: "16px", maxWidth: 360 }}>
                        <div style={{ color: "var(--paper)", fontWeight: 800, lineHeight: 1.25 }}>{row.topic}</div>
                        {row.summary && <div className="cf-caption" style={{ marginTop: 6, lineHeight: 1.35 }}>{row.summary}</div>}
                      </td>
                      <td style={{ padding: "16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <AgentMonogram agent={row.agentId} size={34} />
                          <span>{row.agentName}</span>
                        </div>
                      </td>
                      <td style={{ padding: "16px" }}>
                        <span className="cf-badge cf-badge--neutral">{row.typeLabel}</span>
                      </td>
                      <td style={{ padding: "16px" }}>
                        <span className={`cf-badge ${status.badge}`}>{status.label}</span>
                      </td>
                      <td style={{ padding: "16px" }}>
                        <span className="cf-badge cf-badge--creator">{row.formatLabel}</span>
                      </td>
                      <td style={{ padding: "16px" }}>
                        <div style={{ color: "var(--paper)", fontWeight: 800 }}>{row.editorialScore || "—"}</div>
                        {(row.viralScore || row.retentionScore) ? (
                          <div className="cf-caption">V {row.viralScore || 0} · R {row.retentionScore || 0}</div>
                        ) : null}
                      </td>
                      <td style={{ padding: "16px" }}>
                        <span className={`cf-badge ${risk.badge}`}>{risk.label}</span>
                      </td>
                      <td style={{ padding: "16px" }}>
                        {row.projectId ? (
                          <Link className="cf-btn cf-btn--secondary cf-btn--sm" href={`/dashboard/project/${row.projectId}`} style={{ textDecoration: "none" }}>
                            <Icon name="externalLink" size={13} />
                            Abrir
                          </Link>
                        ) : row.type === "idea" ? (
                          <Link className="cf-btn cf-btn--primary cf-btn--sm" href={buildPreparedProjectUrl(row)} style={{ textDecoration: "none" }}>
                            <Icon name="arrowRight" size={13} />
                            Preparar
                          </Link>
                        ) : (
                          <span className="cf-caption">Sin proyecto</span>
                        )}
                        {row.hasVideo && <div className="cf-caption" style={{ marginTop: 6 }}>Video listo</div>}
                        {row.shortsCount > 0 && <div className="cf-caption">{row.shortsCount} Shorts</div>}
                      </td>
                      <td style={{ padding: "16px", color: "var(--paper-dim)" }}>
                        {formatRadarDate(row.updatedAt || row.createdAt)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
