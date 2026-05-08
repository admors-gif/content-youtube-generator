"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import Icon from "@/components/Icon";
import { useAuth } from "@/context/AuthContext";
import { authedFetch, getApiBase } from "@/lib/apiClient";

const FILTERS = [
  { id: "all", label: "Todos" },
  { id: "needs_video", label: "Falta video" },
  { id: "needs_shorts", label: "Faltan Shorts" },
  { id: "scheduled", label: "Programados" },
  { id: "complete", label: "Completos" },
  { id: "errors", label: "Errores" },
];

const STATUS_META = {
  not_ready: { label: "No listo", cls: "cf-badge--neutral" },
  uploading: { label: "Subiendo", cls: "cf-badge--warn" },
  missing: { label: "Falta subir", cls: "cf-badge--warn" },
  error: { label: "Error", cls: "cf-badge--bad" },
  scheduled: { label: "Programado", cls: "cf-badge--starter" },
  uploaded: { label: "Subido", cls: "cf-badge--ok" },
  ready: { label: "Listo", cls: "cf-badge--ok" },
  none: { label: "Sin Shorts", cls: "cf-badge--neutral" },
  partial: { label: "Parcial", cls: "cf-badge--warn" },
};

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-MX", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatShortDate(value) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function actionHref(item) {
  const kind = item?.nextAction?.kind;
  if (kind === "publish_video") return `/dashboard/project/${item.id}?publish=youtube`;
  if (kind === "publish_shorts") return `/dashboard/project/${item.id}?publish=shorts`;
  return `/dashboard/project/${item.id}`;
}

function actionIcon(kind) {
  if (kind === "publish_video" || kind === "publish_shorts") return "uploadCloud";
  if (kind === "complete") return "check";
  if (kind === "review") return "alert";
  return "eye";
}

function Stat({ label, value, sub, accent }) {
  return (
    <div className="cf-card" style={{ padding: "var(--s-5)", minWidth: 190, flex: 1 }}>
      <div className="cf-mono-sm" style={{ marginBottom: 10 }}>
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 800,
          fontSize: 42,
          lineHeight: 0.95,
          color: accent || "var(--paper)",
          marginBottom: 8,
        }}
      >
        {value}
      </div>
      <div className="cf-caption">{sub}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || STATUS_META.not_ready;
  return <span className={`cf-badge ${meta.cls}`}>{meta.label}</span>;
}

function PublicationRow({ item, index }) {
  const video = item.video || {};
  const shorts = item.shorts || {};
  const nextAction = item.nextAction || {};
  const isTikTok = item.platform === "tiktok";
  const shortsStudioUrl = (shorts.uploads || []).find((upload) => upload.youtubeStudioUrl)?.youtubeStudioUrl;

  return (
    <div
      className={`cf-card cf-fade cf-fade--${(index % 4) + 1}`}
      style={{
        padding: "var(--s-5)",
        display: "grid",
        gridTemplateColumns: "minmax(280px, 1.5fr) minmax(190px, 0.9fr) minmax(190px, 0.9fr) minmax(190px, 0.8fr)",
        gap: "var(--s-5)",
        alignItems: "center",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 8,
            flexWrap: "wrap",
          }}
        >
          <span className="cf-badge cf-badge--neutral">
            {isTikTok ? "TikTok" : (item.format || "video").replace(/_/g, " ")}
          </span>
          {item.channel?.title && (
            <span className="cf-mono-sm" style={{ color: "var(--paper-mute)" }}>
              {item.channel.title}
            </span>
          )}
        </div>
        <h2
          className="cf-h3"
          style={{
            margin: "0 0 8px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={item.title}
        >
          {item.title}
        </h2>
        <div className="cf-caption">Actualizado {formatShortDate(item.updatedAt || item.createdAt)}</div>
      </div>

      <div>
        <div className="cf-mono-sm" style={{ marginBottom: 8 }}>
          {isTikTok ? "VIDEO TIKTOK" : "VIDEO LARGO"}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <StatusBadge status={video.status} />
          {video.warning && <span className="cf-badge cf-badge--warn">Miniatura</span>}
        </div>
        {video.publishAt && (
          <div className="cf-caption" style={{ marginTop: 8 }}>
            {formatDateTime(video.publishAt)}
          </div>
        )}
        {video.error && (
          <div className="cf-caption" style={{ marginTop: 8, color: "var(--bad)" }}>
            {video.error}
          </div>
        )}
      </div>

      <div>
        <div className="cf-mono-sm" style={{ marginBottom: 8 }}>
          {isTikTok ? "PUBLICACIÓN" : "SHORTS"}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <StatusBadge status={isTikTok ? "ready" : shorts.status} />
          {isTikTok && <span className="cf-badge cf-badge--neutral">Nativo</span>}
          {shorts.total > 0 && (
            <span className="cf-badge cf-badge--neutral">
              {shorts.uploaded}/{shorts.total}
            </span>
          )}
        </div>
        {shorts.scheduled > 0 && (
          <div className="cf-caption" style={{ marginTop: 8 }}>
            {shorts.scheduled} programado{shorts.scheduled === 1 ? "" : "s"}
          </div>
        )}
        {(shorts.error || shorts.errors?.length > 0) && (
          <div className="cf-caption" style={{ marginTop: 8, color: "var(--bad)" }}>
            {shorts.error || `${shorts.errors.length} error(es)`}
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", flexWrap: "wrap" }}>
        {video.youtubeStudioUrl && (
          <a
            className="cf-btn cf-btn--ghost cf-btn--sm"
            href={video.youtubeStudioUrl}
            target="_blank"
            rel="noreferrer"
            title="Abrir video en YouTube Studio"
          >
            <Icon name="externalLink" size={14} />
            Studio
          </a>
        )}
        {shortsStudioUrl && (
          <a
            className="cf-btn cf-btn--ghost cf-btn--sm"
            href={shortsStudioUrl}
            target="_blank"
            rel="noreferrer"
            title="Abrir Short en YouTube Studio"
          >
            <Icon name="externalLink" size={14} />
            Short
          </a>
        )}
        <Link
          className={`cf-btn cf-btn--sm ${["publish_video", "publish_shorts"].includes(nextAction.kind) ? "cf-btn--primary" : "cf-btn--secondary"}`}
          href={actionHref(item)}
          style={{ textDecoration: "none" }}
        >
          <Icon name={isTikTok ? "zap" : actionIcon(nextAction.kind)} size={14} />
          {nextAction.label || "Abrir"}
        </Link>
      </div>
    </div>
  );
}

export default function PublicationsPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const loadPublications = async () => {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/youtube/publications`);
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || json.error || "No se pudo cargar publicaciones");
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return undefined;
    const timer = window.setTimeout(() => loadPublications(), 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const items = useMemo(() => data?.items || [], [data]);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      if (filter === "needs_video" && !["missing", "error"].includes(item.video?.status)) return false;
      if (filter === "needs_shorts" && !["missing", "partial", "error"].includes(item.shorts?.status)) return false;
      if (filter === "scheduled" && item.video?.status !== "scheduled" && !(item.shorts?.scheduled > 0)) return false;
      if (filter === "complete" && item.nextAction?.kind !== "complete") return false;
      if (filter === "errors" && item.video?.status !== "error" && item.shorts?.status !== "error") return false;
      if (!q) return true;
      const haystack = `${item.title || ""} ${item.channel?.title || ""} ${item.format || ""}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [items, filter, search]);

  const summary = data?.summary || {};

  return (
    <div style={{ paddingBottom: "var(--s-7)" }}>
      <header className="cf-fade" style={{ marginBottom: "var(--s-7)" }}>
        <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 8 }}>
          CENTRO MULTIPLATAFORMA
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
          <h1
            className="cf-display"
            style={{
              margin: 0,
              maxWidth: 780,
            }}
          >
            Centro de{" "}
            <em style={{ color: "var(--ember)", fontStyle: "italic" }}>
              publicaciones
            </em>
          </h1>
          <button
            className="cf-btn cf-btn--secondary"
            onClick={loadPublications}
            disabled={loading}
          >
            <Icon name="refresh" size={16} />
            {loading ? "Actualizando" : "Actualizar"}
          </button>
        </div>
      </header>

      <div
        style={{
          display: "flex",
          gap: "var(--s-4)",
          marginBottom: "var(--s-6)",
          flexWrap: "wrap",
        }}
      >
        <Stat label="FALTA VIDEO" value={summary.needsVideo ?? 0} sub="videos largos pendientes" accent="var(--warn)" />
        <Stat label="FALTAN SHORTS" value={summary.needsShorts ?? 0} sub="episodios con clips pendientes" accent="var(--ember)" />
        <Stat label="PROGRAMADOS" value={summary.scheduled ?? 0} sub="con fecha de salida" accent="var(--info)" />
        <Stat label="COMPLETOS" value={summary.complete ?? 0} sub="sin acción pendiente" accent="var(--ok)" />
      </div>

      <div
        className="cf-card cf-fade cf-fade--1"
        style={{
          padding: "var(--s-4)",
          marginBottom: "var(--s-5)",
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <span className="cf-mono-sm">FILTRO</span>
        {FILTERS.map((item) => {
          const active = filter === item.id;
          return (
            <button
              key={item.id}
              className={`cf-btn cf-btn--sm ${active ? "cf-btn--secondary" : "cf-btn--ghost"}`}
              onClick={() => setFilter(item.id)}
              style={active ? { borderColor: "var(--ember)", color: "var(--ember)" } : undefined}
            >
              {item.label}
            </button>
          );
        })}
        <div style={{ flex: 1 }} />
        <div style={{ position: "relative", minWidth: 260 }}>
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
            placeholder="Buscar episodio o canal"
            style={{ paddingLeft: 36 }}
          />
        </div>
      </div>

      {error && (
        <div
          className="cf-card"
          style={{
            padding: "var(--s-5)",
            borderColor: "var(--bad)",
            color: "var(--bad)",
            marginBottom: "var(--s-5)",
          }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
          <div className="cf-mono-sm">CARGANDO PUBLICACIONES</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
          <div className="cf-mono-sm" style={{ marginBottom: 8 }}>
            SIN RESULTADOS
          </div>
          <div className="cf-caption">No hay publicaciones con ese filtro.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
          {filtered.map((item, index) => (
            <PublicationRow key={item.id} item={item} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
