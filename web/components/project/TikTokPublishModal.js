"use client";

import { useEffect, useMemo, useState } from "react";
import Icon from "@/components/Icon";
import { authedFetch, getApiBase } from "@/lib/apiClient";

const TERMINAL_STATUSES = new Set(["completed", "failed", "needs_review"]);

function localDatetimeValue(date) {
  if (!date) return "";
  const pad = (n) => String(n).padStart(2, "0");
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toIsoOrEmpty(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString();
}

export default function TikTokPublishModal({ open, onClose, projectId, user }) {
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [accountId, setAccountId] = useState("");
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  const apiBase = getApiBase();
  const configured = preview?.configured !== false;
  const selectedAccount = useMemo(
    () => accounts.find((account) => account.accountId === accountId),
    [accounts, accountId],
  );

  useEffect(() => {
    if (!open || !user || !projectId) return undefined;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      setJob(null);
      try {
        const [previewRes, accountsRes] = await Promise.all([
          authedFetch(user, `${apiBase}/tiktok/publish/preview/${encodeURIComponent(projectId)}`),
          authedFetch(user, `${apiBase}/tiktok/accounts`),
        ]);
        const previewJson = await previewRes.json().catch(() => ({}));
        const accountsJson = await accountsRes.json().catch(() => ({}));
        if (!previewRes.ok) throw new Error(previewJson.detail || previewJson.error || "No se pudo preparar TikTok");
        if (!accountsRes.ok) throw new Error(accountsJson.detail || accountsJson.error || "No se pudieron cargar cuentas TikTok");
        if (cancelled) return;
        setPreview(previewJson);
        const nextAccounts = accountsJson.accounts || [];
        setAccounts(nextAccounts);
        setAccountId(nextAccounts[0]?.accountId || "");
        setCaption(previewJson.metadata?.caption || "");
        setHashtags((previewJson.metadata?.hashtags || []).join(" "));
        setScheduledAt("");
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [apiBase, open, projectId, user]);

  useEffect(() => {
    const activeJobId = job?.jobId || job?.id;
    if (!activeJobId || TERMINAL_STATUSES.has(job.status)) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const res = await authedFetch(user, `${apiBase}/tiktok/publish/jobs/${encodeURIComponent(activeJobId)}`);
        const json = await res.json().catch(() => ({}));
        if (res.ok) setJob(json);
      } catch {
        // polling best-effort
      }
    }, 3500);
    return () => window.clearInterval(timer);
  }, [apiBase, job?.id, job?.jobId, job?.status, user]);

  if (!open) return null;

  const connectTikTok = async () => {
    setError("");
    try {
      const returnTo = `/dashboard/project/${projectId}?publish=tiktok`;
      const res = await authedFetch(
        user,
        `${apiBase}/tiktok/oauth/start?returnTo=${encodeURIComponent(returnTo)}`,
      );
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || json.error || "No se pudo iniciar OAuth TikTok");
      window.location.href = json.authorizationUrl;
    } catch (err) {
      setError(err.message);
    }
  };

  const submit = async () => {
    if (!accountId) {
      setError("Conecta o elige una cuenta TikTok.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await authedFetch(user, `${apiBase}/tiktok/publish/schedule/${encodeURIComponent(projectId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accountId,
          caption,
          hashtags: hashtags.split(/\s+/).filter(Boolean),
          scheduledAt: toIsoOrEmpty(scheduledAt),
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || json.error || "No se pudo enviar a TikTok");
      setJob(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const isScheduled = Boolean(toIsoOrEmpty(scheduledAt));
  const jobStatus = job?.status || "";
  const readyForInbox = jobStatus === "completed" || jobStatus === "inbox_delivered";
  const needsReview = jobStatus === "needs_review" || readyForInbox;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(0,0,0,0.72)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 18,
      }}
    >
      <div
        className="cf-card"
        style={{
          width: "min(1040px, 100%)",
          maxHeight: "92vh",
          overflow: "auto",
          padding: "var(--s-6)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 22 }}>
          <div>
            <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 8 }}>
              TIKTOK INBOX
            </div>
            <h2 className="cf-h1" style={{ margin: 0 }}>
              Enviar con revisión segura
            </h2>
          </div>
          <button className="cf-btn cf-btn--ghost" onClick={onClose}>
            <Icon name="x" size={16} /> Cerrar
          </button>
        </div>

        {error && (
          <div className="cf-card" style={{ borderColor: "var(--bad)", padding: "var(--s-4)", marginBottom: 18, color: "var(--bad)" }}>
            {error}
          </div>
        )}

        {!configured && (
          <div className="cf-card" style={{ borderColor: "var(--warn)", padding: "var(--s-5)", marginBottom: 18 }}>
            <div className="cf-h3" style={{ marginBottom: 8 }}>Falta configurar OAuth de TikTok</div>
            <p className="cf-body" style={{ color: "var(--paper-dim)", margin: 0 }}>
              El backend ya tiene el flujo, pero faltan variables de entorno para conectar cuentas TikTok.
            </p>
          </div>
        )}

        {loading && !preview ? (
          <div className="cf-mono-sm">Preparando TikTok...</div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.2fr) minmax(280px, 0.8fr)",
              gap: "var(--s-5)",
            }}
          >
            <div style={{ display: "grid", gap: "var(--s-4)" }}>
              <label>
                <div className="cf-mono-sm" style={{ marginBottom: 8 }}>CUENTA</div>
                <select
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  className="cf-input"
                  style={{ width: "100%" }}
                >
                  {accounts.map((account) => (
                    <option key={account.accountId} value={account.accountId}>
                      {account.displayName}
                    </option>
                  ))}
                </select>
              </label>

              {!accounts.length && (
                <button className="cf-btn cf-btn--primary" onClick={connectTikTok} disabled={!configured}>
                  <Icon name="zap" size={16} /> Conectar TikTok
                </button>
              )}

              <label>
                <div className="cf-mono-sm" style={{ marginBottom: 8 }}>CAPTION</div>
                <textarea
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  className="cf-input"
                  rows={7}
                  maxLength={2200}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </label>

              <label>
                <div className="cf-mono-sm" style={{ marginBottom: 8 }}>HASHTAGS</div>
                <textarea
                  value={hashtags}
                  onChange={(e) => setHashtags(e.target.value)}
                  className="cf-input"
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </label>

              <label>
                <div className="cf-mono-sm" style={{ marginBottom: 8 }}>PROGRAMAR ENVÍO A INBOX</div>
                <input
                  type="datetime-local"
                  value={scheduledAt}
                  min={localDatetimeValue(new Date())}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  className="cf-input"
                  style={{ width: "100%" }}
                />
              </label>
            </div>

            <div style={{ display: "grid", gap: "var(--s-4)", alignContent: "start" }}>
              <div className="cf-card" style={{ padding: "var(--s-4)" }}>
                <div className="cf-mono-sm" style={{ marginBottom: 10 }}>PRECHECK</div>
                <div className="cf-caption">
                  {preview?.video?.eligible
                    ? `${preview.video.filename} · ${preview.video.durationMinutes} min · ${preview.video.width}x${preview.video.height}`
                    : preview?.video?.error || "Video no validado"}
                </div>
              </div>

              <div className="cf-card" style={{ padding: "var(--s-4)" }}>
                <div className="cf-mono-sm" style={{ marginBottom: 10 }}>MODO SEGURO</div>
                <p className="cf-body" style={{ color: "var(--paper-dim)", margin: 0 }}>
                  Se envía al Inbox de TikTok. Tú terminas la edición y publicación desde TikTok.
                </p>
              </div>

              {selectedAccount && (
                <div className="cf-card" style={{ padding: "var(--s-4)" }}>
                  <div className="cf-mono-sm" style={{ marginBottom: 10 }}>CUENTA CONECTADA</div>
                  <div>{selectedAccount.displayName}</div>
                </div>
              )}

              {job && (
                <div className="cf-card" style={{ padding: "var(--s-4)", borderColor: needsReview ? "var(--ok)" : "var(--warn)" }}>
                  <div className="cf-mono-sm" style={{ marginBottom: 10 }}>
                    {needsReview ? "REVISIÓN EN TIKTOK" : "JOB"}
                  </div>
                  <div className="cf-body" style={{ marginBottom: 8 }}>
                    {job.step || job.status}
                  </div>
                  {needsReview && (
                    <div className="cf-caption">
                      Abre TikTok en tu teléfono y revisa la notificación de inbox para terminar la publicación.
                    </div>
                  )}
                </div>
              )}

              <button
                className="cf-btn cf-btn--primary"
                onClick={submit}
                disabled={loading || !configured || !accounts.length || !preview?.video?.eligible}
                style={{ justifyContent: "center" }}
              >
                <Icon name="uploadCloud" size={16} />
                {loading ? "Enviando..." : isScheduled ? "Programar Inbox" : "Enviar a Inbox"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
