"use client";

import Link from "next/link";
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
  RADAR_INTENT_OPTIONS,
  RADAR_SCOPE_OPTIONS,
  RADAR_WINDOW_OPTIONS,
  agentDisplayName,
  compactNumber,
  formatRadarDate,
  formatRadarIntent,
  formatRadarSourceType,
  formatRecommendation,
  ideaStatusMeta,
  riskMeta,
} from "@/lib/radarUi";

const RADAR_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_RADAR_ENABLED !== "false";
const NEWS_AGENT_ID = "agent_noticias_virales";
const DEFAULT_AGENT_ID = "agent_podcast_general";

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
    intent: filters.scope === "news" ? "news" : filters.intent,
    window: filters.window,
    limit: Number(filters.limit || 3),
    queryLimit: Number(filters.queryLimit || 2),
    force,
  };
  if (filters.scope === "agent") payload.agentId = filters.agentId || DEFAULT_AGENT_ID;
  if (filters.scope === "news") payload.agentId = NEWS_AGENT_ID;
  return payload;
}

function estimateRadarCost(filters) {
  const queryLimit = Number(filters.queryLimit || 2);
  const knowledgeQueries = filters.scope === "news" ? 0 : Math.min(3, queryLimit);
  if (filters.scope === "global") {
    const agentLimit = 6;
    return {
      tavilyCredits: agentLimit,
      tavilyQueries: agentLimit,
      knowledgeQueries: agentLimit * Math.min(3, 1),
      embeddingQueries: agentLimit * Math.min(3, 1),
      label: "estimado local",
    };
  }
  return {
    tavilyCredits: queryLimit,
    tavilyQueries: queryLimit,
    knowledgeQueries,
    embeddingQueries: knowledgeQueries,
    label: "estimado local",
  };
}

function CostPill({ estimate, cached }) {
  const cost = estimate || {};
  return (
    <div className="cf-card" style={{ padding: "var(--s-4)", display: "grid", gap: 8 }}>
      <div className="cf-mono-sm">Costo estimado</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <span className="cf-badge cf-badge--neutral">
          Tavily {cached ? "0 ahora" : `${Number(cost.tavilyCredits || 0)} credit(s)`}
        </span>
        <span className="cf-badge cf-badge--neutral">
          Qdrant {Number(cost.knowledgeQueries || 0)} busq.
        </span>
        <span className="cf-badge cf-badge--neutral">
          Embeddings {Number(cost.embeddingQueries || 0)}
        </span>
      </div>
      <div className="cf-caption">
        {cached ? "Esta vista vino de cache; refrescar vuelve a consumir." : "Buscar usa cache si existe; refrescar fuerza consumo nuevo."}
      </div>
    </div>
  );
}

function PanelSection({ title, caption, badge, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section
      style={{
        border: "1px solid var(--rule-1)",
        borderRadius: "var(--r-3)",
        background: "var(--ink-1)",
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="cf-btn"
        style={{
          width: "100%",
          justifyContent: "space-between",
          border: 0,
          borderRadius: 0,
          background: "transparent",
          padding: "var(--s-4)",
          color: "var(--paper)",
        }}
      >
        <span style={{ display: "grid", gap: 4, textAlign: "left" }}>
          <span style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className="cf-h4">{title}</span>
            {badge && <span className="cf-badge cf-badge--creator">{badge}</span>}
          </span>
          {caption && <span className="cf-caption">{caption}</span>}
        </span>
        <Icon name={open ? "chevronDown" : "chevronRight"} size={18} />
      </button>
      {open && (
        <div style={{ padding: "0 var(--s-4) var(--s-4)" }}>
          {children}
        </div>
      )}
    </section>
  );
}

function formatShortDate(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
  } catch {
    return "";
  }
}

function buildPreparedProjectUrl(item) {
  const params = new URLSearchParams({
    agentId: item.agentId || "",
    topic: item.seoTitle || item.angle || item.title || "",
    from: "radar",
  });
  if (item.candidateHash) params.set("candidateHash", item.candidateHash);
  return `/dashboard/new?${params.toString()}`;
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
      <div className="cf-caption" style={{ textAlign: "right" }}>
        score editorial
      </div>
    </div>
  );
}

function CandidateCard({ item, selected, saving, creating, onSelect, onSave, onCreate }) {
  const risk = riskMeta(item.riskLevel);
  const status = ideaStatusMeta(item.status);
  const createDisabled = item.riskLevel === "high" || Boolean(item.projectId) || creating;
  const knowledgeSignals = item.knowledgeSignals || [];

  return (
    <article
      className="cf-card"
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      style={{
        padding: "var(--s-5)",
        borderColor: selected ? "var(--ember)" : "var(--rule-1)",
        cursor: "pointer",
        boxShadow: selected ? "var(--shadow-ember)" : "var(--shadow-1)",
        transition: "border-color var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out)",
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
            <span className="cf-badge cf-badge--neutral">
              {formatRadarIntent(item.intent || item.radarIntent)}
            </span>
            <span className="cf-badge cf-badge--neutral">
              {formatRadarSourceType(item.sourceType)}
            </span>
          </div>
          <h2 className="cf-h3" style={{ margin: "0 0 8px", lineHeight: 1.2 }}>
            {item.seoTitle || item.angle || item.title}
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
              onClick={(event) => event.stopPropagation()}
              style={{ textDecoration: "none", maxWidth: "100%" }}
            >
              {source.domain || source.title}
            </a>
          ))}
        </div>
      )}

      {knowledgeSignals.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: item.sources?.length ? 8 : 16 }}>
          {knowledgeSignals.slice(0, 3).map((signal) => (
            <span
              key={`${signal.title}-${signal.excerpt?.slice(0, 24)}`}
              className="cf-badge cf-badge--creator"
              title={signal.excerpt || signal.title}
              style={{ maxWidth: "100%" }}
            >
              <Icon name="bookOpen" size={12} />
              {signal.title}
            </span>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
        <button
          className="cf-btn cf-btn--ghost cf-btn--sm"
          onClick={(event) => {
            event.stopPropagation();
            onSelect();
          }}
          type="button"
        >
          <Icon name="eye" size={14} />
          {selected ? "Seleccionado" : "Detalle"}
        </button>
        <button
          className="cf-btn cf-btn--secondary cf-btn--sm"
          onClick={(event) => {
            event.stopPropagation();
            onSave();
          }}
          type="button"
          disabled={saving || item.status === "saved" || item.status === "project_created"}
        >
          <Icon name="bookOpen" size={14} />
          {saving ? "Guardando" : "Guardar"}
        </button>
        <button
          className="cf-btn cf-btn--primary cf-btn--sm"
          onClick={(event) => {
            event.stopPropagation();
            onCreate();
          }}
          type="button"
          disabled={createDisabled}
          title={item.riskLevel === "high" ? "Requiere revision editorial antes de crear proyecto" : ""}
        >
          <Icon name="plus" size={14} />
          {item.projectId ? "Proyecto creado" : creating ? "Preparando" : "Preparar proyecto"}
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
  const knowledgeSignals = item.knowledgeSignals || [];
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
        {item.seoTitle || item.title}
      </h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
        <span className={`cf-badge ${risk.badge}`}>{risk.label}</span>
        <span className="cf-badge cf-badge--neutral">{formatRecommendation(item.recommendedFormat)}</span>
        <span className="cf-badge cf-badge--neutral">{formatRadarSourceType(item.sourceType)}</span>
      </div>
      {item.seoKeywords?.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {item.seoKeywords.slice(0, 6).map((keyword) => (
            <span key={keyword} className="cf-badge cf-badge--creator">
              {keyword}
            </span>
          ))}
        </div>
      )}
      <p className="cf-body" style={{ marginTop: 0 }}>{item.whyNow || item.summary}</p>
      {item.sourceQuery && (
        <div className="cf-caption" style={{ margin: "-8px 0 16px" }}>
          Query radar: {item.sourceQuery}
        </div>
      )}
      {item.sourceType === "fallback" && (
        <div
          style={{
            border: "1px solid var(--rule-1)",
            borderLeft: "3px solid var(--warn)",
            borderRadius: "var(--r-2)",
            padding: "12px 14px",
            marginBottom: 18,
            color: "var(--paper-dim)",
            lineHeight: 1.45,
          }}
        >
          Fallback significa que esta idea vino del motor editorial seguro porque no hubo suficientes resultados utiles de web o base interna en esa corrida.
        </div>
      )}

      {knowledgeSignals.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: item.sources?.length ? 8 : 16 }}>
          {knowledgeSignals.slice(0, 3).map((signal) => (
            <span
              key={`${signal.title}-${signal.excerpt?.slice(0, 24)}`}
              className="cf-badge cf-badge--creator"
              title={signal.excerpt || signal.title}
              style={{ maxWidth: "100%" }}
            >
              <Icon name="bookOpen" size={12} />
              {signal.title}
            </span>
          ))}
        </div>
      )}
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

      {knowledgeSignals.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <div className="cf-mono-sm" style={{ marginBottom: 10 }}>
            BASE INTERNA
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {knowledgeSignals.slice(0, 4).map((signal) => (
              <div
                key={`${signal.title}-${signal.excerpt?.slice(0, 32)}`}
                className="cf-card"
                style={{
                  padding: 12,
                  borderRadius: "var(--r-2)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, color: "var(--paper)" }}>
                  <Icon name="bookOpen" size={14} />
                  <span>{signal.title}</span>
                </div>
                <div className="cf-caption" style={{ marginBottom: 8 }}>
                  {signal.category || "General"}
                </div>
                <p className="cf-body" style={{ margin: 0, fontSize: 14, lineHeight: 1.45 }}>
                  {signal.excerpt}
                </p>
              </div>
            ))}
          </div>
          {item.knowledgeQuery && (
            <div className="cf-caption" style={{ marginTop: 10 }}>
              Query interna: {item.knowledgeQuery}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

function TitleLabOptionCard({ item, saving, copied, onCopy, onSave, onPrepare }) {
  return (
    <article className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <span className="cf-badge cf-badge--creator">Viral {Number(item.viralScore || 0)}</span>
            <span className="cf-badge cf-badge--creator">Ret {Number(item.retentionScore || 0)}</span>
            <span className="cf-badge cf-badge--neutral">SEO {Number(item.seoScore || 0)}</span>
            <span className="cf-badge cf-badge--neutral">Hook {Number(item.clickbaitScore || 0)}</span>
            <span className="cf-badge cf-badge--neutral">Fit {Number(item.fitScore || 0)}</span>
            {item.retentionRank && (
              <span className="cf-badge cf-badge--neutral">#{item.retentionRank} retencion</span>
            )}
          </div>
          <h3 className="cf-h3" style={{ margin: "0 0 10px", lineHeight: 1.18 }}>
            {item.seoTitle || item.title}
          </h3>
          <p className="cf-body" style={{ margin: 0, lineHeight: 1.45 }}>
            {item.hook}
          </p>
          {item.retentionReason && (
            <p className="cf-caption" style={{ margin: "8px 0 0", lineHeight: 1.35 }}>
              {item.retentionReason}
            </p>
          )}
          {(item.evidence || item.inspiredBy?.title) && (
            <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
              {item.evidence && (
                <p className="cf-caption" style={{ margin: 0, color: "var(--ok)", lineHeight: 1.35 }}>
                  {item.evidence}
                </p>
              )}
              {item.inspiredBy?.title && (
                <a
                  href={item.inspiredBy.url || "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="cf-caption"
                  style={{ color: "var(--paper-mute)", textDecoration: "none", display: "flex", gap: 6, alignItems: "center" }}
                >
                  <Icon name="externalLink" size={12} />
                  {item.inspiredBy.channelTitle ? `${item.inspiredBy.channelTitle}: ` : ""}
                  {item.inspiredBy.title}
                </a>
              )}
            </div>
          )}
          {item.seoKeywords?.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              {item.seoKeywords.slice(0, 6).map((keyword) => (
                <span key={keyword} className="cf-badge cf-badge--neutral">
                  {keyword}
                </span>
              ))}
            </div>
          )}
        </div>
        <div style={{ minWidth: 68, textAlign: "right" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 34, lineHeight: 1, fontWeight: 800, color: "var(--ok)" }}>
            {Number(item.overallScore || 0)}
          </div>
          <div className="cf-caption">total</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16 }}>
        <button className="cf-btn cf-btn--ghost cf-btn--sm" type="button" onClick={onCopy}>
          <Icon name="copy" size={14} />
          {copied ? "Copiado" : "Copiar"}
        </button>
        <button className="cf-btn cf-btn--secondary cf-btn--sm" type="button" onClick={onSave} disabled={saving}>
          <Icon name="bookOpen" size={14} />
          {saving ? "Guardando" : "Guardar"}
        </button>
        <button className="cf-btn cf-btn--primary cf-btn--sm" type="button" onClick={onPrepare}>
          <Icon name="arrowRight" size={14} />
          Preparar
        </button>
      </div>
    </article>
  );
}

function ViralOpportunityCard({ item, saving, onSave, onPrepare }) {
  const risk = riskMeta(item.riskLevel);
  const evidence = item.evidence || [];
  const suggestedTitles = item.suggestedTitles || [];
  return (
    <article className="cf-card" style={{ padding: "var(--s-5)", borderRadius: "var(--r-3)" }}>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 18, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            <span className="cf-badge cf-badge--creator">Oportunidad {Number(item.opportunityScore || 0)}</span>
            <span className="cf-badge cf-badge--creator">Evidencia {Number(item.evidenceScore || 0)}</span>
            <span className="cf-badge cf-badge--neutral">Ret {Number(item.retentionScore || 0)}</span>
            <span className={`cf-badge ${risk.badge}`}>{risk.label}</span>
          </div>
          <h3 className="cf-h2" style={{ margin: "0 0 8px", lineHeight: 1.08 }}>
            {item.cluster || item.topic || item.title}
          </h3>
          {item.audienceTension && (
            <p className="cf-body" style={{ margin: "0 0 10px", color: "var(--paper)", lineHeight: 1.45 }}>
              {item.audienceTension}
            </p>
          )}
          <p className="cf-caption" style={{ margin: 0, lineHeight: 1.45 }}>
            {item.whyItCanWork || item.corePattern}
          </p>
        </div>
        <div style={{ textAlign: "right", minWidth: 86 }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 42, lineHeight: 1, fontWeight: 800, color: "var(--ok)" }}>
            {Number(item.opportunityScore || 0)}
          </div>
          <div className="cf-caption">score</div>
        </div>
      </div>

      {evidence.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="cf-mono-sm" style={{ marginBottom: 8 }}>EVIDENCIA</div>
          <div style={{ display: "grid", gap: 8 }}>
            {evidence.slice(0, 3).map((source) => (
              <a
                key={source.url || source.title}
                href={source.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="cf-card"
                style={{ padding: 12, borderRadius: "var(--r-2)", textDecoration: "none", display: "grid", gap: 6 }}
              >
                <div style={{ color: "var(--paper)", fontWeight: 800, lineHeight: 1.25 }}>
                  {source.channelTitle ? `${source.channelTitle}: ` : ""}
                  {source.title}
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {source.views > 0 && <span className="cf-badge cf-badge--neutral">{compactNumber(source.views)} views</span>}
                  {source.viewsPerDay > 0 && <span className="cf-badge cf-badge--creator">{compactNumber(source.viewsPerDay)} / dia</span>}
                  {source.publishedAt && <span className="cf-badge cf-badge--neutral">{formatShortDate(source.publishedAt)}</span>}
                </div>
                {source.whyRelevant && <div className="cf-caption" style={{ color: "var(--ok)" }}>{source.whyRelevant}</div>}
              </a>
            ))}
          </div>
        </div>
      )}

      {suggestedTitles.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="cf-mono-sm" style={{ marginBottom: 8 }}>TITULOS PROPUESTOS</div>
          <div style={{ display: "grid", gap: 8 }}>
            {suggestedTitles.slice(0, 4).map((title, index) => (
              <div key={title} className="cf-card" style={{ padding: 12, borderRadius: "var(--r-2)", display: "flex", gap: 10 }}>
                <span className="cf-mono-sm" style={{ color: "var(--ember)" }}>{String(index + 1).padStart(2, "0")}</span>
                <span style={{ color: "var(--paper)", fontWeight: 750, lineHeight: 1.25 }}>{title}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
        <button className="cf-btn cf-btn--secondary cf-btn--sm" type="button" onClick={onSave} disabled={saving}>
          <Icon name="bookOpen" size={14} />
          {saving ? "Guardando" : "Guardar en temas"}
        </button>
        <button className="cf-btn cf-btn--primary cf-btn--sm" type="button" onClick={onPrepare}>
          <Icon name="arrowRight" size={14} />
          Preparar proyecto
        </button>
      </div>
    </article>
  );
}

export default function RadarPage() {
  const router = useRouter();
  const { user, profile, loading: authLoading } = useAuth();
  const admin = isAdminUser(user, profile);
  const [filters, setFilters] = useState({
    scope: "agent",
    agentId: DEFAULT_AGENT_ID,
    intent: "viral_topics",
    market: "mx",
    category: "all",
    window: "today",
    format: "all",
    limit: 5,
    queryLimit: 2,
  });
  const [titleLabAgentId, setTitleLabAgentId] = useState(DEFAULT_AGENT_ID);
  const [titleLabTopic, setTitleLabTopic] = useState("");
  const [titleLabResult, setTitleLabResult] = useState(null);
  const [titleLabLoading, setTitleLabLoading] = useState(false);
  const [titleLabError, setTitleLabError] = useState("");
  const [titleLabNotice, setTitleLabNotice] = useState("");
  const [titleLabSavingId, setTitleLabSavingId] = useState("");
  const [titleLabCopiedId, setTitleLabCopiedId] = useState("");
  const [titleLabUseTrends, setTitleLabUseTrends] = useState(false);
  const [titleLabUseCompetitors, setTitleLabUseCompetitors] = useState(false);
  const [viralTopic, setViralTopic] = useState("");
  const [viralUseTrends, setViralUseTrends] = useState(true);
  const [viralUseCompetitors, setViralUseCompetitors] = useState(true);
  const [viralUseKnowledge, setViralUseKnowledge] = useState(true);
  const [viralResult, setViralResult] = useState(null);
  const [viralLoading, setViralLoading] = useState(false);
  const [viralError, setViralError] = useState("");
  const [viralNotice, setViralNotice] = useState("");
  const [viralSavingId, setViralSavingId] = useState("");
  const [competitors, setCompetitors] = useState([]);
  const [competitorsLoading, setCompetitorsLoading] = useState(false);
  const [competitorQuery, setCompetitorQuery] = useState("");
  const [competitorResults, setCompetitorResults] = useState([]);
  const [competitorError, setCompetitorError] = useState("");
  const [competitorSavingId, setCompetitorSavingId] = useState("");
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
          intent: payload.intent || "viral_topics",
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

  useEffect(() => {
    if (authLoading || !user || !admin || !RADAR_ENABLED) return;
    const controller = new AbortController();
    const loadCompetitors = async () => {
      setCompetitorsLoading(true);
      setCompetitorError("");
      try {
        const params = new URLSearchParams({ agentId: titleLabAgentId });
        const res = await authedFetch(user, `${getApiBase()}/radar/competitors?${params.toString()}`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron leer competidores.");
        setCompetitors(data.items || []);
      } catch (err) {
        if (err.name !== "AbortError") setCompetitorError(err.message);
      } finally {
        setCompetitorsLoading(false);
      }
    };
    loadCompetitors();
    return () => controller.abort();
  }, [authLoading, user, admin, titleLabAgentId]);

  const visibleItems = useMemo(() => {
    const text = query.trim().toLowerCase();
    return (run?.items || []).filter((item) => {
      const formatOk = filters.format === "all" || item.recommendedFormat === filters.format;
      if (!formatOk) return false;
      if (!text) return true;
      return [
        item.title,
        item.seoTitle,
        ...(item.seoKeywords || []),
        item.angle,
        item.summary,
        item.agentName,
        ...(item.knowledgeSignals || []).flatMap((signal) => [signal.title, signal.category, signal.excerpt]),
      ]
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
    const withKnowledge = visibleItems.filter((item) => (item.knowledgeSignals || []).length > 0).length;
    const avgScore = visibleItems.length
      ? Math.round(visibleItems.reduce((sum, item) => sum + Number(item.editorialScore || 0), 0) / visibleItems.length)
      : 0;
    return { agentCount, highRisk, withKnowledge, avgScore };
  }, [visibleItems]);

  const currentCostEstimate = useMemo(
    () => run?.costEstimate || estimateRadarCost(filters),
    [run?.costEstimate, filters],
  );

  const runViralOpportunities = async () => {
    setViralLoading(true);
    setViralError("");
    setViralNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/viral-opportunities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: titleLabAgentId,
          seedTopic: viralTopic,
          useTrends: viralUseTrends,
          useCompetitors: viralUseCompetitors,
          useKnowledge: viralUseKnowledge,
          limit: 6,
          trendQueryLimit: 2,
          perChannelLimit: 8,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo ejecutar el Radar Viral v3.");
      setViralResult(data);
      setViralNotice(`Radar Viral listo: ${data.items?.length || 0} oportunidad(es) detectada(s).`);
    } catch (err) {
      setViralError(err.message);
    } finally {
      setViralLoading(false);
    }
  };

  const saveViralOpportunity = async (item) => {
    setViralSavingId(item.opportunityId || item.candidateHash);
    setViralError("");
    setViralNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/viral-opportunities/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: titleLabAgentId,
          seedTopic: viralResult?.seedTopic || viralTopic,
          opportunity: item,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo guardar la oportunidad.");
      setViralNotice("Oportunidad guardada en Temas.");
    } catch (err) {
      setViralError(err.message);
    } finally {
      setViralSavingId("");
    }
  };

  const prepareViralOpportunity = (item) => {
    const title = item.suggestedTitles?.[0] || item.seoTitle || item.title;
    router.push(buildPreparedProjectUrl({
      ...item,
      agentId: titleLabAgentId,
      title,
      seoTitle: title,
      angle: item.corePattern || item.title,
    }));
  };

  const runTitleLab = async () => {
    setTitleLabLoading(true);
    setTitleLabError("");
    setTitleLabNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/title-lab`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: titleLabAgentId,
          seedTopic: titleLabTopic,
          seedLimit: 10,
          adjacentLimit: 5,
          useTrends: titleLabUseTrends,
          useCompetitors: titleLabUseCompetitors,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo generar el laboratorio.");
      setTitleLabResult(data);
      setTitleLabNotice(titleLabTopic.trim() ? "Titulos generados para tu idea." : "Titulos sugeridos para el nicho.");
    } catch (err) {
      setTitleLabError(err.message);
    } finally {
      setTitleLabLoading(false);
    }
  };

  const discoverCompetitors = async () => {
    setCompetitorsLoading(true);
    setCompetitorError("");
    setCompetitorResults([]);
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/competitors/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: titleLabAgentId,
          query: competitorQuery,
          seedTopic: titleLabTopic,
          limit: 5,
          includeVideoSignals: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron descubrir competidores.");
      setCompetitorResults(data.items || []);
      setTitleLabNotice(
        `Busqueda YouTube lista: ${data.items?.length || 0} canal(es), ${Number(data.costEstimate?.youtubeQuotaUnits || 0)} unidades aprox.`,
      );
    } catch (err) {
      setCompetitorError(err.message);
    } finally {
      setCompetitorsLoading(false);
    }
  };

  const saveCompetitor = async (item) => {
    setCompetitorSavingId(item.channelId);
    setCompetitorError("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/competitors/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...item,
          agentId: titleLabAgentId,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo guardar el competidor.");
      setCompetitors((current) => {
        const next = data.item || item;
        const id = next.channelId || item.channelId;
        const filtered = current.filter((entry) => entry.channelId !== id);
        return [next, ...filtered];
      });
      setTitleLabNotice("Competidor guardado para este agente.");
    } catch (err) {
      setCompetitorError(err.message);
    } finally {
      setCompetitorSavingId("");
    }
  };

  const copyTitleLabOption = async (item) => {
    try {
      await navigator.clipboard.writeText(item.seoTitle || item.title);
      setTitleLabCopiedId(item.optionId);
      window.setTimeout(() => setTitleLabCopiedId(""), 1600);
    } catch {
      setTitleLabError("No se pudo copiar el titulo.");
    }
  };

  const saveTitleLabOption = async (item) => {
    setTitleLabSavingId(item.optionId);
    setTitleLabError("");
    setTitleLabNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/radar/title-lab/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...item,
          agentId: titleLabAgentId,
          seedTopic: titleLabResult?.seedTopic || titleLabTopic,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo guardar el titulo.");
      setTitleLabNotice("Titulo guardado en Biblioteca por agente.");
    } catch (err) {
      setTitleLabError(err.message);
    } finally {
      setTitleLabSavingId("");
    }
  };

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
      setNotice("Idea guardada en Biblioteca por agente.");
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
      router.push(buildPreparedProjectUrl(item));
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
          RADAR V2
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
          <div>
            <h1 className="cf-h1" style={{ margin: 0 }}>
              Radar editorial
            </h1>
            <p className="cf-body" style={{ maxWidth: 680, margin: "12px 0 0" }}>
              Temas virales, dolores de audiencia, hooks, noticias y senales internas de la biblioteca Qdrant.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link className="cf-btn cf-btn--ghost" href="/dashboard/library" style={{ textDecoration: "none" }}>
              <Icon name="bookOpen" size={16} />
              Biblioteca
            </Link>
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

      <section className="cf-card cf-fade cf-fade--1" style={{ padding: "var(--s-5)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 16 }}>
          <div>
            <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 8 }}>
              RADAR VIRAL V3
            </div>
            <h2 className="cf-h2" style={{ margin: 0 }}>Oportunidades basadas en evidencia</h2>
            <p className="cf-body" style={{ margin: "10px 0 0", maxWidth: 800 }}>
              Primero detecta patrones que ya muestran demanda en competidores, tendencias y Qdrant; despues propone titulos para producir.
            </p>
          </div>
          <button className="cf-btn cf-btn--primary" onClick={runViralOpportunities} disabled={viralLoading} type="button">
            <Icon name="trendingUp" size={16} />
            {viralLoading ? "Analizando" : "Encontrar oportunidades"}
          </button>
        </div>

        <PanelSection
          title="Fuentes y territorio"
          caption="Usa competidores guardados como senal principal. Tavily y Qdrant ayudan con contexto y profundidad."
          defaultOpen
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 240px), 1fr))", gap: 12 }}>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Nicho / agente</div>
              <select
                className="cf-input"
                value={titleLabAgentId}
                onChange={(event) => setTitleLabAgentId(event.target.value)}
              >
                {SYSTEM_AGENTS.map((agent) => (
                  <option key={agent.agentId} value={agent.agentId}>{agent.name}</option>
                ))}
              </select>
            </label>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Territorio opcional</div>
              <input
                className="cf-input"
                value={viralTopic}
                placeholder="Ej: amor propio, contacto cero, ghosting"
                onChange={(event) => setViralTopic(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") runViralOpportunities();
                }}
              />
            </label>
            <div>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Competidores guardados</div>
              <div className="cf-card" style={{ padding: 12, borderRadius: "var(--r-2)" }}>
                <div style={{ fontFamily: "var(--font-display)", fontSize: 30, lineHeight: 1, fontWeight: 800 }}>
                  {compactNumber(competitors.length)}
                </div>
                <div className="cf-caption">canal(es) para este agente</div>
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))", gap: 12, marginTop: 14 }}>
            {[
              ["Competidores YouTube", "La senal mas importante: videos reales, views y views/dia.", viralUseCompetitors, setViralUseCompetitors],
              ["Tendencias Tavily", "Contexto web actual para detectar lenguaje y demanda.", viralUseTrends, setViralUseTrends],
              ["Qdrant libros", "Profundidad conceptual para mejorar el angulo, no para decidir viralidad.", viralUseKnowledge, setViralUseKnowledge],
            ].map(([label, caption, checked, setter]) => (
              <label key={label} className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)", display: "flex", gap: 12, alignItems: "flex-start" }}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => setter(event.target.checked)}
                  style={{ marginTop: 5 }}
                />
                <span>
                  <span className="cf-mono-sm" style={{ display: "block", color: "var(--paper)" }}>{label}</span>
                  <span className="cf-caption">{caption}</span>
                </span>
              </label>
            ))}
          </div>
        </PanelSection>

        {(viralError || viralNotice) && (
          <div
            className="cf-card"
            style={{
              padding: "var(--s-4)",
              marginTop: 14,
              borderColor: viralError ? "var(--bad)" : "var(--ok)",
              color: viralError ? "var(--bad)" : "var(--ok)",
            }}
          >
            {viralError || viralNotice}
          </div>
        )}

        {viralResult?.items?.length > 0 && (
          <div style={{ display: "grid", gap: 14, marginTop: 14 }}>
            {viralResult.warnings?.length > 0 && (
              <div className="cf-card" style={{ padding: "var(--s-4)", borderColor: "var(--warn)", color: "var(--warn)" }}>
                {viralResult.warnings.join(" ")}
              </div>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
              {[
                ["Oportunidades", viralResult.summary?.opportunities || viralResult.items.length],
                ["Senales", viralResult.summary?.signalsAnalyzed || 0],
                ["Top score", viralResult.summary?.topScore || 0],
                ["Views/dia", viralResult.summary?.topViewsPerDay || 0],
              ].map(([label, value]) => (
                <div key={label} className="cf-card" style={{ padding: 12, borderRadius: "var(--r-2)" }}>
                  <div className="cf-mono-sm" style={{ marginBottom: 8 }}>{label}</div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: 30, lineHeight: 1, fontWeight: 800 }}>
                    {compactNumber(value)}
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))", gap: 14 }}>
              {viralResult.items.map((item) => (
                <ViralOpportunityCard
                  key={item.opportunityId || item.candidateHash}
                  item={item}
                  saving={viralSavingId === (item.opportunityId || item.candidateHash)}
                  onSave={() => saveViralOpportunity(item)}
                  onPrepare={() => prepareViralOpportunity(item)}
                />
              ))}
            </div>
            <div className="cf-caption">
              Costo: Tavily {Number(viralResult.costEstimate?.tavilyCredits || 0)} credito(s). YouTube {Number(viralResult.costEstimate?.youtubeQuotaUnits || 0)} unidad(es). Qdrant {Number(viralResult.costEstimate?.knowledgeQueries || 0)} busq. No crea proyectos ni consume creditos de produccion.
            </div>
          </div>
        )}
      </section>

      <section className="cf-card cf-fade cf-fade--1" style={{ padding: "var(--s-5)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 16 }}>
          <div>
            <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 8 }}>
              LABORATORIO DE TITULOS
            </div>
            <h2 className="cf-h2" style={{ margin: 0 }}>Convierte una idea en titulos virales</h2>
            <p className="cf-body" style={{ margin: "10px 0 0", maxWidth: 760 }}>
              Escribe una semilla como contacto cero o deja el campo vacio para recibir ideas independientes del nicho.
            </p>
          </div>
          <button className="cf-btn cf-btn--primary" onClick={runTitleLab} disabled={titleLabLoading} type="button">
            <Icon name="sparkles" size={16} />
            {titleLabLoading ? "Generando" : "Generar titulos"}
          </button>
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <PanelSection
            title="1. Idea y fuentes"
            caption="Elige el agente, escribe una semilla opcional y decide que señales usar."
            defaultOpen
          >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 12 }}>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Nicho / agente</div>
            <select
              className="cf-input"
              value={titleLabAgentId}
              onChange={(event) => setTitleLabAgentId(event.target.value)}
            >
              {SYSTEM_AGENTS.map((agent) => (
                <option key={agent.agentId} value={agent.agentId}>{agent.name}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Idea semilla opcional</div>
            <input
              className="cf-input"
              value={titleLabTopic}
              placeholder="Ej: contacto cero, ghosting, apego ansioso"
              onChange={(event) => setTitleLabTopic(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") runTitleLab();
              }}
            />
          </label>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 12, marginTop: 14 }}>
          <label className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)", display: "flex", gap: 12, alignItems: "flex-start" }}>
            <input
              type="checkbox"
              checked={titleLabUseTrends}
              onChange={(event) => setTitleLabUseTrends(event.target.checked)}
              style={{ marginTop: 5 }}
            />
            <span>
              <span className="cf-mono-sm" style={{ display: "block", color: "var(--paper)" }}>Tendencias Tavily</span>
              <span className="cf-caption">Agrega senales web actuales. Normalmente 1 credito Tavily.</span>
            </span>
          </label>
          <label className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)", display: "flex", gap: 12, alignItems: "flex-start" }}>
            <input
              type="checkbox"
              checked={titleLabUseCompetitors}
              onChange={(event) => setTitleLabUseCompetitors(event.target.checked)}
              style={{ marginTop: 5 }}
            />
            <span>
              <span className="cf-mono-sm" style={{ display: "block", color: "var(--paper)" }}>Competidores YouTube</span>
              <span className="cf-caption">Usa canales guardados por agente. Mucho mas barato que descubrir de cero.</span>
            </span>
          </label>
        </div>
          </PanelSection>

          <PanelSection
            title="2. Competidores curados"
            caption={`${competitors.length} guardado(s). Descubrir usa canales + videos: aprox. 202 unidades por busqueda.`}
            badge={competitorResults.length ? `${competitorResults.length} sugeridos` : ""}
            defaultOpen={competitorResults.length > 0 || competitors.length === 0}
          >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div>
              <div className="cf-mono-sm" style={{ marginBottom: 6 }}>Competidores curados</div>
              <div className="cf-caption">
                {competitors.length} guardado(s). Descubrir usa canales + videos: aprox. 202 unidades por busqueda.
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <input
                className="cf-input"
                value={competitorQuery}
                placeholder="Ej: contacto cero relaciones podcast"
                onChange={(event) => setCompetitorQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") discoverCompetitors();
                }}
                style={{ minWidth: 280 }}
              />
              <button className="cf-btn cf-btn--secondary cf-btn--sm" type="button" onClick={discoverCompetitors} disabled={competitorsLoading}>
                <Icon name="search" size={14} />
                {competitorsLoading ? "Buscando" : "Descubrir"}
              </button>
            </div>
          </div>

          {competitors.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              {competitors.slice(0, 8).map((item) => (
                <a
                  key={item.channelId}
                  className="cf-badge cf-badge--neutral"
                  href={item.url || "#"}
                  target="_blank"
                  rel="noreferrer"
                  style={{ textDecoration: "none" }}
                >
                  <Icon name="externalLink" size={12} />
                  {item.title || item.channelId}
                </a>
              ))}
            </div>
          )}

          {(competitorError || competitorResults.length > 0) && (
            <div style={{ marginTop: 12 }}>
              {competitorError && (
                <div className="cf-caption" style={{ color: "var(--bad)", marginBottom: 10 }}>
                  {competitorError}
                </div>
              )}
              {competitorResults.length > 0 && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 10 }}>
                  {competitorResults.map((item) => {
                    const alreadySaved = competitors.some((entry) => entry.channelId === item.channelId);
                    const foundByVideo = item.foundByVideo || {};
                    const publishedAt = formatShortDate(foundByVideo.publishedAt || item.publishedAt);
                    return (
                      <div key={item.channelId} className="cf-card" style={{ padding: 12, borderRadius: "var(--r-2)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ color: "var(--paper)", fontWeight: 700, lineHeight: 1.25 }}>{item.title}</div>
                            <p className="cf-caption" style={{ margin: "6px 0 0", lineHeight: 1.35 }}>
                              {item.description || item.channelId}
                            </p>
                            {foundByVideo.title && (
                              <div className="cf-card" style={{ padding: 10, borderRadius: "var(--r-2)", marginTop: 10 }}>
                                <a
                                  href={foundByVideo.url || "#"}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="cf-caption"
                                  style={{ color: "var(--paper)", textDecoration: "none", display: "flex", gap: 6, alignItems: "center" }}
                                >
                                  <Icon name="play" size={12} />
                                  {foundByVideo.title}
                                </a>
                                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                                  <span className="cf-badge cf-badge--neutral">{compactNumber(foundByVideo.views || item.views)} views</span>
                                  <span className="cf-badge cf-badge--creator">{compactNumber(foundByVideo.viewsPerDay || item.viewsPerDay)} / dia</span>
                                  {publishedAt && <span className="cf-badge cf-badge--neutral">{publishedAt}</span>}
                                </div>
                              </div>
                            )}
                            {item.whyRelevant && (
                              <p className="cf-caption" style={{ margin: "8px 0 0", color: "var(--ok)", lineHeight: 1.35 }}>
                                {item.whyRelevant}
                              </p>
                            )}
                          </div>
                          <button
                            className="cf-btn cf-btn--ghost cf-btn--sm"
                            type="button"
                            onClick={() => saveCompetitor(item)}
                            disabled={alreadySaved || competitorSavingId === item.channelId}
                          >
                            <Icon name={alreadySaved ? "check" : "plus"} size={14} />
                            {alreadySaved ? "Guardado" : "Guardar"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
          </PanelSection>
        </div>

        {(titleLabError || titleLabNotice) && (
          <div
            className="cf-card"
            style={{
              padding: "var(--s-4)",
              marginTop: 14,
              borderColor: titleLabError ? "var(--bad)" : "var(--ok)",
              color: titleLabError ? "var(--bad)" : "var(--ok)",
            }}
          >
            {titleLabError || titleLabNotice}
          </div>
        )}

        {titleLabResult?.groups?.length > 0 && (
          <PanelSection
            title="3. Resultados"
            caption={titleLabResult.generationMode === "llm_v2" ? "Sintesis generada con señales del agente, fuentes y competidores." : "Fallback semantico local, sin llamada LLM."}
            badge={titleLabResult.generationMode === "llm_v2" ? "v2 inteligente" : "fallback"}
            defaultOpen
          >
          <div style={{ display: "grid", gap: "var(--s-5)" }}>
            {titleLabResult.warnings?.length > 0 && (
              <div className="cf-card" style={{ padding: "var(--s-4)", borderColor: "var(--warn)", color: "var(--warn)" }}>
                {titleLabResult.warnings.join(" ")}
              </div>
            )}
            {titleLabResult.topicDiagnosis && Object.keys(titleLabResult.topicDiagnosis).length > 0 && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))",
                  gap: 10,
                }}
              >
                {[
                  ["Tension", titleLabResult.topicDiagnosis.coreTension],
                  ["Audiencia", titleLabResult.topicDiagnosis.audienceState],
                  ["Evitar", titleLabResult.topicDiagnosis.avoid],
                ].filter(([, value]) => value).map(([label, value]) => (
                  <div key={label} style={{ border: "1px solid var(--rule-1)", borderRadius: "var(--r-2)", padding: 12 }}>
                    <div className="cf-mono-sm" style={{ marginBottom: 6 }}>{label}</div>
                    <div className="cf-caption" style={{ lineHeight: 1.4 }}>{value}</div>
                  </div>
                ))}
              </div>
            )}
            {titleLabResult.retentionRanking?.length > 0 && (
              <PanelSection
                title="Ranking por retencion probable"
                caption="Prioriza los titulos con mas tension narrativa, claridad y promesa de quedarse viendo."
                badge={`Top ${titleLabResult.retentionRanking.length}`}
                defaultOpen
              >
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 10 }}>
                  {titleLabResult.retentionRanking.slice(0, 6).map((ranked, index) => {
                    const fullItem = (titleLabResult.items || []).find((entry) => entry.optionId === ranked.optionId) || ranked;
                    return (
                      <div key={ranked.optionId} className="cf-card" style={{ padding: 12, borderRadius: "var(--r-2)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                          <div style={{ minWidth: 0 }}>
                            <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 6 }}>
                              #{index + 1} · Retencion {Number(ranked.retentionScore || 0)}
                            </div>
                            <div style={{ color: "var(--paper)", fontWeight: 800, lineHeight: 1.25 }}>
                              {ranked.seoTitle || ranked.title}
                            </div>
                            <p className="cf-caption" style={{ margin: "8px 0 0", lineHeight: 1.35 }}>
                              {ranked.retentionReason}
                            </p>
                          </div>
                          <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                            <button className="cf-btn cf-btn--ghost cf-btn--sm" type="button" onClick={() => copyTitleLabOption(fullItem)}>
                              <Icon name="copy" size={13} />
                            </button>
                            <button className="cf-btn cf-btn--primary cf-btn--sm" type="button" onClick={() => router.push(buildPreparedProjectUrl({ ...fullItem, agentId: titleLabAgentId }))}>
                              <Icon name="arrowRight" size={13} />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </PanelSection>
            )}
            {titleLabResult.groups.map((group) => (
              <PanelSection
                key={group.id}
                title={group.label}
                caption={`${group.items.length} opcion(es)`}
                badge={group.id === "ai" ? "recomendado" : group.id === "adjacent" ? "extra" : ""}
                defaultOpen={group.id === "ai" || group.id === "competitor"}
              >
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 12 }}>
                  {group.items.map((item) => (
                    <TitleLabOptionCard
                      key={item.optionId}
                      item={item}
                      saving={titleLabSavingId === item.optionId}
                      copied={titleLabCopiedId === item.optionId}
                      onCopy={() => copyTitleLabOption(item)}
                      onSave={() => saveTitleLabOption(item)}
                      onPrepare={() => router.push(buildPreparedProjectUrl({ ...item, agentId: titleLabAgentId }))}
                    />
                  ))}
                </div>
              </PanelSection>
            ))}
            <div className="cf-caption">
              Costo: Tavily {Number(titleLabResult.costEstimate?.tavilyCredits || 0)} credito(s). YouTube {Number(titleLabResult.costEstimate?.youtubeQuotaUnits || 0)} unidad(es). Qdrant {Number(titleLabResult.costEstimate?.knowledgeQueries || 0)} busq. Embeddings {Number(titleLabResult.costEstimate?.embeddingQueries || 0)}.
              {Number(titleLabResult.costEstimate?.llmCalls || 0) > 0 && ` LLM ${Number(titleLabResult.costEstimate?.llmCalls || 0)} llamada(s).`}
            </div>
          </div>
          </PanelSection>
        )}
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: "var(--s-5)" }}>
        {[
          ["Ideas", compactNumber(visibleItems.length), run?.cached ? "cache" : "actual"],
          ["Agentes", compactNumber(stats.agentCount), "cubiertos"],
          ["Score editorial", compactNumber(stats.avgScore), "promedio"],
          ["Base interna", compactNumber(stats.withKnowledge), "con Qdrant"],
          ["Alto riesgo", compactNumber(stats.highRisk), "bloqueados"],
        ].map(([label, value, sub]) => (
          <div className="cf-card" key={label} style={{ padding: "var(--s-4)" }}>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>{label}</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 34, fontWeight: 800, lineHeight: 1 }}>{value}</div>
            <div className="cf-caption" style={{ marginTop: 6 }}>{sub}</div>
          </div>
        ))}
      </section>

      <div style={{ marginBottom: "var(--s-5)" }}>
        <CostPill estimate={currentCostEstimate} cached={run?.cached} />
      </div>

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
                  onClick={() => setFilters((current) => ({
                    ...current,
                    scope: option.id,
                    agentId: option.id === "news" ? NEWS_AGENT_ID : current.agentId === NEWS_AGENT_ID ? DEFAULT_AGENT_ID : current.agentId,
                    intent: option.id === "news" ? "news" : current.intent === "news" ? "viral_topics" : current.intent,
                  }))}
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
          <div>
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Intencion</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {RADAR_INTENT_OPTIONS.map((option) => {
                const selectedIntent = filters.scope === "news" ? "news" : filters.intent;
                const disabled = filters.scope === "news" ? option.id !== "news" : option.id === "news";
                return (
                  <button
                    key={option.id}
                    className="cf-btn cf-btn--sm"
                    style={{
                      ...buttonStyle(selectedIntent === option.id),
                      opacity: disabled ? 0.45 : 1,
                    }}
                    onClick={() => {
                      if (disabled) return;
                      setFilters((current) => ({ ...current, intent: option.id }));
                    }}
                    type="button"
                    disabled={disabled}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>
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
            <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Ideas</div>
            <select
              className="cf-input"
              value={filters.limit}
              onChange={(event) => setFilters((current) => ({ ...current, limit: Number(event.target.value) }))}
            >
              {[3, 5, 8, 12].map((value) => (
                <option key={value} value={value}>{value} ideas</option>
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
