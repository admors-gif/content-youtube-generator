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

function humanizeYouTubeWarning(value) {
  const raw = String(value || "");
  const lower = raw.toLowerCase();
  if (!raw) return "";
  if (lower.includes("thumbnail") && (lower.includes("permission") || lower.includes("403") || lower.includes("forbidden"))) {
    return "El video sí se subió, pero YouTube no permitió aplicar la miniatura personalizada. Verifica el canal en YouTube Studio o súbela manualmente ahí.";
  }
  return raw;
}

function formatDuration(seconds) {
  const total = Number(seconds) || 0;
  if (total <= 0) return "";
  const minutes = Math.floor(total / 60);
  const remaining = Math.round(total % 60);
  return `${minutes}:${String(remaining).padStart(2, "0")} min`;
}

export default function YouTubePublishModal({ open, onClose, projectId, project, user }) {
  const [loading, setLoading] = useState(false);
  const [channels, setChannels] = useState([]);
  const [configured, setConfigured] = useState(null);
  const [missing, setMissing] = useState([]);
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState({
    channelId: "",
    title: "",
    description: "",
    tags: "",
    privacyStatus: "private",
    publishAtLocal: "",
    thumbnailIndex: 0,
  });
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
          authedFetch(user, `${apiBase}/youtube/publish/preview/${encodeURIComponent(projectId)}`),
          fetch(`${apiBase}/youtube/oauth/status`),
          authedFetch(user, `${apiBase}/youtube/channels`),
        ]);

        const previewData = await readJsonResponse(previewRes);
        const configData = await readJsonResponse(configRes);
        const channelsData = await readJsonResponse(channelsRes);
        if (cancelled) return;

        if (!previewRes.ok) throw new Error(previewData.error || previewData.detail || "No se pudo cargar metadata");

        const isConfigured = Boolean(configData.configured ?? channelsData.configured);
        setPreview(previewData);
        setConfigured(isConfigured);
        setMissing(configData.missing || channelsData.missing || []);
        const list = channelsRes.ok ? channelsData.channels || [] : [];
        setChannels(list);
        if (isConfigured && !channelsRes.ok) {
          const detail = channelsData.error || channelsData.detail;
          setError(
            typeof detail === "string"
              ? detail
              : "No se pudieron cargar canales conectados. Puedes intentar conectar YouTube.",
          );
        }
        setForm((prev) => ({
          ...prev,
          channelId: prev.channelId || list[0]?.channelId || "",
          title: prev.title || previewData.metadata?.title || project?.title || "",
          description: prev.description || previewData.metadata?.description || "",
          tags: prev.tags || previewData.metadata?.tagsCsv || "",
          privacyStatus: "private",
          thumbnailIndex: 0,
        }));
      } catch (err) {
        if (!cancelled) setError(err.message || "No se pudo preparar publicación");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [open, user, projectId, apiBase, project?.title]);

  useEffect(() => {
    if (!job?.jobId || ["completed", "error"].includes(job.status)) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const res = await authedFetch(user, `${apiBase}/youtube/publish/jobs/${encodeURIComponent(job.jobId)}`);
        const data = await res.json();
        if (!cancelled && res.ok) setJob((prev) => ({ ...prev, ...data, jobId: prev.jobId }));
      } catch {
        // Polling is best-effort; the job keeps running server-side.
      }
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [job?.jobId, job?.status, apiBase, user]);

  const selectedThumbnail = useMemo(() => {
    const thumbs = preview?.thumbnails || [];
    return thumbs[Math.max(0, Math.min(Number(form.thumbnailIndex) || 0, thumbs.length - 1))];
  }, [preview?.thumbnails, form.thumbnailIndex]);
  const selectedChannel = useMemo(
    () => channels.find((channel) => channel.channelId === form.channelId),
    [channels, form.channelId],
  );
  const videoDurationSeconds = Number(preview?.video?.durationSeconds || 0);
  const longUploadsStatus = String(selectedChannel?.longUploadsStatus || "").toLowerCase();
  const isLongVideo = Boolean(preview?.video?.isLongerThanDefaultLimit);
  const longUploadBlocked = isLongVideo && longUploadsStatus && longUploadsStatus !== "allowed";
  const longUploadWarning = isLongVideo && longUploadsStatus !== "allowed";

  if (!open) return null;

  const connectYouTube = async () => {
    setError("");
    try {
      const returnTo = `/dashboard/project/${projectId}`;
      const res = await authedFetch(user, `${apiBase}/youtube/oauth/start?returnTo=${encodeURIComponent(returnTo)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "YouTube no está configurado");
      window.location.href = data.authorizationUrl;
    } catch (err) {
      setError(err.message || "No se pudo conectar YouTube");
    }
  };

  const submitPublish = async () => {
    setError("");
    setLoading(true);
    try {
      const publishAt = form.publishAtLocal
        ? new Date(form.publishAtLocal).toISOString()
        : "";
      const res = await authedFetch(user, `${apiBase}/youtube/publish/${encodeURIComponent(projectId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channelId: form.channelId,
          title: form.title,
          description: form.description,
          tags: form.tags,
          privacyStatus: publishAt ? "private" : form.privacyStatus,
          publishAt,
          thumbnailIndex: Number(form.thumbnailIndex) || 0,
          categoryId: "22",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "No se pudo iniciar publicación");
      setJob({ ...data, jobId: data.jobId });
    } catch (err) {
      setError(err.message || "No se pudo publicar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Publicar en YouTube"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.72)",
        zIndex: 80,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        className="cf-card"
        style={{
          width: "min(960px, 100%)",
          maxHeight: "92vh",
          overflow: "auto",
          padding: 24,
          boxShadow: "var(--shadow-2)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
          <div>
            <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 8 }}>
              YouTube Studio
            </div>
            <h2 className="cf-h2" style={{ margin: 0 }}>
              Publicar con revisión segura
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

        {loading && configured === null && (
          <div className="cf-card" style={{ padding: 18, marginBottom: 16 }}>
            <div className="cf-h4" style={{ marginBottom: 8 }}>Preparando conexión</div>
            <div className="cf-body">
              Validando proyecto, canal conectado y permisos de publicación.
            </div>
          </div>
        )}

        {!loading && configured === false && (
          <div className="cf-card" style={{ padding: 18, marginBottom: 16, borderColor: "var(--warn)" }}>
            <div className="cf-h4" style={{ marginBottom: 8 }}>Falta configurar OAuth de YouTube</div>
            <div className="cf-body" style={{ marginBottom: 12 }}>
              El backend ya tiene la integración, pero faltan variables de entorno para conectar canales.
            </div>
            <div className="cf-mono-sm">Faltantes: {missing.join(", ") || "configuración OAuth"}</div>
          </div>
        )}

        {configured === true && channels.length === 0 && (
          <div className="cf-card" style={{ padding: 18, marginBottom: 16 }}>
            <div className="cf-h4" style={{ marginBottom: 8 }}>Conecta tu canal</div>
            <div className="cf-body" style={{ marginBottom: 16 }}>
              Content Factory subirá el video como privado o programado. Nunca necesita tu contraseña.
            </div>
            <button className="cf-btn cf-btn--primary" onClick={connectYouTube} disabled={loading}>
              <Icon name="uploadCloud" size={16} /> Conectar YouTube
            </button>
          </div>
        )}

        {configured === true && channels.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 280px", gap: 18 }}>
            <div style={{ display: "grid", gap: 14 }}>
              {longUploadWarning && (
                <div className="cf-card" style={{ padding: 14, borderColor: "var(--warn)" }}>
                  <div className="cf-h4" style={{ marginBottom: 8 }}>Verifica el canal para videos largos</div>
                  <div className="cf-body">
                    Este video dura {formatDuration(videoDurationSeconds) || "más de 15 minutos"}. YouTube suele rechazar
                    videos de más de 15 minutos si el canal aún no tiene subidas largas habilitadas.
                  </div>
                  <div className="cf-caption" style={{ marginTop: 10 }}>
                    Estado detectado: {longUploadsStatus || "no confirmado"}.{" "}
                    <a href="https://www.youtube.com/verify" target="_blank" rel="noreferrer" style={{ color: "var(--warn)" }}>
                      Verificar canal
                    </a>
                  </div>
                </div>
              )}

              <div>
                <FieldLabel>Canal</FieldLabel>
                <select
                  style={inputStyle}
                  value={form.channelId}
                  onChange={(e) => setForm((prev) => ({ ...prev, channelId: e.target.value }))}
                >
                  {channels.map((channel) => (
                    <option key={channel.channelId} value={channel.channelId}>
                      {channel.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <FieldLabel>Título</FieldLabel>
                <input
                  style={inputStyle}
                  maxLength={100}
                  value={form.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                />
              </div>

              <div>
                <FieldLabel>Descripción</FieldLabel>
                <textarea
                  style={{ ...inputStyle, minHeight: 170, resize: "vertical" }}
                  maxLength={5000}
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                />
              </div>

              <div>
                <FieldLabel>Tags</FieldLabel>
                <textarea
                  style={{ ...inputStyle, minHeight: 84, resize: "vertical" }}
                  value={form.tags}
                  onChange={(e) => setForm((prev) => ({ ...prev, tags: e.target.value }))}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <FieldLabel>Privacidad</FieldLabel>
                  <select
                    style={inputStyle}
                    value={form.publishAtLocal ? "private" : form.privacyStatus}
                    disabled={Boolean(form.publishAtLocal)}
                    onChange={(e) => setForm((prev) => ({ ...prev, privacyStatus: e.target.value }))}
                  >
                    <option value="private">Privado</option>
                    <option value="unlisted">No listado</option>
                  </select>
                </div>
                <div>
                  <FieldLabel>Programar</FieldLabel>
                  <input
                    style={inputStyle}
                    type="datetime-local"
                    value={form.publishAtLocal}
                    onChange={(e) => setForm((prev) => ({ ...prev, publishAtLocal: e.target.value }))}
                  />
                </div>
              </div>
            </div>

            <div>
              <FieldLabel>Miniatura</FieldLabel>
              {selectedThumbnail?.url && (
                <div
                  role="img"
                  aria-label="Miniatura seleccionada"
                  style={{
                    width: "100%",
                    aspectRatio: "16 / 9",
                    backgroundImage: `url(${selectedThumbnail.url})`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                    borderRadius: "var(--r-2)",
                    border: "1px solid var(--rule-1)",
                  }}
                />
              )}
              {(preview?.thumbnails || []).length > 1 && (
                <select
                  style={{ ...inputStyle, marginTop: 10 }}
                  value={form.thumbnailIndex}
                  onChange={(e) => setForm((prev) => ({ ...prev, thumbnailIndex: e.target.value }))}
                >
                  {preview.thumbnails.map((thumb, index) => (
                    <option key={thumb.url || index} value={index}>
                      Variante {index + 1}
                    </option>
                  ))}
                </select>
              )}

              {job && (
                <div className="cf-card" style={{ padding: 14, marginTop: 14 }}>
                  <div className="cf-mono-sm" style={{ color: job.status === "error" ? "var(--bad)" : "var(--ok)" }}>
                    {String(job.status || "queued").toUpperCase()}
                  </div>
                  <div className="cf-body" style={{ marginTop: 8 }}>{job.step || "En proceso"}</div>
                  {job.error && (
                    <div className="cf-caption" style={{ marginTop: 8, color: "var(--bad)" }}>
                      {job.error}
                    </div>
                  )}
                  {job.warning && (
                    <div className="cf-caption" style={{ marginTop: 8, color: "var(--warn)" }}>
                      {humanizeYouTubeWarning(job.warning)}
                    </div>
                  )}
                  {job.youtubeStudioUrl && (
                    <a className="cf-btn cf-btn--secondary" href={job.youtubeStudioUrl} target="_blank" rel="noreferrer" style={{ marginTop: 12 }}>
                      Abrir en Studio
                    </a>
                  )}
                </div>
              )}

              <button
                className="cf-btn cf-btn--primary"
                style={{ width: "100%", justifyContent: "center", marginTop: 14 }}
                onClick={submitPublish}
                disabled={loading || !form.channelId || !form.title || longUploadBlocked}
              >
                <Icon name="uploadCloud" size={16} /> {longUploadBlocked ? "Verifica canal" : "Subir como privado"}
              </button>
              <div className="cf-caption" style={{ marginTop: 10 }}>
                La publicación inicia privada para revisar antes de hacerla pública.
              </div>
            </div>
          </div>
        )}

        {loading && <div className="cf-mono-sm" style={{ marginTop: 16 }}>Preparando conexión...</div>}
      </div>
    </div>
  );
}
