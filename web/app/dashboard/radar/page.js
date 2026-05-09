"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Icon from "@/components/Icon";
import { AgentMonogram } from "@/lib/agentVisual";
import { isAdminUser } from "@/lib/admin";
import { authedFetch, getApiBase } from "@/lib/apiClient";
import { SYSTEM_AGENTS } from "@/lib/agents";
import { useAuth } from "@/context/AuthContext";
import {
  RADAR_CATEGORY_OPTIONS,
  RADAR_FORMAT_OPTIONS,
  RADAR_SCOPE_OPTIONS,
  RADAR_WINDOW_OPTIONS,
  agentDisplayName,
  compactNumber,
  formatRadarDate,
  formatRecommendation,
  ideaStatusMeta,
  riskMeta,
} from "@/lib/radarUi";

const RADAR_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_RADAR_ENABLED !== "false";
const DEFAULT_AGENT_ID = "agent_noticias_virales";

function buttonStyle(selected) {
  return {
    borderColor: selected ? "var(--ember)" : "var(--rule-1)",
    background: selected ? "var(--ember-tint)" : "var(--ink-1)",
    color: selected ? "var(--ember)" : "var(--paper-dim)",
  };
}

function buildRadarParams(filters, force = false) {
  const payload = {
    scope: filters.scope,
    market: filters.market,
    language: "es",
    category: filters.category,
    window: filters.window,
    limit: Number(filters.limit || 3),
    queryLimit: Number(filters.queryLimit || 2),
    force,
  };
  if (filters.scope === "agent") payload.agentId = filters.agentId || DEFAULT_AGENT_ID;
  if (filters.scope === "news") payload.agentId = DEFAULT_AGENT_ID;
  return payload;
}

function Score({ value }) {
  const score = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div style={{ display: "grid", gap: 7, minWidth: 92 }}>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 800,
          fontSize: 30,
          lineHeight: 1,
          color: score >= 76 ? "var(--ok)" : score >= 58 ? "var(--warn)" : "var(--paper-dim)",
        }}
      >
        {score}
      </div>
      <div
        style={{
          height: 4,
          borderRadius: 999,
          background: "var(--ink-3)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${score}%`,
            height: "100%",
            background: score >= 76 ? "var(--ok)" : score >= 58 ? "var(--warn)" : "var(--ember)",
          }}
        />
      </div>
    </div>
  );
}

function CandidateCard({ item, selected, saving, creating, onSelect, onSave, onCreate }) {
  const risk = riskMeta(item.riskLevel);
  const status = ideaStatusMeta(item.status);
  const createDisabled = item.riskLevel === "high" || Boolean(item.projectId) || creating;

  return (
    <article
      className="cf-card"
      style={{
        padding: "var(--s-5)",
        borderColor: selected ? "var(--ember)" : "var(--rule-1)",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
        <AgentMonogram agent={item.agentId} size={46} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <span className={`cf-badge ${risk.badge}`}>{risk.label}</span>
            <span className={`cf-badge ${status.badge}`}>{status.label}</span>
            <span className="cf-badge cf-badge--neutral">
              {formatRecommendation(item.recommendedFormat)}
            </span>
          </div>
          <h2 className="cf-h3" style={{ margin: "0 0 8px", lineHeight: 1.2 }}>
            {item.angle || item.title}
          </h2>
          <div className="cf-caption" style={{ marginBottom: 12 }}>
            {agentDisplayName(item.agentId, item.agentName, SYSTEM_AGENTS)}
          </div>
          <p className="cf-body" style={{ margin: 0, lineHeight: 1.5 }}>
            {item.summary}
          </p>
        </div>
        <Score value={item.editorialScore} />
      </div>

      {item.sources?.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
          {item.sources.slice(0, 3).map((source) => (
            <a
              key={source.url || source.domain || source.title}
              href={source.url || "#"}
              target="_blank"
              rel="noreferrer"
              className="cf-badge cf-badge--neutral"
              style={{ textDecoration: "none", maxWidth: "100%" }}
            >
              {source.domain || source.title}
            </a>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
        <button className="cf-btn cf-btn--ghost cf-btn--sm" onClick={onSelect} type="button">
          <Icon name="eye" size={14} />
          Detalle
        </button>
        <button
          className="cf-btn cf-btn--secondary cf-btn--sm"
          onClick={onSave}
          type="button"
          disabled={saving || item.status === "saved" || item.status === "project_created"}
        >
          <Icon name="bookOpen" size={14} />
          {saving ? "Guardando" : "Guardar"}
        </button>
        <button
          className="cf-btn cf-btn--primary cf-btn--sm"
          onClick={onCreate}
          type="button"
          disabled={createDisabled}
          title={item.riskLevel === "high" ? "Requiere revision editorial antes de crear proyecto" : ""}
        >
          <Icon name="plus" size={14} />
          {item.projectId ? "Proyecto creado" : creating ? "Creando" : "Crear proyecto"}
        </button>
      </div>
    </article>
  );
}

function DetailPanel({ item }) {
  if (!item) {
    return (
      <aside className="cf-card" style={{ padding: "var(--s-5)" }}>
        <div className="cf-mono-sm" style={{ marginBottom: 10 }}>
          DETALLE
        </div>
        <p className="cf-body" style={{ margin: 0 }}>
          Sin candidatos en el radar actual.
        </p>
      </aside>
    );
  }
  const risk = riskMeta(item.riskLevel);
  const scores = item.scores || {};
  const scoreRows = [
    ["Audiencia", scores.audience],
    ["Encaje", scores.fit],
    ["Arco", scores.storyArc],
    ["Frescura", scores.freshness],
    ["Produccion", scores.productionEase],
    ["Riesgo", scores.risk],
  ];

  return (
    <aside
      className="cf-card"
      style={{
        padding: "var(--s-5)",
        position: "sticky",
        top: 24,
      }}
    >
      <div className="cf-mono-sm" style={{ marginBottom: 12 }}>
        DETALLE EDITORIAL
      </div>
      <h2 className="cf-h3" style={{ margin: "0 0 10px", lineHeight: 1.2 }}>
        {item.title}
      </h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
        <span className={`cf-badge ${risk.badge}`}>{risk.label}</span>
        <span className="cf-badge cf-badge--neutral">{formatRecommendation(item.recommendedFormat)}</span>
      </div>
      <p className="cf-body" style={{ marginTop: 0 }}>{item.whyNow || item.summary}</p>
      {item.riskReason && (
        <div
          style={{
            border: "1px solid var(--rule-1)",
            borderLeft: `3px solid ${risk.color}`,
            borderRadius: "var(--r-2)",
            padding: "12px 14px",
            marginBottom: 18,
            color: "var(--paper-dim)",
            lineHeight: 1.45,
          }}
        >
          {item.riskReason}
        </div>
      )}

      <div style={{ display: "grid", gap: 10, marginBottom: 20 }}>
        {scoreRows.map(([label, value]) => (
          <div
            key={label}
            style={{
              display: "grid",
              gridTemplateColumns: "92px 1fr 34px",
              alignItems: "center",
              gap: 10,
            }}
          >
            <span className="cf-mono-sm">{label}</span>
            <div style={{ height: 4, background: "var(--ink-3)", borderRadius: 999, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${Number(value || 0)}%`, background: "var(--ember)" }} />
            </div>
            <span className="cf-mono-sm" style={{ color: "var(--paper-dim)", textAlign: "right" }}>
              {Number(value || 0)}
            </span>
          </div>
        ))}
      </div>

      <div className="cf-mono-sm" style={{ marginBottom: 10 }}>
        FUENTES
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {(item.sources || []).length ? (
          item.sources.map((source) => (
            <a
              key={source.url || source.title}
              href={source.url || "#"}
              target="_blank"
              rel="noreferrer"
              className="cf-card"
              style={{
                padding: 12,
                textDecoration: "none",
                color: "var(--paper-dim)",
                display: "block",
                borderRadius: "var(--r-2)",
              }}
            >
              <div style={{ color: "var(--paper)", marginBottom: 4 }}>{source.title || source.domain}</div>
              <div className="cf-caption">{source.domain || source.url}</div>
            </a>
          ))
        ) : (
          <div className="cf-caption">Idea evergreen sin fuentes externas.</div>
        )}
      </div>
    </aside>
  );
}

export default function RadarPage() {
  const router = useRouter();
  const { user, profile, loading: authLoading } = useAuth();
  const admin = isAdminUser(user, profile);
  const [filters, setFilters] = useState({
    scope: "global",
    agentId: DEFAULT_AGENT_ID,
    market: "mx",
    category: "all",
    window: "today",
    format: "all",
    limit: 3,
    queryLimit: 2,
  });
  const [query, setQuery] = useState("");
  const [run, setRun] = useState(null);
  const [selectedHash, setSelectedHash] = useState("");
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [savingHash, setSavingHash] = useState("");
  const [creatingHash, setCreatingHash] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (authLoading || !user || !admin || !RADAR_ENABLED) return;
    const controller = new AbortController();
    const loadLatest = async () => {
      setLoading(true);
      setError("");
      try {
        const payload = buildRadarParams(filters, false);
        const params = new URLSearchParams({
          scope: payload.scope,
          agentId: payload.agentId || "",
          market: payload.market,
          language: payload.language,
          category: payload.category,
          window: payload.window,
        });
        const res = await authedFetch(user, `${getApiBase()}/radar/latest?${params.toString()}`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || data.error || "No se pudo leer el radar.");
        setRun(data);
        setSelectedHash((current) => current || data.items?.[0]?.candidateHash || "");
      } catch (err) {
        if (err.name !== "AbortError") setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    loadLatest();
    return () => controller.abort();
  }, [
    authLoading,
    user,
    admin,
    filters,
  ]);

  const visibleItems = useMemo(() => {
    const text = query.trim().toLowerCase();
    return (run?.items || []).filter((item) => {
      const formatOk = filters.format === "all" || item.recommendedFormat === filters.format;
      if (!formatOk) return false;
      if (!text) return true;
      return [item.title, item.angle, item.summary, item.agentName]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text);
    });
  }, [run, filters.format, query]);

  const groups = useMemo(() => {
    const map = new Map();
    for (const item of visibleItems) {
      const id = item.agentId || "unknown";
      if (!map.has(id)) {
        map.set(id, {
          agentId: id,
          agentName: agentDisplayName(id, item.agentName, SYSTEM_AGENTS),
          items: [],
        });
      }
      map.get(id).items.push(item);
    }
    return Array.from(map.values());
  }, [visibleItems]);

  const selectedItem = useMemo(
    () => visibleItems.find((item) => item.candidateHash === selectedHash) || visibleItems[0],
    [visibleItems, selectedHash],
  );

  const stats = useMemo(() => {
    const agentCount = new Set(visibleItems.map((item) => item.agentId)).size;
    const highRisk = visibleItems.filter((item) => item.riskLevel === "high").length;
    const avgScore = visibleItems.length
      ? Math.round(visibleItems.reduce((sum, item) => sum + Number(item.editorialScore || 0), 0) / visibleItems.length)
      : 0;
    return { agentCount, highRisk, avgScore };
  }, [visibleItems]);

  const updateCandidate = (hash, patch) => {
    setRun((current) => {
      if (!current?.items) return current;
      return {
        ...current,
        items: current.items.map((item) => (
          item.candidateHash === hash ? { ...item, ...patch } : item
        )),
      };
    });
  };

  const runRadar = async (force) => {
    setRunning(true);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRadarParams(filters, force)),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo ejecutar el radar.");
      setRun(data);
      setSelectedHash(data.items?.[0]?.candidateHash || "");
      setNotice(data.cached ? "Radar cacheado cargado." : "Radar actualizado.");
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  const saveCandidate = async (item) => {
    setSavingHash(item.candidateHash);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/candidates/${item.candidateHash}/save`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo guardar la idea.");
      updateCandidate(item.candidateHash, { status: "saved" });
      setNotice("Idea guardada en biblioteca.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingHash("");
    }
  };

  const createProject = async (item) => {
    if (item.riskLevel === "high") return;
    setCreatingHash(item.candidateHash);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/candidates/${item.candidateHash}/create-project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.projectId) throw new Error(data.detail || data.error || "No se pudo crear el proyecto.");
      updateCandidate(item.candidateHash, { status: "project_created", projectId: data.projectId });
      router.push(`/dashboard/project/${data.projectId}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingHash("");
    }
  };

  if (!RADAR_ENABLED) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
        <Icon name="lock" size={30} style={{ margin: "0 auto 16px", color: "var(--paper-mute)" }} />
        <h1 className="cf-h2" style={{ margin: 0 }}>Radar apagado</h1>
      </div>
    );
  }

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
          RADAR
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
          <div>
            <h1 className="cf-h1" style={{ margin: 0 }}>
              Radar editorial
            </h1>
            <p className="cf-body" style={{ maxWidth: 680, margin: "12px 0 0" }}>
              Noticias virales, ideas por agente, fuentes, riesgo y creacion ordenada de proyectos.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="cf-btn cf-btn--secondary" onClick={() => runRadar(false)} disabled={running || loading} type="button">
              <Icon name="search" size={16} />
              {running ? "Buscando" : "Buscar"}
            </button>
            <button className="cf-btn cf-btn--primary" onClick={() => runRadar(true)} disabled={running} type="button">
              <Icon name="refresh" size={16} />
              Refrescar
            </button>
          </div>
        </div>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: "var(--s-5)" }}>
        {[
          ["Ideas", compactNumber(visibleItems.length), run?.cached ? "cache" : "actual"],
          ["Agentes", compactNumber(stats.agentCount), "cubiertos"],
          ["Score prom.", compactNumber(stats.avgScore), "editorial"],
          ["Alto riesgo", compactNumber(stats.highRisk), "bloqueados"],
        ].map(([label, value, sub]) => (
          <div className="cf-card" key={label} style={{ padding: "var(--s-4)" }}>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>{label}</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 34, fontWeight: 800, lineHeight: 1 }}>{value}</div>
            <div className="cf-caption" style={{ marginTop: 6 }}>{sub}</div>
          </div>
        ))}
      </section>

      <section className="cf-card cf-fade cf-fade--1" style={{ padding: "var(--s-5)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
          <div>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Scope</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {RADAR_SCOPE_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  className="cf-btn cf-btn--sm"
                  style={buttonStyle(filters.scope === option.id)}
                  onClick={() => setFilters((current) => ({ ...current, scope: option.id }))}
                  type="button"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Agente</div>
            <select
              className="cf-input"
              value={filters.agentId}
              disabled={filters.scope !== "agent"}
              onChange={(event) => setFilters((current) => ({ ...current, agentId: event.target.value }))}
            >
              {SYSTEM_AGENTS.map((agent) => (
                <option key={agent.agentId} value={agent.agentId}>{agent.name}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Categoria</div>
            <select
              className="cf-input"
              value={filters.category}
              onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}
            >
              {RADAR_CATEGORY_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Ventana</div>
            <select
              className="cf-input"
              value={filters.window}
              onChange={(event) => setFilters((current) => ({ ...current, window: event.target.value }))}
            >
              {RADAR_WINDOW_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Buscar</div>
            <input
              className="cf-input"
              value={query}
              placeholder="Tema, agente o fuente"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginTop: 16, flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {RADAR_FORMAT_OPTIONS.map((option) => (
              <button
                key={option.id}
                className="cf-btn cf-btn--sm"
                style={buttonStyle(filters.format === option.id)}
                onClick={() => setFilters((current) => ({ ...current, format: option.id }))}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="cf-caption">
            Ultimo refresh: {formatRadarDate(run?.generatedAt)}
          </div>
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

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))",
          gap: "var(--s-5)",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "var(--s-5)" }}>
          {loading && (
            <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
              <Icon name="refresh" size={24} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
              <div className="cf-body">Cargando radar.</div>
            </div>
          )}
          {!loading && groups.length === 0 && (
            <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
              <Icon name="search" size={28} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
              <h2 className="cf-h3" style={{ margin: 0 }}>Sin ideas en cache</h2>
            </div>
          )}
          {groups.map((group) => (
            <div key={group.agentId} style={{ display: "grid", gap: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <AgentMonogram agent={group.agentId} size={34} variant="compact" />
                <div>
                  <div className="cf-h4">{group.agentName}</div>
                  <div className="cf-caption">{group.items.length} idea(s)</div>
                </div>
              </div>
              {group.items.map((item) => (
                <CandidateCard
                  key={item.candidateHash}
                  item={item}
                  selected={selectedItem?.candidateHash === item.candidateHash}
                  saving={savingHash === item.candidateHash}
                  creating={creatingHash === item.candidateHash}
                  onSelect={() => setSelectedHash(item.candidateHash)}
                  onSave={() => saveCandidate(item)}
                  onCreate={() => createProject(item)}
                />
              ))}
            </div>
          ))}
        </div>
        <DetailPanel item={selectedItem} />
      </section>
    </div>
  );
}
