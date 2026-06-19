"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { collection, limit, onSnapshot, query, where } from "firebase/firestore";
import Icon from "@/components/Icon";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import { SYSTEM_AGENTS } from "@/lib/agents";
import {
  EDITORIAL_CALENDAR_ITEMS,
  EDITORIAL_SIGNAL,
  EDITORIAL_STATUS,
  buildCreateContentHref,
  derivativeOptionsForItem,
} from "@/lib/editorialCalendar";

const STORAGE_KEY = "content-factory-editorial-agenda-v1";

const STATUS_META = {
  pending: { label: "Pendiente", badge: "cf-badge--neutral", color: "var(--paper-mute)" },
  creating: { label: "En creación", badge: "cf-badge--warn", color: "var(--warn)" },
  created: { label: "Creado", badge: "cf-badge--starter", color: "var(--info)" },
  scheduled: { label: "Programado", badge: "cf-badge--creator", color: "var(--ember)" },
  published: { label: "Publicado", badge: "cf-badge--ok", color: "var(--ok)" },
  measured: { label: "Medido", badge: "cf-badge--ok", color: "var(--ok)" },
};

const SIGNAL_META = {
  unknown: { label: "Sin medir", badge: "cf-badge--neutral" },
  normal: { label: "Normal", badge: "cf-badge--neutral" },
  promising: { label: "Prometedor", badge: "cf-badge--starter" },
  winner: { label: "Ganador", badge: "cf-badge--ok" },
  avoid: { label: "No repetir", badge: "cf-badge--bad" },
};

const TYPE_FILTERS = [
  { id: "all", label: "Todo" },
  { id: "long", label: "Largos" },
  { id: "short", label: "Shorts" },
];

const STATUS_FILTERS = [
  { id: "all", label: "Todos" },
  { id: "pending", label: "Pendientes" },
  { id: "creating", label: "En creacion" },
  { id: "created", label: "Creados" },
  { id: "scheduled", label: "Programados" },
  { id: "published", label: "Publicados" },
  { id: "measured", label: "Medidos" },
  { id: "winner", label: "Ganadores" },
];

const WORK_FILTERS = [
  { id: "all", label: "Todo" },
  { id: "catchup", label: "Atrasados" },
  { id: "daily", label: "Plan diario" },
  { id: "todo", label: "Por crear" },
  { id: "ready", label: "Listos para publicar" },
];

const LIVE_PROJECT_STATUSES = new Set([
  "draft",
  "researching",
  "scripting",
  "prompting",
  "producing",
  "imaging",
  "voicing",
  "assembling",
  "rendering",
  "subtitling",
  "publishing",
]);

const DONE_STATUSES = new Set(["published", "measured"]);
const READY_STATUSES = new Set(["created", "scheduled"]);

const AGENT_ALIASES = {
  "agent_podcast_general_v2_largo": new Set([
    "agent_podcast_general",
    "agent_podcast_general_v2",
    "agent_podcast_general_v2_largo",
  ]),
  agent_misterios_v2: new Set(["agent_misterios", "agent_misterios_v2"]),
};

const AGENT_NAMES = SYSTEM_AGENTS.reduce((acc, agent) => {
  acc[agent.agentId] = agent.name;
  return acc;
}, {});

function toDate(date) {
  return new Date(`${date}T12:00:00`);
}

function todayIso() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 10);
}

function formatMonthLabel(date) {
  return new Intl.DateTimeFormat("es-MX", {
    month: "long",
    year: "numeric",
  })
    .format(toDate(date))
    .replace(/^\w/, (letter) => letter.toUpperCase());
}

function formatDayLabel(date) {
  return new Intl.DateTimeFormat("es-MX", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(toDate(date));
}

function formatShortDay(date) {
  return new Intl.DateTimeFormat("es-MX", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  }).format(toDate(date));
}

function daysFromToday(date, today) {
  const ms = toDate(date).getTime() - toDate(today).getTime();
  return Math.round(ms / 86400000);
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function timestampMillis(value) {
  if (!value) return 0;
  if (typeof value?.toDate === "function") return value.toDate().getTime();
  if (typeof value?.seconds === "number") return value.seconds * 1000;
  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDetectedDate(value) {
  const ms = timestampMillis(value);
  if (!ms) return "";
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "short",
  }).format(new Date(ms));
}

function compatibleAgentIds(item) {
  return AGENT_ALIASES[item.agentId] || new Set([item.agentId]);
}

function agentName(agentId) {
  return AGENT_NAMES[agentId] || agentId || "Agente sin identificar";
}

function agentIsCompatible(item, agentId) {
  if (!agentId || !item?.agentId) return true;
  return compatibleAgentIds(item).has(agentId);
}

function hasCompletedDelivery(project) {
  return (
    project?.status === "completed" ||
    Boolean(project?.videoUrl) ||
    Boolean(project?.videoPath) ||
    Boolean(project?.outputs?.videoUrl) ||
    Boolean(project?.carousel?.instagram?.length)
  );
}

function hasPublishedDelivery(project, item = null) {
  const youtube = project?.youtube || {};
  const tiktok = project?.tiktok || {};
  const longUpload = Boolean(youtube.lastVideoId || youtube.lastStudioUrl);
  const shortsUpload = Boolean(
    youtube.shortsLastPublishJobId ||
      (Array.isArray(youtube.shortsUploads) && youtube.shortsUploads.length > 0)
  );
  const tiktokUpload = Boolean(tiktok?.publishing?.lastPublishId || tiktok?.publishing?.status === "inbox_delivered");

  if (item?.type === "long") return longUpload || tiktokUpload;
  if (item?.type === "short") return longUpload || shortsUpload || tiktokUpload;
  return longUpload || shortsUpload || tiktokUpload;
}

function hasScheduledDelivery(project, today, item = null) {
  const publishAt = project?.youtube?.lastScheduledPublishAt;
  const deadline = toDate(today).getTime();
  if (publishAt && timestampMillis(publishAt) > deadline) return true;
  if (item?.type !== "long" && Array.isArray(project?.youtube?.shortsUploads)) {
    return project.youtube.shortsUploads.some((upload) => timestampMillis(upload?.publishAt) > deadline);
  }
  return false;
}

function inferProjectStatus(project, today, item = null) {
  if (!project) return { status: "pending", label: "" };
  if (hasPublishedDelivery(project, item)) return { status: "published", label: "Subido detectado" };
  if (hasScheduledDelivery(project, today, item)) return { status: "scheduled", label: "Programado detectado" };
  if (hasCompletedDelivery(project)) return { status: "created", label: "Proyecto listo" };
  if (LIVE_PROJECT_STATUSES.has(project.status)) return { status: "creating", label: "Proyecto en curso" };
  if (project.status === "failed" || project.status === "error") return { status: "pending", label: "Proyecto con error" };
  return { status: "pending", label: "" };
}

function projectMatchesItem(project, item) {
  const projectAgent = project?.agentId || project?.agent || "";
  const allowedAgents = compatibleAgentIds(item);
  if (projectAgent && item.agentId && !allowedAgents.has(projectAgent)) return false;

  const projectTitle = normalizeText(project?.title || project?.topic || "");
  const itemTitle = normalizeText(item.title);
  const parentTopic = normalizeText(item.parentTopic || "");
  if (!projectTitle || !itemTitle) return false;

  if (projectTitle === itemTitle) return true;
  if (parentTopic && projectTitle === parentTopic) return true;

  const shorter = projectTitle.length < itemTitle.length ? projectTitle : itemTitle;
  const longer = projectTitle.length < itemTitle.length ? itemTitle : projectTitle;
  return shorter.length >= 18 && longer.includes(shorter);
}

function findDetectedProject(item, projects) {
  const candidates = projects
    .filter((project) => projectMatchesItem(project, item))
    .sort((a, b) => {
      const score = (project) => {
        if (hasPublishedDelivery(project, item)) return 5;
        if (hasCompletedDelivery(project)) return 4;
        if (LIVE_PROJECT_STATUSES.has(project.status)) return 3;
        if (project.status === "failed" || project.status === "error") return 1;
        return 2;
      };
      return (
        score(b) - score(a) ||
        timestampMillis(b.updatedAt || b.completedAt || b.createdAt) -
          timestampMillis(a.updatedAt || a.completedAt || a.createdAt)
      );
    });
  return candidates[0] || null;
}

function isRecoveryCandidate(item, today) {
  return daysFromToday(item.date, today) <= 0 && !DONE_STATUSES.has(item.status);
}

function getDefaultScope(items, today) {
  const currentMonth = formatMonthLabel(today);
  return items.some((item) => item.monthLabel === currentMonth) ? currentMonth : "all";
}

function loadOverrides() {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveOverrides(overrides) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

function mergeItem(item, overrides, detectedProject, today) {
  const saved = overrides[item.id] || {};
  const detected = inferProjectStatus(detectedProject, today, item);
  const hasManualStatus = Object.prototype.hasOwnProperty.call(saved, "status");
  const status = hasManualStatus ? saved.status : detected.status || "pending";
  return {
    ...item,
    ...saved,
    title: saved.title || item.title,
    status,
    signal: saved.signal || "unknown",
    detectedStatus: detected.status,
    detectedStatusLabel: detected.label,
    statusSource: hasManualStatus ? "manual" : detectedProject ? "detectado" : "agenda",
    detectedProject: detectedProject
      ? {
          id: detectedProject.id,
          title: detectedProject.title || detectedProject.topic || "",
          status: detectedProject.status || "",
          agentId: detectedProject.agentId || detectedProject.agent || "",
          updatedAt: detectedProject.updatedAt || detectedProject.completedAt || detectedProject.createdAt || null,
          youtubeStudioUrl: detectedProject.youtube?.lastStudioUrl || "",
          youtubeVideoId: detectedProject.youtube?.lastVideoId || "",
          videoUrl: detectedProject.videoUrl || detectedProject.outputs?.videoUrl || "",
          error: detectedProject.error || detectedProject.deliveryError || "",
        }
      : null,
    metrics: {
      views: "",
      retention: "",
      comments: "",
      subscribers: "",
      ...(saved.metrics || {}),
    },
  };
}

function buildGroupedItems(items) {
  return items.reduce((acc, item) => {
    if (!acc[item.date]) acc[item.date] = [];
    acc[item.date].push(item);
    return acc;
  }, {});
}

function createScopedItems(items, scope, today) {
  if (scope === "all") return items;
  if (scope === "today") return items.filter((item) => item.date === today);
  if (scope === "week") {
    return items.filter((item) => {
      const delta = daysFromToday(item.date, today);
      return delta >= 0 && delta <= 7;
    });
  }
  return items.filter((item) => item.monthLabel === scope);
}

function Stat({ label, value, sub, accent = "var(--paper)" }) {
  return (
    <div className="cf-card cf-stat-card" style={{ padding: "var(--s-5)", minWidth: 180, flex: 1 }}>
      <div className="cf-mono-sm" style={{ marginBottom: 10 }}>
        {label}
      </div>
      <div
        className="cf-stat-value"
        style={{
          fontFamily: "var(--font-display)",
          fontStyle: "italic",
          fontWeight: 800,
          fontSize: 40,
          lineHeight: 0.95,
          color: accent,
          marginBottom: 8,
        }}
      >
        {value}
      </div>
      <div className="cf-caption">{sub}</div>
    </div>
  );
}

function SegmentedControl({ label, options, value, onChange }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      {label && <span className="cf-mono-sm">{label}</span>}
      {options.map((option) => {
        const active = value === option.id;
        return (
          <button
            key={option.id}
            type="button"
            className={`cf-btn cf-btn--sm ${active ? "cf-btn--secondary" : "cf-btn--ghost"}`}
            onClick={() => onChange(option.id)}
            style={active ? { borderColor: "var(--ember)", color: "var(--ember)" } : undefined}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function MetricInput({ label, value, onChange, placeholder }) {
  return (
    <label style={{ minWidth: 86, flex: "1 1 86px" }}>
      <span className="cf-mono-sm" style={{ display: "block", marginBottom: 6 }}>
        {label}
      </span>
      <input
        className="cf-input"
        value={value || ""}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        style={{ padding: "9px 10px", fontSize: 13 }}
      />
    </label>
  );
}

function AgendaItem({ item, today, updateItem }) {
  const statusMeta = STATUS_META[item.status] || STATUS_META.pending;
  const signalMeta = SIGNAL_META[item.signal] || SIGNAL_META.unknown;
  const dateDelta = daysFromToday(item.date, today);
  const isToday = dateDelta === 0;
  const isPast = dateDelta < 0;
  const createHref = buildCreateContentHref(item);
  const derivatives = derivativeOptionsForItem(item);
  const projectHref = item.detectedProject?.id ? `/dashboard/project/${item.detectedProject.id}` : "";
  const publishedHref = item.detectedProject?.youtubeStudioUrl || item.youtubeUrl || "";
  const plannedAgentName = agentName(item.agentId);
  const detectedAgentId = item.detectedProject?.agentId || "";
  const detectedAgentName = agentName(detectedAgentId);
  const detectedAgentDiffers = detectedAgentId && !agentIsCompatible(item, detectedAgentId);
  const sourceLabel =
    item.statusSource === "manual"
      ? "Manual"
      : item.statusSource === "detectado"
        ? "Detectado"
        : "Agenda";
  const primaryAction = projectHref
    ? {
        href: projectHref,
        label: item.status === "creating" ? "Ver avance" : item.status === "pending" ? "Revisar proyecto" : "Abrir proyecto",
        icon: item.status === "creating" ? "eye" : "externalLink",
      }
    : {
        href: createHref,
        label: "Crear",
        icon: "sparkles",
      };

  const updateMetric = (key, value) => {
    updateItem(item.id, {
      metrics: {
        ...(item.metrics || {}),
        [key]: value,
      },
    });
  };

  return (
    <article
      className="cf-card cf-fade"
      style={{
        padding: "var(--s-5)",
        borderColor: isToday ? "var(--ember)" : "var(--rule-1)",
        background: isToday
          ? "linear-gradient(180deg, rgba(224,83,61,0.08), rgba(224,83,61,0.02)), var(--ink-1)"
          : "var(--ink-1)",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.2fr) minmax(260px, 0.7fr)",
          gap: "var(--s-5)",
          alignItems: "start",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            <span className={`cf-badge ${item.type === "long" ? "cf-badge--starter" : "cf-badge--creator"}`}>
              {item.typeLabel}
            </span>
            <span className={`cf-badge ${statusMeta.badge}`}>{statusMeta.label}</span>
            <span className={`cf-badge ${signalMeta.badge}`}>{signalMeta.label}</span>
            <span className="cf-badge cf-badge--neutral">{sourceLabel}</span>
            <span className="cf-mono-sm" style={{ color: isPast ? "var(--paper-mute)" : "var(--paper-dim)" }}>
              {item.displayTime}
            </span>
          </div>

          <input
            className="cf-input"
            value={item.title}
            onChange={(event) => updateItem(item.id, { title: event.target.value })}
            style={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 760,
              fontSize: 24,
              lineHeight: 1.12,
              padding: "12px 14px",
              marginBottom: 12,
            }}
          />

          <div className="cf-caption" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
            <span>{item.channel}</span>
            <span>·</span>
            <span>{item.pillar}</span>
          </div>
          <div
            className="cf-caption"
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              margin: "-6px 0 16px",
              alignItems: "center",
            }}
          >
            <span
              className="cf-badge cf-badge--neutral"
              title={item.agentId}
              style={{ textTransform: "none" }}
            >
              Plan: {plannedAgentName}
            </span>
            {item.detectedProject && (
              <span
                className={`cf-badge ${detectedAgentDiffers ? "cf-badge--warn" : "cf-badge--ok"}`}
                title={detectedAgentId}
                style={{ textTransform: "none" }}
              >
                Creado con: {detectedAgentName}
              </span>
            )}
            {detectedAgentDiffers && (
              <span className="cf-caption" style={{ color: "var(--warn)" }}>
                Revisar: el proyecto detectado usa otro agente.
              </span>
            )}
          </div>
          {item.seoKeywords && (
            <div className="cf-caption" style={{ margin: "-6px 0 16px", color: "var(--paper-dim)" }}>
              SEO: {item.seoKeywords}
            </div>
          )}
          {item.detectedProject && (
            <div
              className="cf-caption"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                flexWrap: "wrap",
                margin: "-4px 0 16px",
                color: "var(--paper-dim)",
              }}
            >
              <Icon name="check" size={14} />
              <span>
                {item.detectedStatusLabel || "Proyecto detectado"}
                {item.detectedProject.updatedAt ? ` · ${formatDetectedDate(item.detectedProject.updatedAt)}` : ""}
              </span>
              {item.detectedProject.error && (
                <span style={{ color: "var(--warn)" }}>Revisar error antes de continuar</span>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="cf-btn cf-btn--primary cf-btn--sm" href={primaryAction.href} style={{ textDecoration: "none" }}>
              <Icon name={primaryAction.icon} size={14} />
              {primaryAction.label}
            </Link>
            {projectHref && (
              <Link
                className="cf-btn cf-btn--ghost cf-btn--sm"
                href={createHref}
                title={`Crear con ${plannedAgentName} (${item.agentId})`}
                style={{ textDecoration: "none" }}
              >
                <Icon name="sparkles" size={14} />
                Crear otra version
              </Link>
            )}
            {publishedHref && (
              <a
                className="cf-btn cf-btn--ghost cf-btn--sm"
                href={publishedHref}
                target="_blank"
                rel="noreferrer"
                style={{ textDecoration: "none" }}
              >
                <Icon name="externalLink" size={14} />
                Ver subida
              </a>
            )}
            <button
              type="button"
              className="cf-btn cf-btn--ghost cf-btn--sm"
              onClick={() => navigator.clipboard?.writeText(item.title)}
            >
              <Icon name="copy" size={14} />
              Copiar título
            </button>
            {derivatives.map((option) => (
              <Link
                key={`${item.id}-${option.agentId}`}
                className="cf-btn cf-btn--ghost cf-btn--sm"
                href={buildCreateContentHref(item, option)}
                title={`Crear con ${agentName(option.agentId)} (${option.agentId})`}
                style={{ textDecoration: "none" }}
              >
                <Icon name={option.agentId.includes("carousel") ? "image" : option.agentId.includes("shorts") ? "zap" : "film"} size={14} />
                {option.label}
              </Link>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--s-3)" }}>
            <label>
              <span className="cf-mono-sm" style={{ display: "block", marginBottom: 6 }}>
                Estado
              </span>
              <select
                className="cf-input"
                value={item.status}
                onChange={(event) => updateItem(item.id, { status: event.target.value })}
                style={{ padding: "9px 10px", fontSize: 13 }}
              >
                {EDITORIAL_STATUS.map((status) => (
                  <option key={status.id} value={status.id}>
                    {status.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="cf-mono-sm" style={{ display: "block", marginBottom: 6 }}>
                Señal
              </span>
              <select
                className="cf-input"
                value={item.signal}
                onChange={(event) => updateItem(item.id, { signal: event.target.value })}
                style={{ padding: "9px 10px", fontSize: 13 }}
              >
                {EDITORIAL_SIGNAL.map((signal) => (
                  <option key={signal.id} value={signal.id}>
                    {signal.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div style={{ display: "flex", gap: "var(--s-2)", flexWrap: "wrap" }}>
            <MetricInput label="Vistas" value={item.metrics?.views} onChange={(value) => updateMetric("views", value)} placeholder="24h" />
            <MetricInput label="Retención" value={item.metrics?.retention} onChange={(value) => updateMetric("retention", value)} placeholder="%" />
            <MetricInput label="Comentarios" value={item.metrics?.comments} onChange={(value) => updateMetric("comments", value)} placeholder="0" />
            <MetricInput label="Subs" value={item.metrics?.subscribers} onChange={(value) => updateMetric("subscribers", value)} placeholder="+0" />
          </div>

          <input
            className="cf-input"
            value={item.youtubeUrl || ""}
            onChange={(event) => updateItem(item.id, { youtubeUrl: event.target.value })}
            placeholder="URL publicada"
            style={{ padding: "9px 10px", fontSize: 13 }}
          />
          <textarea
            className="cf-input"
            value={item.notes || ""}
            onChange={(event) => updateItem(item.id, { notes: event.target.value })}
            placeholder="Notas editoriales o temas derivados"
            rows={2}
            style={{ resize: "vertical", minHeight: 62, fontSize: 13 }}
          />
        </div>
      </div>
    </article>
  );
}

function DayGroup({ date, items, today, updateItem }) {
  const delta = daysFromToday(date, today);
  const label =
    delta === 0
      ? "Hoy"
      : delta === 1
        ? "Mañana"
        : delta === -1
          ? "Ayer"
          : delta > 0
            ? `En ${delta} días`
            : `Hace ${Math.abs(delta)} días`;

  return (
    <section style={{ display: "grid", gridTemplateColumns: "180px minmax(0, 1fr)", gap: "var(--s-5)", alignItems: "start" }}>
      <div className="cf-card" style={{ padding: "var(--s-4)", position: "sticky", top: 24 }}>
        <div className="cf-mono-sm" style={{ color: delta === 0 ? "var(--ember)" : "var(--paper-mute)", marginBottom: 8 }}>
          {label}
        </div>
        <div className="cf-h3" style={{ marginBottom: 6, textTransform: "capitalize" }}>
          {formatShortDay(date)}
        </div>
        <div className="cf-caption">{items.length} pieza{items.length === 1 ? "" : "s"}</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
        {items.map((item) => (
          <AgendaItem key={item.id} item={item} today={today} updateItem={updateItem} />
        ))}
      </div>
    </section>
  );
}

export default function EditorialAgendaPage() {
  const { user } = useAuth();
  const today = todayIso();
  const [overrides, setOverrides] = useState({});
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [projectLoadError, setProjectLoadError] = useState("");
  const [scope, setScope] = useState(() => getDefaultScope(EDITORIAL_CALENDAR_ITEMS, today));
  const [workFilter, setWorkFilter] = useState("catchup");
  const [channelFilter, setChannelFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setOverrides(loadOverrides()), 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!user) {
      const timer = window.setTimeout(() => {
        setProjects([]);
        setLoadingProjects(false);
      }, 0);
      return () => window.clearTimeout(timer);
    }

    const loadingTimer = window.setTimeout(() => {
      setLoadingProjects(true);
      setProjectLoadError("");
    }, 0);
    const projectsQuery = query(
      collection(db, "projects"),
      where("userId", "==", user.uid),
      limit(800),
    );

    const unsubscribe = onSnapshot(
      projectsQuery,
      (snap) => {
        const nextProjects = snap.docs
          .map((doc) => ({ id: doc.id, ...doc.data() }))
          .sort(
            (a, b) =>
              timestampMillis(b.updatedAt || b.completedAt || b.createdAt) -
              timestampMillis(a.updatedAt || a.completedAt || a.createdAt),
        );
        setProjects(nextProjects);
        setProjectLoadError("");
        setLoadingProjects(false);
      },
      (error) => {
        setProjectLoadError(error.message || "No se pudieron leer los proyectos.");
        setLoadingProjects(false);
      },
    );

    return () => {
      window.clearTimeout(loadingTimer);
      unsubscribe();
    };
  }, [user]);

  const items = useMemo(
    () =>
      EDITORIAL_CALENDAR_ITEMS.map((item) => {
        const detectedProject = findDetectedProject(item, projects);
        return mergeItem(item, overrides, detectedProject, today);
      }),
    [overrides, projects, today],
  );

  const months = useMemo(() => {
    const seen = new Set();
    return items
      .map((item) => item.monthLabel)
      .filter((month) => {
        if (seen.has(month)) return false;
        seen.add(month);
        return true;
      });
  }, [items]);

  const channelOptions = useMemo(() => {
    const seen = new Map();
    items.forEach((item) => {
      seen.set(item.channelSlug || item.channel, item.channel);
    });
    return [
      { id: "all", label: "Todos los canales" },
      ...Array.from(seen, ([id, label]) => ({ id, label })),
    ];
  }, [items]);

  const scoped = useMemo(() => {
    const q = search.trim().toLowerCase();
    const baseItems =
      workFilter === "catchup" || workFilter === "daily"
        ? items
        : createScopedItems(items, scope, today);
    let result = baseItems.filter((item) => {
      if (workFilter === "catchup" && !isRecoveryCandidate(item, today)) return false;
      if (workFilter === "todo" && item.status !== "pending") return false;
      if (workFilter === "ready" && !READY_STATUSES.has(item.status)) return false;
      if (channelFilter !== "all" && (item.channelSlug || item.channel) !== channelFilter) return false;
      if (typeFilter !== "all" && item.type !== typeFilter) return false;
      if (statusFilter === "winner" && item.signal !== "winner") return false;
      if (statusFilter !== "all" && statusFilter !== "winner" && item.status !== statusFilter) return false;
      if (!q) return true;
      return `${item.title} ${item.parentTopic || ""} ${item.pillar} ${item.typeLabel} ${item.channel} ${item.seoKeywords || ""}`
        .toLowerCase()
        .includes(q);
    });
    if (workFilter === "daily") {
      result = result.filter((item) => isRecoveryCandidate(item, today)).slice(0, 10);
    }
    return result;
  }, [channelFilter, items, scope, search, statusFilter, today, typeFilter, workFilter]);

  const grouped = useMemo(() => buildGroupedItems(scoped), [scoped]);
  const dayKeys = useMemo(() => Object.keys(grouped).sort(), [grouped]);

  const summary = useMemo(() => {
    const nextSeven = items.filter((item) => {
      const delta = daysFromToday(item.date, today);
      return delta >= 0 && delta <= 7;
    });
    const recoveryQueue = items.filter((item) => isRecoveryCandidate(item, today));
    return {
      today: items.filter((item) => item.date === today).length,
      overdue: items.filter((item) => daysFromToday(item.date, today) < 0 && !DONE_STATUSES.has(item.status)).length,
      pending: items.filter((item) => item.status === "pending").length,
      created: items.filter((item) => READY_STATUSES.has(item.status)).length,
      published: items.filter((item) => item.status === "published" || item.status === "measured").length,
      nextSeven: nextSeven.length,
      winners: items.filter((item) => item.signal === "winner").length,
      recoveryQueue,
      nextRecovery: recoveryQueue[0] || null,
    };
  }, [items, today]);

  const updateItem = (id, patch) => {
    setOverrides((current) => {
      const next = {
        ...current,
        [id]: {
          ...(current[id] || {}),
          ...patch,
          metrics: patch.metrics || current[id]?.metrics,
        },
      };
      saveOverrides(next);
      return next;
    });
  };

  const resetAgenda = () => {
    if (!window.confirm("¿Restaurar estados y métricas de la agenda local?")) return;
    setOverrides({});
    saveOverrides({});
  };

  const scopeOptions = [
    { id: "today", label: "Hoy" },
    { id: "week", label: "7 días" },
    { id: "all", label: "Todo" },
    ...months.map((month) => ({ id: month, label: month.replace(" 2026", "") })),
  ];

  return (
    <div style={{ paddingBottom: "var(--s-7)" }}>
      <header className="cf-fade" style={{ marginBottom: "var(--s-7)" }}>
        <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 8 }}>
          AGENDA EDITORIAL
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: 24,
            flexWrap: "wrap",
          }}
        >
          <div>
            <h1 className="cf-display" style={{ margin: 0, maxWidth: 840 }}>
              Agenda editorial,{" "}
              <em style={{ color: "var(--ember)", fontStyle: "italic" }}>canal por canal.</em>
            </h1>
            <p className="cf-body-lg" style={{ maxWidth: 760, margin: "var(--s-4) 0 0" }}>
              Calendario operativo de largos, Shorts y derivados: creación, publicación, medición y próximos temas.
            </p>
          </div>
          <button className="cf-btn cf-btn--secondary" type="button" onClick={resetAgenda}>
            <Icon name="refresh" size={16} />
            Restaurar
          </button>
        </div>
      </header>

      <div className="cf-stat-grid" style={{ display: "flex", gap: "var(--s-4)", flexWrap: "wrap", marginBottom: "var(--s-6)" }}>
        <Stat label="ATRASADOS" value={summary.overdue} sub="pendientes antes de hoy" accent="var(--warn)" />
        <Stat label="POR CREAR" value={summary.pending} sub="sin proyecto detectado" accent="var(--ember)" />
        <Stat label="LISTOS" value={summary.created} sub="creados o programados" accent="var(--info)" />
        <Stat label="PUBLICADOS" value={summary.published} sub="subidos o medidos" accent="var(--ok)" />
        <Stat label="HOY" value={summary.today} sub={formatDayLabel(today)} accent="var(--paper)" />
      </div>

      {(summary.nextRecovery || loadingProjects || projectLoadError) && (
        <section
          className="cf-card cf-fade cf-fade--1"
          style={{
            padding: "var(--s-5)",
            marginBottom: "var(--s-5)",
            borderColor: summary.nextRecovery ? "rgba(224,83,61,0.45)" : "var(--rule-1)",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: "var(--s-4)", alignItems: "center" }}>
            <div style={{ minWidth: 0 }}>
              <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 8 }}>
                PLAN DE RECUPERACIÓN
              </div>
              {loadingProjects ? (
                <div className="cf-caption">Cruzando agenda con proyectos existentes...</div>
              ) : projectLoadError ? (
                <div className="cf-caption" style={{ color: "var(--warn)" }}>
                  No pude leer proyectos para autocompletar estados: {projectLoadError}
                </div>
              ) : summary.nextRecovery ? (
                <>
                  <h2 className="cf-h3" style={{ margin: 0 }}>
                    {summary.nextRecovery.title}
                  </h2>
                  <div className="cf-caption" style={{ marginTop: 8 }}>
                    Siguiente recomendado · {summary.nextRecovery.channel} · {summary.nextRecovery.typeLabel} · {formatShortDay(summary.nextRecovery.date)}
                  </div>
                </>
              ) : (
                <div className="cf-caption">No hay backlog pendiente con los filtros actuales.</div>
              )}
            </div>
            {summary.nextRecovery && (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                <Link
                  className="cf-btn cf-btn--primary cf-btn--sm"
                  href={
                    summary.nextRecovery.detectedProject?.id
                      ? `/dashboard/project/${summary.nextRecovery.detectedProject.id}`
                      : buildCreateContentHref(summary.nextRecovery)
                  }
                  style={{ textDecoration: "none" }}
                >
                  <Icon name={summary.nextRecovery.detectedProject?.id ? "externalLink" : "sparkles"} size={14} />
                  {summary.nextRecovery.detectedProject?.id ? "Abrir" : "Crear ahora"}
                </Link>
                <button
                  className="cf-btn cf-btn--ghost cf-btn--sm"
                  type="button"
                  onClick={() => {
                    setWorkFilter("daily");
                    setScope("all");
                  }}
                >
                  <Icon name="calendar" size={14} />
                  Ver plan diario
                </button>
              </div>
            )}
          </div>
        </section>
      )}

      <section className="cf-card cf-filter-strip cf-fade cf-fade--1" style={{ padding: "var(--s-4)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
          <SegmentedControl label="VISTA" options={scopeOptions} value={scope} onChange={setScope} />
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <SegmentedControl label="TRABAJO" options={WORK_FILTERS} value={workFilter} onChange={setWorkFilter} />
            <SegmentedControl label="CANAL" options={channelOptions} value={channelFilter} onChange={setChannelFilter} />
            <SegmentedControl label="FORMATO" options={TYPE_FILTERS} value={typeFilter} onChange={setTypeFilter} />
            <SegmentedControl label="ESTADO" options={STATUS_FILTERS} value={statusFilter} onChange={setStatusFilter} />
            <div style={{ flex: 1 }} />
            <div className="cf-filter-search" style={{ position: "relative", minWidth: 280 }}>
              <span
                style={{
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--paper-mute)",
                  pointerEvents: "none",
                }}
              >
                <Icon name="search" size={16} />
              </span>
              <input
                className="cf-input"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar tema, canal o pilar"
                style={{ paddingLeft: 36 }}
              />
            </div>
          </div>
        </div>
      </section>

      {dayKeys.length === 0 ? (
        <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
          <div className="cf-mono-sm" style={{ marginBottom: 8 }}>
            SIN RESULTADOS
          </div>
          <div className="cf-caption">No hay piezas con estos filtros.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-6)" }}>
          {dayKeys.map((date) => (
            <DayGroup key={date} date={date} items={grouped[date]} today={today} updateItem={updateItem} />
          ))}
        </div>
      )}
    </div>
  );
}
