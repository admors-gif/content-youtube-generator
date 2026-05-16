"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
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

const STATUS_FILTERS = [
  { id: "all", label: "Todo" },
  { id: "ideas", label: "Ideas" },
  { id: "saved", label: "Guardadas" },
  { id: "project_created", label: "Con proyecto" },
  { id: "completed", label: "Completado" },
  { id: "archived", label: "Archivado" },
];

function buttonStyle(selected) {
  return {
    borderColor: selected ? "var(--ember)" : "var(--rule-1)",
    background: selected ? "var(--ember-tint)" : "var(--ink-1)",
    color: selected ? "var(--ember)" : "var(--paper-dim)",
  };
}

function matchesText(item, query, agentName) {
  const text = query.trim().toLowerCase();
  if (!text) return true;
  return [
    item.title,
    item.seoTitle,
    ...(item.seoKeywords || []),
    item.angle,
    item.summary,
    item.seriesName,
    item.seriesObjective,
    item.seriesCta,
    item.status,
    item.recommendedFormat,
    agentName,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(text);
}

function buildPreparedProjectUrl(item) {
  const params = new URLSearchParams({
    agentId: item.agentId || "",
    topic: item.seoTitle || item.angle || item.title || "",
    from: "library",
  });
  if (item.candidateHash) params.set("candidateHash", item.candidateHash);
  if (item.durationProfile) params.set("durationProfile", item.durationProfile);
  return `/dashboard/new?${params.toString()}`;
}

function IdeaCard({ item, creating, archiving, onCreate, onArchive }) {
  const risk = riskMeta(item.riskLevel);
  const status = ideaStatusMeta(item.status);
  const createDisabled = item.riskLevel === "high" || Boolean(item.projectId) || creating;

  return (
    <article className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 16 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <span className={`cf-badge ${status.badge}`}>{status.label}</span>
            <span className={`cf-badge ${risk.badge}`}>{risk.label}</span>
            <span className="cf-badge cf-badge--neutral">{formatRecommendation(item.recommendedFormat)}</span>
            {item.seriesName ? (
              <span
                className="cf-badge cf-badge--creator"
                title={item.seriesObjective || item.seriesName}
                style={{ maxWidth: "100%", whiteSpace: "normal", lineHeight: 1.35 }}
              >
                {item.seriesName}
              </span>
            ) : null}
          </div>
          <h3 className="cf-h3" style={{ margin: "0 0 8px", lineHeight: 1.2 }}>
            {item.seoTitle || item.angle || item.title}
          </h3>
          {item.seoKeywords?.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
              {item.seoKeywords.slice(0, 5).map((keyword) => (
                <span key={keyword} className="cf-badge cf-badge--creator">
                  {keyword}
                </span>
              ))}
            </div>
          )}
          <p className="cf-body" style={{ margin: 0, lineHeight: 1.5 }}>
            {item.summary || item.title}
          </p>
          {item.seriesCta ? (
            <p className="cf-caption" style={{ margin: "10px 0 0", lineHeight: 1.45 }}>
              CTA: {item.seriesCta}
            </p>
          ) : null}
          {item.knowledgeSignals?.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
              {item.knowledgeSignals.slice(0, 3).map((signal) => (
                <span
                  key={`${signal.title}-${signal.excerpt?.slice(0, 24)}`}
                  className="cf-badge cf-badge--neutral"
                  title={signal.excerpt || signal.title}
                >
                  <Icon name="bookOpen" size={12} />
                  {signal.title}
                </span>
              ))}
            </div>
          )}
          {item.sources?.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
              {item.sources.slice(0, 3).map((source) => (
                <a
                  key={source.url || source.domain || source.title}
                  className="cf-badge cf-badge--neutral"
                  href={source.url || "#"}
                  target="_blank"
                  rel="noreferrer"
                  style={{ textDecoration: "none" }}
                >
                  {source.domain || source.title}
                </a>
              ))}
            </div>
          )}
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 34,
              lineHeight: 1,
              fontWeight: 800,
              color: "var(--ember)",
            }}
          >
            {Number(item.editorialScore || 0)}
          </div>
          <div className="cf-caption">score</div>
          {item.scores?.audience ? (
            <div className="cf-caption">audiencia {Number(item.scores.audience || 0)}</div>
          ) : null}
        </div>
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
        {item.projectId ? (
          <Link
            className="cf-btn cf-btn--secondary cf-btn--sm"
            href={`/dashboard/project/${item.projectId}`}
            style={{ textDecoration: "none" }}
          >
            <Icon name="externalLink" size={14} />
            Abrir proyecto
          </Link>
        ) : (
          <button
            className="cf-btn cf-btn--primary cf-btn--sm"
            onClick={onCreate}
            disabled={createDisabled}
            type="button"
          >
            <Icon name="plus" size={14} />
            {creating ? "Preparando" : "Preparar proyecto"}
          </button>
        )}
        {item.status !== "archived" && (
          <button
            className="cf-btn cf-btn--ghost cf-btn--sm"
            onClick={onArchive}
            disabled={archiving}
            type="button"
          >
            <Icon name="trash" size={14} />
            {archiving ? "Archivando" : "Archivar"}
          </button>
        )}
      </div>
    </article>
  );
}

function ProjectCard({ item }) {
  const status = projectStatusMeta(item.status);
  return (
    <article className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <span className={`cf-badge ${status.badge}`}>{status.label}</span>
            <span className="cf-badge cf-badge--neutral">{item.platform || "youtube"}</span>
            {item.shortsCount > 0 && <span className="cf-badge cf-badge--starter">{item.shortsCount} Shorts</span>}
          </div>
          <h3 className="cf-h3" style={{ margin: "0 0 8px", lineHeight: 1.2 }}>
            {item.title || "Sin titulo"}
          </h3>
          <div className="cf-caption">Actualizado {formatRadarDate(item.updatedAt || item.createdAt)}</div>
        </div>
        <Link
          className="cf-btn cf-btn--secondary cf-btn--sm"
          href={`/dashboard/project/${item.projectId}`}
          style={{ textDecoration: "none" }}
        >
          <Icon name="externalLink" size={14} />
          Abrir
        </Link>
      </div>
    </article>
  );
}

export default function LibraryPage() {
  const { user, profile, loading: authLoading } = useAuth();
  const router = useRouter();
  const admin = isAdminUser(user, profile);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    agentId: "all",
    status: "all",
    format: "all",
    risk: "all",
  });
  const [creatingHash, setCreatingHash] = useState("");
  const [archivingId, setArchivingId] = useState("");
  const [seedingWellness, setSeedingWellness] = useState(false);
  const [seedingPodcast, setSeedingPodcast] = useState(false);

  const fetchLibrary = useCallback(async () => {
    const res = await authedFetch(user, `${getApiBase()}/library/agents`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.error || "No se pudo leer la biblioteca.");
    return data.agents || [];
  }, [user]);

  const loadLibrary = async () => {
    if (!user || !admin) return;
    setLoading(true);
    setError("");
    try {
      setGroups(await fetchLibrary());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authLoading || !user || !admin) return;
    let cancelled = false;
    const loadInitial = async () => {
      setLoading(true);
      setError("");
      try {
        const nextGroups = await fetchLibrary();
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
  }, [authLoading, user, admin, fetchLibrary]);

  const visibleGroups = useMemo(() => {
    return groups
      .map((group) => {
        const agentName = agentDisplayName(group.agentId, group.name, SYSTEM_AGENTS);
        if (filters.agentId !== "all" && group.agentId !== filters.agentId) return null;
        const ideas = (group.ideas || []).filter((item) => {
          if (filters.status === "completed") return false;
          if (filters.status === "ideas" && item.status === "archived") return false;
          if (!["all", "ideas"].includes(filters.status) && item.status !== filters.status) return false;
          if (filters.format !== "all" && item.recommendedFormat !== filters.format) return false;
          if (filters.risk !== "all" && item.riskLevel !== filters.risk) return false;
          return matchesText(item, query, agentName);
        });
        const projects = (group.projects || []).filter((item) => {
          if (["ideas", "saved", "archived"].includes(filters.status)) return false;
          if (filters.status === "completed" && item.status !== "completed") return false;
          if (filters.status === "project_created" && !item.projectId) return false;
          if (filters.format !== "all" && item.format !== filters.format && item.platform !== filters.format) return false;
          return matchesText(item, query, agentName);
        });
        if (!ideas.length && !projects.length) return null;
        return { ...group, name: agentName, ideas, projects };
      })
      .filter(Boolean);
  }, [groups, filters, query]);

  const totals = useMemo(() => {
    const ideas = groups.reduce((sum, group) => sum + (group.ideas?.length || 0), 0);
    const projects = groups.reduce((sum, group) => sum + (group.projects?.length || 0), 0);
    const completed = groups.reduce((sum, group) => sum + (group.counts?.completed || 0), 0);
    const gaps = groups.reduce((sum, group) => sum + (group.gaps?.length || 0), 0);
    return { ideas, projects, completed, gaps };
  }, [groups]);

  const createProject = async (item) => {
    if (!item.candidateHash || item.riskLevel === "high") return;
    setCreatingHash(item.candidateHash);
    setError("");
    setNotice("");
    try {
      router.push(buildPreparedProjectUrl(item));
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingHash("");
    }
  };

  const archiveItem = async (item) => {
    if (!item.itemId) return;
    setArchivingId(item.itemId);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/library/items/${item.itemId}/archive`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo archivar la idea.");
      setNotice("Idea archivada.");
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setArchivingId("");
    }
  };

  const seedWellnessTopics = async () => {
    if (!user || !admin) return;
    setSeedingWellness(true);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/library/seed-wellness-topics`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron importar los temas.");
      setNotice(`Temas wellness listos: ${data.created || 0} nuevos, ${data.updated || 0} ya existentes.`);
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setSeedingWellness(false);
    }
  };

  const seedPodcastTopics = async () => {
    if (!user || !admin) return;
    setSeedingPodcast(true);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/library/seed-podcast-topics`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron importar los temas.");
      setNotice(`Temas de Esto no es amor listos: ${data.created || 0} nuevos, ${data.updated || 0} ya existentes.`);
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setSeedingPodcast(false);
    }
  };

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
          BIBLIOTECA
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
          <div>
            <h1 className="cf-h1" style={{ margin: 0 }}>Biblioteca por agente</h1>
            <p className="cf-body" style={{ margin: "12px 0 0", maxWidth: 680 }}>
              Ideas guardadas, proyectos creados, material completado y huecos editoriales.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="cf-btn cf-btn--secondary"
              onClick={seedWellnessTopics}
              disabled={seedingWellness}
              type="button"
            >
              <Icon name="sparkles" size={16} />
              {seedingWellness ? "Importando" : "Cargar 50 meditaciones"}
            </button>
            <button
              className="cf-btn cf-btn--secondary"
              onClick={seedPodcastTopics}
              disabled={seedingPodcast}
              type="button"
            >
              <Icon name="bookOpen" size={16} />
              {seedingPodcast ? "Importando" : "Cargar 100 Esto no es amor"}
            </button>
            <button className="cf-btn cf-btn--secondary" onClick={loadLibrary} disabled={loading} type="button">
              <Icon name="refresh" size={16} />
              {loading ? "Cargando" : "Actualizar"}
            </button>
          </div>
        </div>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: "var(--s-5)" }}>
        {[
          ["Ideas", totals.ideas],
          ["Proyectos", totals.projects],
          ["Completados", totals.completed],
          ["Huecos", totals.gaps],
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
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Riesgo</div>
            <select
              className="cf-input"
              value={filters.risk}
              onChange={(event) => setFilters((current) => ({ ...current, risk: event.target.value }))}
            >
              <option value="all">Todos</option>
              <option value="low">Bajo</option>
              <option value="medium">Medio</option>
              <option value="high">Alto</option>
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Buscar</div>
            <input
              className="cf-input"
              value={query}
              placeholder="Tema, agente o estado"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
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

      {(error || notice) && (
        <div
          className="cf-card"
          style={{
            padding: "var(--s-4)",
            marginBottom: "var(--s-5)",
            borderColor: error ? "var(--bad)" : "var(--ok)",
            color: error ? "var(--bad)" : "var(--ok)",
          }}
        >
          {error || notice}
        </div>
      )}

      {loading && (
        <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
          <Icon name="refresh" size={24} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
          <div className="cf-body">Cargando biblioteca.</div>
        </div>
      )}

      {!loading && visibleGroups.length === 0 && (
        <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
          <Icon name="bookOpen" size={28} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
          <h2 className="cf-h3" style={{ margin: 0 }}>Sin material para estos filtros</h2>
        </div>
      )}

      <section style={{ display: "grid", gap: "var(--s-7)" }}>
        {visibleGroups.map((group) => (
          <div key={group.agentId} className="cf-fade">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <AgentMonogram agent={group.agentId} size={44} />
                <div>
                  <h2 className="cf-h3" style={{ margin: 0 }}>{group.name}</h2>
                  <div className="cf-caption">
                    {group.ideas.length} idea(s) · {group.projects.length} proyecto(s)
                  </div>
                </div>
              </div>
              {group.gaps?.length > 0 && (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {group.gaps.slice(0, 3).map((gap) => (
                    <span key={gap} className="cf-badge cf-badge--warn">{gap}</span>
                  ))}
                </div>
              )}
            </div>

            {group.ideas.length > 0 && (
              <div style={{ display: "grid", gap: 14, marginBottom: group.projects.length ? "var(--s-5)" : 0 }}>
                <div className="cf-mono-sm">IDEAS</div>
                {group.ideas.map((item) => (
                  <IdeaCard
                    key={item.itemId || item.candidateHash}
                    item={item}
                    creating={creatingHash === item.candidateHash}
                    archiving={archivingId === item.itemId}
                    onCreate={() => createProject(item)}
                    onArchive={() => archiveItem(item)}
                  />
                ))}
              </div>
            )}

            {group.projects.length > 0 && (
              <div style={{ display: "grid", gap: 14 }}>
                <div className="cf-mono-sm">MATERIAL CREADO</div>
                {group.projects.map((item) => (
                  <ProjectCard key={item.projectId} item={item} />
                ))}
              </div>
            )}
          </div>
        ))}
      </section>
    </div>
  );
}
