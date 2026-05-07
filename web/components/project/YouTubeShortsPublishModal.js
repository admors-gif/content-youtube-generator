"use client";

import { useEffect, useMemo, useState } from "react";
import Icon from "@/components/Icon";
import { authedFetch, getApiBase } from "@/lib/apiClient";

const inputStyle = {
  width: "100%",
  border: "1px solid var(--rule-1)",
  background: "rgba(11, 11, 14, 0.72)",
  color: "var(--paper)",
  borderRadius: "var(--r-2)",
  padding: "12px 14px",
  font: "var(--t-body)",
  outline: "none",
};

const SHORT_LABELS = {
  hook: "Gancho",
  mid: "Punto fuerte",
  end: "Cierre",
  closing: "Cierre",
};

function FieldLabel({ children }) {
  return (
    <label
      style={{
        display: "block",
        font: "var(--t-mono-sm)",
        color: "var(--paper-mute)",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        marginBottom: 8,
      }}
    >
      {children}
    </label>
  );
}

async function readJsonResponse(res) {
  try {
    return await res.json();
  } catch {
    return {};
  }
}

function toLocalInputValue(value) {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function addHoursToLocalValue(value, hours) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  date.setHours(date.getHours() + Number(hours || 0));
  return toLocalInputValue(date);
}

function formatDuration(seconds) {
  const value = Number(seconds || 0);
  if (!value) return "";
  return `${Math.round(value)}s`;
}

function makeRows(shorts, basePublishAtLocal = "") {
  return (shorts || []).map((short) => {
    const metadata = short.metadata || {};
    const preflight = short.preflight || {};
    const eligible = preflight.eligible !== false;
    return {
      index: short.index,
      label: short.label || "",
      signedUrl: short.signedUrl,
      duration: short.duration || preflight.durationSeconds,
      selected: eligible,
      title: metadata.title || "",
      description: metadata.description || "",
      tags: metadata.tagsCsv || "",
      privacyStatus: "private",
      publishAtLocal: basePublishAtLocal
        ? addHoursToLocalValue(basePublishAtLocal, metadata.offsetHours)
        : "",
      offsetHours: metadata.offsetHours || 0,
      preflight,
    };
  });
}

export default function YouTubeShortsPublishModal({ open, onClose, projectId, user }) {
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState(null);
  const [missing, setMissing] = useState([]);
  const [channels, setChannels] = useState([]);
  const [channelId, setChannelId] = useState("");
  const [basePublishAtLocal, setBasePublishAtLocal] = useState("");
  const [rows, setRows] = useState([]);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  const apiBase = getApiBase();

  useEffect(() => {
    if (!open || !user || !projectId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      setJob(null);
      setConfigured(null);
      try {
        const [previewRes, configRes, channelsRes] = await Promise.all([
          authedFetch(user, `${apiBase}/youtube/shorts/preview/${encodeURIComponent(projectId)}`),
          fetch(`${apiBase}/youtube/oauth/status`),
          authedFetch(user, `${apiBase}/youtube/channels`),
        ]);
        const previewData = await readJsonResponse(previewRes);
        const configData = await readJsonResponse(configRes);
        const channelsData = await readJsonResponse(channelsRes);
        if (cancelled) return;
        if (!previewRes.ok) throw new Error(previewData.error || previewData.detail || "No se pudo cargar Shorts");

        const isConfigured = Boolean(configData.configured ?? channelsData.configured);
        const channelList = channelsRes.ok ? channelsData.channels || [] : [];
        const baseValue = toLocalInputValue(previewData.defaults?.basePublishAt);
        setConfigured(isConfigured);
        setMissing(configData.missing || channelsData.missing || []);
        setChannels(channelList);
        setChannelId((prev) => prev || channelList[0]?.channelId || "");
        setBasePublishAtLocal(baseValue);
        setRows(makeRows(previewData.shorts || [], baseValue));
        if (isConfigured && !channelsRes.ok) {
          const detail = channelsData.error || channelsData.detail;
          setError(typeof detail === "string" ? detail : "No se pudieron cargar canales conectados.");
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "No se pudo preparar Shorts");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [open, user, projectId, apiBase]);

  useEffect(() => {
    if (!job?.jobId || ["completed", "error"].includes(job.status)) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const res = await authedFetch(user, `${apiBase}/youtube/publish/jobs/${encodeURIComponent(job.jobId)}`);
        const data = await res.json();
        if (!cancelled && res.ok) setJob((prev) => ({ ...prev, ...data, jobId: prev.jobId }));
      } catch {
        // El job sigue corriendo en backend aunque falle un poll.
      }
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [job?.jobId, job?.status, apiBase, user]);

  const selectedRows = useMemo(() => rows.filter((row) => row.selected), [rows]);

  if (!open) return null;

  const connectYouTube = async () => {
    setError("");
    try {
      const returnTo = `/dashboard/project/${projectId}`;
      const res = await authedFetch(user, `${apiBase}/youtube/oauth/start?returnTo=${encodeURIComponent(returnTo)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "YouTube no esta configurado");
      window.location.href = data.authorizationUrl;
    } catch (err) {
      setError(err.message || "No se pudo conectar YouTube");
    }
  };

  const updateRow = (index, patch) => {
    setRows((prev) => prev.map((row) => (row.index === index ? { ...row, ...patch } : row)));
  };

  const applySuggestedSchedule = (value = basePublishAtLocal) => {
    setRows((prev) =>
      prev.map((row) => ({
        ...row,
        publishAtLocal: value ? addHoursToLocalValue(value, row.offsetHours) : "",
      })),
    );
  };

  const submitPublish = async () => {
    setError("");
    setLoading(true);
    try {
      const shorts = selectedRows.map((row) => {
        const publishAt = row.publishAtLocal ? new Date(row.publishAtLocal).toISOString() : "";
        return {
          index: row.index,
          title: row.title,
          description: row.description,
          tags: row.tags,
          privacyStatus: publishAt ? "private" : row.privacyStatus,
          publishAt,
          categoryId: "22",
          hasPaidProductPlacement: false,
        };
      });
      const res = await authedFetch(user, `${apiBase}/youtube/shorts/publish/${encodeURIComponent(projectId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channelId, shorts }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "No se pudo iniciar publicacion de Shorts");
      setJob({ ...data, jobId: data.jobId });
    } catch (err) {
      setError(err.message || "No se pudieron publicar Shorts");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Publicar Shorts en YouTube"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.72)",
        zIndex: 82,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        className="cf-card"
        style={{
          width: "min(1120px, 100%)",
          maxHeight: "92vh",
          overflow: "auto",
          padding: 24,
          boxShadow: "var(--shadow-2)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
          <div>
            <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 8 }}>
              YouTube Shorts
            </div>
            <h2 className="cf-h2" style={{ margin: 0 }}>
              Programar clips cortos
            </h2>
          </div>
          <button className="cf-btn cf-btn--ghost" onClick={onClose} aria-label="Cerrar">
            <Icon name="x" size={16} /> Cerrar
          </button>
        </div>

        {error && (
          <div className="cf-card" style={{ padding: 14, marginBottom: 16, borderColor: "var(--bad)", color: "var(--paper)" }}>
            {error}
          </div>
        )}

        {!loading && configured === false && (
          <div className="cf-card" style={{ padding: 18, marginBottom: 16, borderColor: "var(--warn)" }}>
            <div className="cf-h4" style={{ marginBottom: 8 }}>Falta configurar OAuth de YouTube</div>
            <div className="cf-body" style={{ marginBottom: 12 }}>
              El backend ya tiene la integracion, pero faltan variables de entorno para conectar canales.
            </div>
            <div className="cf-mono-sm">Faltantes: {missing.join(", ") || "configuracion OAuth"}</div>
          </div>
        )}

        {configured === true && channels.length === 0 && (
          <div className="cf-card" style={{ padding: 18, marginBottom: 16 }}>
            <div className="cf-h4" style={{ marginBottom: 8 }}>Conecta tu canal</div>
            <div className="cf-body" style={{ marginBottom: 16 }}>
              Content Factory subira cada Short como privado o programado. Nunca necesita tu contrasena.
            </div>
            <button className="cf-btn cf-btn--primary" onClick={connectYouTube} disabled={loading}>
              <Icon name="uploadCloud" size={16} /> Conectar YouTube
            </button>
          </div>
        )}

        {configured === true && channels.length > 0 && (
          <div style={{ display: "grid", gap: 18 }}>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(220px, 320px)", gap: 14 }}>
              <div>
                <FieldLabel>Canal</FieldLabel>
                <select style={inputStyle} value={channelId} onChange={(e) => setChannelId(e.target.value)}>
                  {channels.map((channel) => (
                    <option key={channel.channelId} value={channel.channelId}>
                      {channel.title}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <FieldLabel>Fecha del episodio principal</FieldLabel>
                <input
                  style={inputStyle}
                  type="datetime-local"
                  value={basePublishAtLocal}
                  onChange={(e) => {
                    setBasePublishAtLocal(e.target.value);
                    applySuggestedSchedule(e.target.value);
                  }}
                />
              </div>
            </div>

            {rows.length === 0 && (
              <div className="cf-card" style={{ padding: 18, borderColor: "var(--warn)" }}>
                <div className="cf-h4" style={{ marginBottom: 8 }}>Este proyecto aun no tiene Shorts</div>
                <div className="cf-body">
                  Primero genera los clips cortos desde el flujo existente; despues vuelve aqui para subirlos o programarlos.
                </div>
              </div>
            )}

            {rows.map((row) => {
              const blocked = row.preflight?.eligible === false;
              return (
                <div
                  key={row.index}
                  className="cf-card"
                  style={{
                    padding: 14,
                    display: "grid",
                    gridTemplateColumns: "110px minmax(0, 1fr)",
                    gap: 14,
                    borderColor: blocked ? "var(--bad)" : "var(--rule-1)",
                  }}
                >
                  <div>
                    <video
                      src={row.signedUrl}
                      controls
                      preload="metadata"
                      style={{
                        width: "100%",
                        aspectRatio: "9/16",
                        background: "#000",
                        borderRadius: "var(--r-2)",
                        display: "block",
                      }}
                    />
                  </div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                      <label style={{ display: "inline-flex", alignItems: "center", gap: 8, color: "var(--paper)" }}>
                        <input
                          type="checkbox"
                          checked={row.selected}
                          disabled={blocked}
                          onChange={(e) => updateRow(row.index, { selected: e.target.checked })}
                        />
                        <span className="cf-mono-sm">
                          {String(row.index).padStart(2, "0")} · {SHORT_LABELS[row.label] || row.label || "Short"}
                        </span>
                      </label>
                      <span className="cf-caption">{formatDuration(row.duration)}</span>
                      {row.publishAtLocal && <span className="cf-caption">Programado desde sugerencia {row.offsetHours > 0 ? "+" : ""}{row.offsetHours}h</span>}
                    </div>

                    {blocked && (
                      <div className="cf-caption" style={{ color: "var(--bad)" }}>
                        {row.preflight?.error || "Short no elegible para YouTube Shorts"}
                      </div>
                    )}

                    <input
                      style={inputStyle}
                      maxLength={100}
                      value={row.title}
                      onChange={(e) => updateRow(row.index, { title: e.target.value })}
                    />
                    <textarea
                      style={{ ...inputStyle, minHeight: 110, resize: "vertical" }}
                      maxLength={5000}
                      value={row.description}
                      onChange={(e) => updateRow(row.index, { description: e.target.value })}
                    />
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 220px 180px", gap: 10 }}>
                      <textarea
                        style={{ ...inputStyle, minHeight: 52, resize: "vertical" }}
                        value={row.tags}
                        onChange={(e) => updateRow(row.index, { tags: e.target.value })}
                      />
                      <select
                        style={inputStyle}
                        value={row.publishAtLocal ? "private" : row.privacyStatus}
                        disabled={Boolean(row.publishAtLocal)}
                        onChange={(e) => updateRow(row.index, { privacyStatus: e.target.value })}
                      >
                        <option value="private">Privado</option>
                        <option value="unlisted">No listado</option>
                        <option value="public">Publico</option>
                      </select>
                      <input
                        style={inputStyle}
                        type="datetime-local"
                        value={row.publishAtLocal}
                        onChange={(e) => updateRow(row.index, { publishAtLocal: e.target.value })}
                      />
                    </div>
                  </div>
                </div>
              );
            })}

            {job && (
              <div className="cf-card" style={{ padding: 14 }}>
                <div className="cf-mono-sm" style={{ color: job.status === "error" ? "var(--bad)" : "var(--ok)" }}>
                  {String(job.status || "queued").toUpperCase()}
                </div>
                <div className="cf-body" style={{ marginTop: 8 }}>{job.step || "En proceso"}</div>
                {job.error && <div className="cf-caption" style={{ color: "var(--bad)", marginTop: 8 }}>{job.error}</div>}
                {job.warning && <div className="cf-caption" style={{ color: "var(--warn)", marginTop: 8 }}>{job.warning}</div>}
                {Array.isArray(job.items) && job.items.length > 0 && (
                  <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                    {job.items.map((item, idx) => (
                      <div key={`${item.index}-${idx}`} className="cf-caption">
                        Short {item.index}:{" "}
                        {item.youtubeStudioUrl ? (
                          <a href={item.youtubeStudioUrl} target="_blank" rel="noreferrer" style={{ color: "var(--ok)" }}>
                            abrir en Studio
                          </a>
                        ) : (
                          <span style={{ color: "var(--bad)" }}>{item.error || "pendiente"}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div className="cf-caption">
                {selectedRows.length} Short{selectedRows.length === 1 ? "" : "s"} seleccionado{selectedRows.length === 1 ? "" : "s"}. Prueba primero con 1 si quieres cuidar cuota.
              </div>
              <button
                className="cf-btn cf-btn--primary"
                onClick={submitPublish}
                disabled={loading || !channelId || selectedRows.length === 0 || selectedRows.some((row) => !row.title)}
              >
                <Icon name="uploadCloud" size={16} /> Subir Shorts
              </button>
            </div>
          </div>
        )}

        {loading && <div className="cf-mono-sm" style={{ marginTop: 16 }}>Preparando Shorts...</div>}
      </div>
    </div>
  );
}
