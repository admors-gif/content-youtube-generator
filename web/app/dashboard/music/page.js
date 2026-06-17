"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Icon from "@/components/Icon";
import { isAdminUser } from "@/lib/admin";
import { authedFetch, getApiBase } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";

const MUSIC_STUDIO_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_MUSIC_STUDIO_ENABLED !== "false";

const DEFAULT_FORM = {
  intention: "disciplina",
  style: "latin_trap_anthem",
  theme: "Hoy no negocio conmigo",
  targetUse: "entrenar fuerza",
  energy: "alta, elegante, feroz pero limpia",
  vocalPerspective: "primera persona, presente, identidad ganadora",
  personalAngle:
    "Una cancion para escuchar entrenando, recordar que ya no negocio mi disciplina y volver a mi vision cuando aparezca cansancio.",
  mustInclude:
    "frases memorables, hook repetible, imagenes de amanecer, hierro, enfoque, promesa conmigo mismo",
  mustAvoid:
    "promesas medicas, bajar de peso como castigo, imitacion de artistas reales, lenguaje vulgar gratuito",
};

const emptyPresets = {
  intentions: [],
  styles: [],
  targetUses: [],
  model: "",
};

function pillStyle(tone = "neutral") {
  const tones = {
    neutral: { color: "var(--paper-dim)", border: "var(--rule-1)", bg: "var(--ink-2)" },
    ember: { color: "var(--ember)", border: "rgba(224,83,61,0.42)", bg: "rgba(224,83,61,0.1)" },
    ok: { color: "var(--ok)", border: "rgba(116,201,154,0.36)", bg: "rgba(116,201,154,0.1)" },
  };
  const meta = tones[tone] || tones.neutral;
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    minHeight: 30,
    padding: "6px 10px",
    borderRadius: 999,
    border: `1px solid ${meta.border}`,
    background: meta.bg,
    color: meta.color,
    font: "var(--t-mono-sm)",
    textTransform: "uppercase",
  };
}

function fieldBase() {
  return {
    width: "100%",
    border: "1px solid var(--rule-1)",
    background: "var(--ink-2)",
    color: "var(--paper)",
    borderRadius: "var(--r-2)",
    padding: "14px 14px",
    font: "var(--t-body)",
    outline: "none",
    minHeight: 50,
  };
}

function labelStyle() {
  return {
    display: "block",
    marginBottom: 8,
    color: "var(--paper-mute)",
    font: "var(--t-mono-sm)",
    textTransform: "uppercase",
  };
}

function Field({ label, value, onChange, placeholder }) {
  return (
    <label style={{ display: "block" }}>
      <span style={labelStyle()}>{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        style={fieldBase()}
      />
    </label>
  );
}

function TextArea({ label, value, onChange, placeholder, rows = 4 }) {
  return (
    <label style={{ display: "block" }}>
      <span style={labelStyle()}>{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={rows}
        style={{
          ...fieldBase(),
          resize: "vertical",
          lineHeight: 1.55,
        }}
      />
    </label>
  );
}

function SelectField({ label, value, onChange, options, getLabel = (item) => item.label || item.name || item.id }) {
  return (
    <label style={{ display: "block" }}>
      <span style={labelStyle()}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={fieldBase()}>
        {options.map((item) => (
          <option key={item.id || item.value || item} value={item.id || item.value || item}>
            {getLabel(item)}
          </option>
        ))}
      </select>
    </label>
  );
}

function Notice({ error, notice }) {
  if (!error && !notice) return null;
  return (
    <div
      className="cf-card"
      style={{
        padding: "var(--s-4)",
        borderColor: error ? "var(--bad)" : "var(--ok)",
        color: error ? "var(--bad)" : "var(--ok)",
        marginBottom: "var(--s-5)",
      }}
    >
      {error || notice}
    </div>
  );
}

function CopyButton({ label, value, onCopy, icon = "copy" }) {
  return (
    <button
      type="button"
      className="cf-button"
      onClick={() => onCopy(label, value)}
      disabled={!value}
      style={{
        minHeight: 44,
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        color: "var(--paper)",
        opacity: value ? 1 : 0.5,
      }}
    >
      <Icon name={icon} size={16} />
      {label}
    </button>
  );
}

function Section({ label, title, children, actions }) {
  return (
    <section className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          alignItems: "flex-start",
          marginBottom: "var(--s-4)",
        }}
      >
        <div>
          <div className="cf-mono-sm" style={{ marginBottom: 8 }}>{label}</div>
          {title && (
            <h2
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(28px, 4vw, 48px)",
                lineHeight: 1,
                margin: 0,
              }}
            >
              {title}
            </h2>
          )}
        </div>
        {actions && <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>{actions}</div>}
      </div>
      {children}
    </section>
  );
}

function formatDate(value) {
  if (!value) return "Sin fecha";
  try {
    return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  } catch {
    return String(value);
  }
}

function safeText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    const text = value.map((item) => safeText(item)).filter(Boolean).join(", ");
    return text || fallback;
  }
  if (typeof value === "object") {
    return safeText(
      value.prompt ||
        value.visualPrompt ||
        value.description ||
        value.title ||
        value.section ||
        value.textOverlay ||
        value.text ||
        value.label,
      fallback
    );
  }
  return fallback;
}

function packageText(pkg, key) {
  if (!pkg) return "";
  if (key === "lyrics") return safeText(pkg.lyrics);
  if (key === "suno") return safeText(pkg.sunoPrompt);
  if (key === "sunoAlt") return safeText(pkg.sunoPromptAlt);
  if (key === "negative") return safeText(pkg.negativePrompt);
  if (key === "youtube") {
    const youtube = pkg.youtube || {};
    return [
      safeText(youtube.title),
      "",
      safeText(youtube.description),
      "",
      Array.isArray(youtube.hashtags) ? youtube.hashtags.map((tag) => safeText(tag)).filter(Boolean).join(" ") : "",
      Array.isArray(youtube.tags) ? `Tags: ${youtube.tags.map((tag) => safeText(tag)).filter(Boolean).join(", ")}` : "",
      youtube.thumbnailText ? `Miniatura: ${safeText(youtube.thumbnailText)}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

function TrackList({ tracks, selectedId, onSelect }) {
  if (!tracks.length) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-4)", color: "var(--paper-mute)" }}>
        Todavia no hay canciones guardadas. Genera la primera y quedara aqui como biblioteca.
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {tracks.map((track) => {
        const pkg = track.package || {};
        const render = track.render || {};
        const statusLabel =
          render.status === "completed"
            ? "video listo"
            : render.status === "running" || render.status === "queued"
              ? "render"
              : track.audio?.url
                ? "audio"
                : track.status || "lyrics";
        const active = selectedId && selectedId === track.trackId;
        return (
          <button
            type="button"
            key={track.trackId}
            onClick={() => onSelect(track)}
            className="cf-card"
            style={{
              padding: "var(--s-4)",
              textAlign: "left",
              borderColor: active ? "var(--ember)" : "var(--rule-1)",
              cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <strong style={{ display: "block", color: "var(--paper)", fontSize: 16 }}>{pkg.title || "Sin titulo"}</strong>
                <span className="cf-caption">{pkg.subtitle || track.status || "lyrics_ready"}</span>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                <span style={pillStyle(render.status === "completed" ? "ok" : "neutral")}>{statusLabel}</span>
                <span style={pillStyle("neutral")}>{pkg.bpm || "--"} bpm</span>
              </div>
            </div>
            <div className="cf-caption" style={{ marginTop: 8 }}>
              {formatDate(track.updatedAt || track.createdAt)}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ScoreBar({ label, value }) {
  const safeValue = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 6 }}>
        <span className="cf-mono-sm">{label}</span>
        <span className="cf-mono-sm" style={{ color: "var(--paper)" }}>{Math.round(safeValue)}</span>
      </div>
      <div
        style={{
          height: 7,
          borderRadius: 999,
          overflow: "hidden",
          background: "var(--ink-2)",
          border: "1px solid var(--rule-1)",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${safeValue}%`,
            background: safeValue >= 78 ? "var(--ok)" : safeValue >= 62 ? "var(--ember)" : "var(--bad)",
          }}
        />
      </div>
    </div>
  );
}

function LyricScoreCard({ score }) {
  if (!score || typeof score !== "object") return null;
  const dimensions = score.dimensions || {};
  const entries = [
    ["Melodia", dimensions.melodia],
    ["Lirica", dimensions.lirica],
    ["Ritmo", dimensions.ritmo],
    ["Viralidad", dimensions.viralidad],
    ["Musica", dimensions.musica],
    ["Coherencia", dimensions.coherencia],
    ["Impacto", dimensions.impacto],
    ["Poder", dimensions.poder],
  ];
  return (
    <Section
      label="Calificador"
      title="Score de letra"
      actions={<span style={pillStyle(Number(score.total || 0) >= 78 ? "ok" : "ember")}>{Math.round(Number(score.total || 0))}/100</span>}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "var(--s-4)",
        }}
      >
        {entries.map(([label, value]) => (
          <ScoreBar key={label} label={label} value={value} />
        ))}
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "var(--s-4)",
          marginTop: "var(--s-4)",
        }}
      >
        <div>
          <div className="cf-mono-sm">Fortalezas</div>
          <ul style={{ color: "var(--paper-dim)", lineHeight: 1.65, paddingLeft: 18 }}>
            {(score.strengths || ["Calificacion generada sin costo extra."]).map((item, index) => (
              <li key={`${safeText(item)}-${index}`}>{safeText(item)}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="cf-mono-sm">Mejoras sugeridas</div>
          <ul style={{ color: "var(--paper-mute)", lineHeight: 1.65, paddingLeft: 18 }}>
            {(score.suggestions || score.risks || ["Lista para probar en Suno."]).map((item, index) => (
              <li key={`${safeText(item)}-${index}`}>{safeText(item)}</li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  );
}

function AudioVersionList({ versions, activeId, onActivate, activating }) {
  const items = Array.isArray(versions) ? versions : [];
  if (!items.length) {
    return <p className="cf-caption" style={{ marginTop: "var(--s-4)" }}>Todavia no hay versiones de audio subidas.</p>;
  }
  return (
    <div style={{ display: "grid", gap: 10, marginTop: "var(--s-4)" }}>
      {items.map((version, index) => {
        const versionId = safeText(version.versionId || `take_${index + 1}`);
        const active = activeId ? activeId === versionId : version.isActive;
        return (
          <div
            key={`${versionId}-${index}`}
            className="cf-card"
            style={{
              padding: "var(--s-4)",
              borderColor: active ? "var(--ok)" : "var(--rule-1)",
              background: active ? "rgba(116,201,154,0.07)" : "var(--ink-1)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
              <div>
                <strong style={{ color: "var(--paper)" }}>{safeText(version.label, `Toma ${index + 1}`)}</strong>
                <div className="cf-caption">
                  {safeText(version.promptKind, "suno")} · {safeText(version.originalFileName || version.fileName, "audio")}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {active && <span style={pillStyle("ok")}>activa</span>}
                <button
                  type="button"
                  className="cf-button"
                  onClick={() => onActivate(versionId)}
                  disabled={active || activating}
                  style={{ minHeight: 40, color: "var(--paper)" }}
                >
                  <Icon name="check" size={16} />
                  Usar esta version
                </button>
              </div>
            </div>
            {version.url && <audio controls src={version.url} style={{ width: "100%", marginTop: 12 }} />}
          </div>
        );
      })}
    </div>
  );
}

function VisualSceneList({ scenes }) {
  const items = Array.isArray(scenes) ? scenes : [];
  if (!items.length) return <p className="cf-caption">El paquete aun no trae escenas visuales.</p>;
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {items.map((scene, index) => {
        const title = safeText(scene?.title || scene?.section, "Escena");
        const prompt = safeText(scene?.prompt || scene?.visualPrompt || scene?.description || scene, "Direccion visual pendiente.");
        const overlay = safeText(scene?.textOverlay);
        return (
          <div
            key={`${title}-${index}`}
            style={{
              border: "1px solid var(--rule-1)",
              borderRadius: "var(--r-2)",
              padding: "var(--s-4)",
              background: "var(--ink-2)",
            }}
          >
            <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 6 }}>
              {String(index + 1).padStart(2, "0")} · {title}
            </div>
            <div style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{prompt}</div>
            {overlay && (
              <div style={{ marginTop: 10 }}>
                <span style={pillStyle("neutral")}>{overlay}</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function MusicStudioPage() {
  const { user, profile } = useAuth();
  const admin = isAdminUser(user, profile);
  const [presets, setPresets] = useState(emptyPresets);
  const [tracks, setTracks] = useState([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [current, setCurrent] = useState(null);
  const [currentId, setCurrentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadingAudio, setUploadingAudio] = useState(false);
  const [producingVideo, setProducingVideo] = useState(false);
  const [activatingAudio, setActivatingAudio] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [audioVersionLabel, setAudioVersionLabel] = useState("");
  const [audioPromptKind, setAudioPromptKind] = useState("original");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [copied, setCopied] = useState("");

  const packageData = current?.package || null;
  const audioData = current?.audio || null;
  const audioVersions = current?.audioVersions || [];
  const activeAudioVersionId = current?.activeAudioVersionId || audioData?.versionId || "";
  const renderData = current?.render || null;
  const lyricScore = packageData?.lyricScore || null;

  const intentionMeta = useMemo(
    () => (presets.intentions || []).find((item) => item.id === form.intention),
    [form.intention, presets.intentions]
  );
  const styleMeta = useMemo(
    () => (presets.styles || []).find((item) => item.id === form.style),
    [form.style, presets.styles]
  );

  const updateForm = useCallback((key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const apiFetch = useCallback(
    async (path, options = {}) => {
      const response = await authedFetch(user, `${getApiBase()}${path}`, options);
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data?.ok === false) {
        throw new Error(data?.detail || data?.error || `Error ${response.status}`);
      }
      return data;
    },
    [user]
  );

  const loadTracks = useCallback(async () => {
    if (!user || !admin || !MUSIC_STUDIO_ENABLED) return;
    try {
      const data = await apiFetch("/music/tracks?limit=24");
      setTracks(data.items || []);
    } catch (exc) {
      setError(exc.message);
    }
  }, [admin, apiFetch, user]);

  const refreshCurrentTrack = useCallback(async () => {
    if (!currentId) return null;
    const data = await apiFetch(`/music/tracks/${encodeURIComponent(currentId)}`);
    if (data.track) {
      setCurrent(data.track);
      setCurrentId(data.track.trackId || currentId);
    }
    return data.track || null;
  }, [apiFetch, currentId]);

  useEffect(() => {
    if (!user || !admin || !MUSIC_STUDIO_ENABLED) return undefined;
    let cancelled = false;
    Promise.all([apiFetch("/music/presets"), apiFetch("/music/tracks?limit=24")])
      .then(([presetData, trackData]) => {
        if (cancelled) return;
        setPresets({
          intentions: presetData.intentions || [],
          styles: presetData.styles || [],
          targetUses: presetData.targetUses || [],
          model: presetData.model || "",
        });
        setTracks(trackData.items || []);
      })
      .catch((exc) => {
        if (!cancelled) setError(exc.message);
      });
    return () => {
      cancelled = true;
    };
  }, [admin, apiFetch, user]);

  useEffect(() => {
    const status = renderData?.status;
    if (!currentId || !["queued", "running"].includes(status)) return undefined;
    const timer = setInterval(() => {
      refreshCurrentTrack()
        .then((track) => {
          if (track?.render?.status === "completed") {
            setNotice("Video musical finalizado en el VPS.");
            loadTracks();
          }
          if (track?.render?.status === "failed") {
            setError(track.render.error || "El render musical fallo.");
            loadTracks();
          }
        })
        .catch((exc) => setError(exc.message));
    }, 7000);
    return () => clearInterval(timer);
  }, [currentId, loadTracks, refreshCurrentTrack, renderData?.status]);

  async function generatePackage() {
    setError("");
    setNotice("");
    setCopied("");
    setLoading(true);
    try {
      const data = await apiFetch("/music/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, save: true }),
      });
      const next = {
        trackId: data.trackId,
        package: data.package,
        status: "lyrics_ready",
        model: data.model,
        generationMode: data.generationMode,
      };
      setCurrent(next);
      setCurrentId(data.trackId || "");
      setNotice("Paquete premium listo. Copia la letra y el prompt a Suno; no se gasto credito interno.");
      await loadTracks();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setLoading(false);
    }
  }

  async function copyText(label, value) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      setNotice(`${label} copiado al portapapeles.`);
    } catch {
      setError("No pude copiar automaticamente. Selecciona el texto manualmente.");
    }
  }

  async function uploadAudio() {
    if (!currentId) {
      setError("Primero genera o selecciona un track.");
      return;
    }
    if (!audioFile) {
      setError("Selecciona el archivo de audio descargado de Suno.");
      return;
    }
    setError("");
    setNotice("");
    setUploadingAudio(true);
    try {
      const body = new FormData();
      body.append("file", audioFile);
      body.append("label", audioVersionLabel || `Toma ${audioVersions.length + 1}`);
      body.append("promptKind", audioPromptKind || "suno");
      const data = await apiFetch(`/music/tracks/${encodeURIComponent(currentId)}/audio`, {
        method: "POST",
        body,
      });
      setCurrent(data.track);
      setCurrentId(data.track?.trackId || currentId);
      setAudioFile(null);
      setAudioVersionLabel("");
      setNotice("Version de audio subida y seleccionada. Ya puedes producir el video musical completo en el VPS.");
      await loadTracks();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setUploadingAudio(false);
    }
  }

  async function produceVideo() {
    if (!currentId) {
      setError("Primero genera o selecciona un track.");
      return;
    }
    if (!audioData?.url && !audioData?.storagePath) {
      setError("Primero sube el audio final descargado de Suno.");
      return;
    }
    setError("");
    setNotice("");
    setProducingVideo(true);
    try {
      const data = await apiFetch(`/music/tracks/${encodeURIComponent(currentId)}/produce`, {
        method: "POST",
      });
      if (data.track) {
        setCurrent(data.track);
        setCurrentId(data.track.trackId || currentId);
      }
      if (data.alreadyReady) {
        setNotice("Este track ya tiene video final listo.");
      } else {
        setNotice("Render musical enviado al VPS. Puedes cerrar esta pantalla; el worker seguira produciendo.");
      }
      await loadTracks();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setProducingVideo(false);
    }
  }

  async function activateAudioVersion(versionId) {
    if (!currentId || !versionId) return;
    setError("");
    setNotice("");
    setActivatingAudio(true);
    try {
      const data = await apiFetch(`/music/tracks/${encodeURIComponent(currentId)}/audio/${encodeURIComponent(versionId)}/activate`, {
        method: "POST",
      });
      if (data.track) {
        setCurrent(data.track);
        setCurrentId(data.track.trackId || currentId);
      }
      setNotice("Version de audio seleccionada. El siguiente render usara esta toma.");
      await loadTracks();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setActivatingAudio(false);
    }
  }

  function selectTrack(track) {
    setCurrent(track);
    setCurrentId(track.trackId || "");
    setNotice("");
    setError("");
  }

  if (!MUSIC_STUDIO_ENABLED) {
    return (
      <main className="cf-page">
        <Section label="Music Studio" title="Desactivado">
          <p className="cf-caption">Activa NEXT_PUBLIC_CONTENT_FACTORY_MUSIC_STUDIO_ENABLED para usar este modulo.</p>
        </Section>
      </main>
    );
  }

  if (!admin) {
    return (
      <main className="cf-page">
        <Section label="Music Studio" title="Solo admin">
          <p className="cf-caption">Este laboratorio musical esta reservado para administradores en v1.</p>
        </Section>
      </main>
    );
  }

  return (
    <main className="cf-page">
      <header style={{ marginBottom: "var(--s-6)" }}>
        <div className="cf-kicker">POWER MUSIC</div>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(48px, 8vw, 92px)",
            lineHeight: 0.95,
            margin: "10px 0 12px",
          }}
        >
          Música de poder
        </h1>
        <p style={{ font: "var(--t-lead)", color: "var(--paper-dim)", maxWidth: 980 }}>
          Letras, hooks, prompts Suno y direccion visual para canciones de disciplina, identidad y energia.
        </p>
      </header>

      <Notice error={error} notice={notice || (copied ? `${copied} listo para pegar.` : "")} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "var(--s-5)",
          alignItems: "start",
        }}
      >
        <Section
          label="Contrato creativo"
          title="Generar paquete"
          actions={<span style={pillStyle("ok")}>0 creditos internos</span>}
        >
          <div style={{ display: "grid", gap: "var(--s-4)" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--s-4)" }}>
              <SelectField
                label="Intencion"
                value={form.intention}
                onChange={(value) => updateForm("intention", value)}
                options={presets.intentions.length ? presets.intentions : [{ id: DEFAULT_FORM.intention, label: "Disciplina" }]}
              />
              <SelectField
                label="Estilo"
                value={form.style}
                onChange={(value) => updateForm("style", value)}
                options={presets.styles.length ? presets.styles : [{ id: DEFAULT_FORM.style, label: "Latin Trap Anthem" }]}
              />
            </div>

            <Field label="Tema central" value={form.theme} onChange={(value) => updateForm("theme", value)} />

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--s-4)" }}>
              <SelectField
                label="Uso"
                value={form.targetUse}
                onChange={(value) => updateForm("targetUse", value)}
                options={presets.targetUses.length ? presets.targetUses : [DEFAULT_FORM.targetUse]}
                getLabel={(item) => item.label || item}
              />
              <Field label="Energia" value={form.energy} onChange={(value) => updateForm("energy", value)} />
            </div>

            <Field
              label="Perspectiva vocal"
              value={form.vocalPerspective}
              onChange={(value) => updateForm("vocalPerspective", value)}
            />
            <TextArea label="Angulo personal" value={form.personalAngle} onChange={(value) => updateForm("personalAngle", value)} rows={4} />
            <TextArea label="Debe incluir" value={form.mustInclude} onChange={(value) => updateForm("mustInclude", value)} rows={3} />
            <TextArea label="Evitar" value={form.mustAvoid} onChange={(value) => updateForm("mustAvoid", value)} rows={3} />

            <button
              type="button"
              className="cf-button cf-button--primary"
              onClick={generatePackage}
              disabled={loading}
              style={{ minHeight: 58, justifyContent: "center", fontSize: 18 }}
            >
              <Icon name={loading ? "refresh" : "flame"} size={20} />
              {loading ? "Generando paquete..." : "Generar paquete premium"}
            </button>
          </div>
        </Section>

        <div style={{ display: "grid", gap: "var(--s-5)" }}>
          <Section label="Pipeline" title="Suno primero">
            <div style={{ display: "grid", gap: 12 }}>
              {[
                ["01", "Genera letra y prompt maestro en Content Factory."],
                ["02", "Copia letra + prompt en Suno y crea la cancion final."],
                ["03", "Descarga audio de Suno y subelo al track aqui mismo."],
                ["04", "Produce en el VPS el video, miniatura, portada y metadata final."],
              ].map(([step, text]) => (
                <div key={step} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <span style={pillStyle("ember")}>{step}</span>
                  <p style={{ margin: 0, color: "var(--paper-dim)", lineHeight: 1.55 }}>{text}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section label="Biblioteca" title="Tracks recientes">
            <TrackList tracks={tracks} selectedId={currentId} onSelect={selectTrack} />
          </Section>
        </div>
      </div>

      {intentionMeta || styleMeta ? (
        <section
          className="cf-card"
          style={{
            marginTop: "var(--s-5)",
            padding: "var(--s-5)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "var(--s-4)",
          }}
        >
          <div>
            <div className="cf-mono-sm">Intencion activa</div>
            <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{intentionMeta?.description || "Define el cambio emocional buscado."}</p>
          </div>
          <div>
            <div className="cf-mono-sm">ADN sonoro</div>
            <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{styleMeta?.description || "Define ritmo, energia y textura musical."}</p>
          </div>
          <div>
            <div className="cf-mono-sm">Modelo</div>
            <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{presets.model || "Configurado en backend"}</p>
          </div>
        </section>
      ) : null}

      {packageData && (
        <div style={{ display: "grid", gap: "var(--s-5)", marginTop: "var(--s-6)" }}>
          <Section
            label="Paquete listo"
            title={safeText(packageData.title, "Cancion generada")}
            actions={
              <>
                {lyricScore?.total && <span style={pillStyle(Number(lyricScore.total) >= 78 ? "ok" : "ember")}>score {Math.round(Number(lyricScore.total))}</span>}
                <span style={pillStyle("ember")}>{safeText(packageData.bpm, "--")} bpm</span>
                <span style={pillStyle("neutral")}>{safeText(packageData.energy, "energia")}</span>
              </>
            }
          >
            <p style={{ font: "var(--t-lead)", color: "var(--paper-dim)", marginTop: 0 }}>
              {safeText(packageData.subtitle || packageData.mainHook, "Lista para llevar a Suno.")}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: "var(--s-4)" }}>
              <CopyButton label="Copiar letra" value={packageText(packageData, "lyrics")} onCopy={copyText} />
              <CopyButton label="Copiar prompt Suno" value={packageText(packageData, "suno")} onCopy={copyText} icon="zap" />
              <CopyButton label="Prompt alterno" value={packageText(packageData, "sunoAlt")} onCopy={copyText} icon="copy" />
              <CopyButton label="YouTube" value={packageText(packageData, "youtube")} onCopy={copyText} icon="fileText" />
            </div>
          </Section>

          <LyricScoreCard score={lyricScore} />

          <Section
            label="Audio de Suno"
            title={audioVersions.length ? "Versiones de audio" : "Subir cancion final"}
            actions={
              audioData?.url ? (
                <span style={pillStyle("ok")}>{audioVersions.length || 1} toma(s)</span>
              ) : (
                <span style={pillStyle("neutral")}>mp3 wav m4a</span>
              )
            }
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: "var(--s-4)",
                alignItems: "end",
              }}
            >
              <Field
                label="Nombre de version"
                value={audioVersionLabel}
                onChange={setAudioVersionLabel}
                placeholder={`Toma ${audioVersions.length + 1} - prompt ${audioPromptKind}`}
              />
              <SelectField
                label="Prompt usado en Suno"
                value={audioPromptKind}
                onChange={setAudioPromptKind}
                options={[
                  { id: "original", label: "Prompt maestro" },
                  { id: "alternate", label: "Prompt alterno" },
                  { id: "retry", label: "Otro intento" },
                  { id: "manual", label: "Ajuste manual" },
                ]}
              />
              <label style={{ display: "block" }}>
                <span style={labelStyle()}>Archivo descargado de Suno</span>
                <input
                  type="file"
                  accept=".mp3,.wav,.m4a,.aac,audio/mpeg,audio/wav,audio/mp4,audio/aac"
                  onChange={(event) => setAudioFile(event.target.files?.[0] || null)}
                  style={{
                    ...fieldBase(),
                    paddingTop: 12,
                    color: "var(--paper-dim)",
                  }}
                />
              </label>
              <button
                type="button"
                className="cf-button cf-button--primary"
                onClick={uploadAudio}
                disabled={uploadingAudio || !currentId || !audioFile}
                style={{ minHeight: 54, justifyContent: "center" }}
              >
                <Icon name={uploadingAudio ? "refresh" : "uploadCloud"} size={18} />
                {uploadingAudio ? "Subiendo audio..." : "Subir como nueva version"}
              </button>
            </div>

            <AudioVersionList
              versions={audioVersions}
              activeId={activeAudioVersionId}
              onActivate={activateAudioVersion}
              activating={activatingAudio}
            />
          </Section>

          <Section
            label="Render en VPS"
            title={renderData?.status === "completed" ? "Video musical listo" : "Producir video final"}
            actions={
              renderData?.status === "completed" ? (
                <span style={pillStyle("ok")}>video_ready</span>
              ) : renderData?.status === "running" || renderData?.status === "queued" ? (
                <span style={pillStyle("ember")}>{renderData.status}</span>
              ) : (
                <span style={pillStyle("neutral")}>vps worker</span>
              )
            }
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "var(--s-4)",
                alignItems: "start",
              }}
            >
              <div>
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.6, marginTop: 0 }}>
                  {renderData?.status === "completed"
                    ? "El video final, miniatura, portada y metadata ya quedaron generados y guardados."
                    : audioData?.url || audioData?.storagePath
                      ? `Renderiza el video completo en el VPS usando la version activa: ${safeText(audioData?.label, "toma seleccionada")}.`
                      : "Sube primero el audio final descargado de Suno para habilitar el render."}
                </p>
                {(renderData?.status === "running" || renderData?.status === "queued") && (
                  <div style={{ margin: "var(--s-4) 0" }}>
                    <div
                      style={{
                        height: 8,
                        borderRadius: 999,
                        overflow: "hidden",
                        background: "var(--ink-2)",
                        border: "1px solid var(--rule-1)",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${Math.max(2, Math.min(100, Number(renderData.progress || 2)))}%`,
                          background: "var(--ember)",
                        }}
                      />
                    </div>
                    <div className="cf-caption" style={{ marginTop: 8 }}>
                      {renderData.progress || 2}% · {renderData.stepName || "Procesando en worker"}
                    </div>
                  </div>
                )}
                {renderData?.status === "failed" && (
                  <div className="cf-card" style={{ padding: "var(--s-4)", borderColor: "var(--bad)", color: "var(--bad)", marginBottom: "var(--s-4)" }}>
                    {renderData.error || "El render fallo. Puedes reintentar sin volver a crear la letra."}
                  </div>
                )}
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="cf-button cf-button--primary"
                    onClick={produceVideo}
                    disabled={
                      producingVideo ||
                      !currentId ||
                      (!audioData?.url && !audioData?.storagePath) ||
                      renderData?.status === "completed" ||
                      renderData?.status === "running" ||
                      renderData?.status === "queued"
                    }
                    style={{ minHeight: 52 }}
                  >
                    <Icon name={producingVideo || renderData?.status === "running" ? "refresh" : "clapperboard"} size={18} />
                    {renderData?.status === "completed" ? "Regenerar no disponible" : producingVideo ? "Enviando al VPS..." : "Producir video musical"}
                  </button>
                  {renderData?.video?.url && (
                    <a className="cf-button" href={renderData.video.url} target="_blank" rel="noreferrer" style={{ minHeight: 52, textDecoration: "none", color: "var(--paper)" }}>
                      <Icon name="download" size={18} />
                      Abrir MP4
                    </a>
                  )}
                  {renderData?.thumbnail?.url && (
                    <a className="cf-button" href={renderData.thumbnail.url} target="_blank" rel="noreferrer" style={{ minHeight: 52, textDecoration: "none", color: "var(--paper)" }}>
                      <Icon name="image" size={18} />
                      Miniatura
                    </a>
                  )}
                </div>
              </div>
              <div>
                {renderData?.video?.url ? (
                  <video controls src={renderData.video.url} poster={renderData.thumbnail?.url || renderData.cover?.url} style={{ width: "100%", borderRadius: "var(--r-2)", border: "1px solid var(--rule-1)", background: "var(--ink-2)" }} />
                ) : renderData?.thumbnail?.url || renderData?.cover?.url ? (
                  <img src={renderData.thumbnail?.url || renderData.cover?.url} alt="Miniatura musical" style={{ width: "100%", borderRadius: "var(--r-2)", border: "1px solid var(--rule-1)" }} />
                ) : (
                  <div className="cf-card" style={{ padding: "var(--s-5)", minHeight: 180, display: "grid", placeItems: "center", color: "var(--paper-mute)" }}>
                    Vista previa pendiente
                  </div>
                )}
                {renderData?.durationSeconds && (
                  <div className="cf-caption" style={{ marginTop: 8 }}>
                    {Math.round(Number(renderData.durationSeconds))}s · {renderData.visualBeatCount || renderData.sceneCount || 0} beats visuales
                    {renderData.visualProvider ? ` · ${renderData.visualProvider === "comfy_flux" ? "Flux/Comfy" : "fallback local"}` : ""}
                    {renderData.visualIntervalSeconds ? ` · cada ${Math.round(Number(renderData.visualIntervalSeconds))}s` : ""}
                  </div>
                )}
              </div>
            </div>
          </Section>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
              gap: "var(--s-5)",
              alignItems: "start",
            }}
          >
            <Section
              label="Letra"
              title="Lyrics"
              actions={<CopyButton label="Copiar letra para Suno" value={packageText(packageData, "lyrics")} onCopy={copyText} />}
            >
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  margin: 0,
                  color: "var(--paper-dim)",
                  font: "var(--t-body)",
                  lineHeight: 1.65,
                  background: "var(--ink-2)",
                  border: "1px solid var(--rule-1)",
                  borderRadius: "var(--r-2)",
                  padding: "var(--s-4)",
                  maxHeight: 620,
                  overflow: "auto",
                }}
              >
                {safeText(packageData.lyrics)}
              </pre>
            </Section>

            <div style={{ display: "grid", gap: "var(--s-5)" }}>
              <Section label="Suno" title="Prompt maestro">
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.6 }}>{safeText(packageData.sunoPrompt)}</p>
                {packageData.sunoPromptAlt && (
                  <div style={{ marginTop: "var(--s-4)" }}>
                    <div className="cf-mono-sm">Alternativa</div>
                    <p style={{ color: "var(--paper-dim)", lineHeight: 1.6 }}>{safeText(packageData.sunoPromptAlt)}</p>
                  </div>
                )}
                {packageData.negativePrompt && (
                  <div style={{ marginTop: "var(--s-4)" }}>
                    <div className="cf-mono-sm">Evitar en Suno</div>
                    <p style={{ color: "var(--paper-mute)", lineHeight: 1.6 }}>{safeText(packageData.negativePrompt)}</p>
                  </div>
                )}
              </Section>

              <Section label="Video" title="Direccion visual">
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.6 }}>
                  {safeText(packageData.videoConcept?.visualIdentity || packageData.coverPrompt, "Identidad visual pendiente.")}
                </p>
                {Array.isArray(packageData.videoConcept?.palette) && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, margin: "var(--s-4) 0" }}>
                    {packageData.videoConcept.palette.map((color, index) => {
                      const label = safeText(color, "color");
                      return (
                        <span key={`${label}-${index}`} style={pillStyle("neutral")}>{label}</span>
                      );
                    })}
                  </div>
                )}
                <VisualSceneList scenes={packageData.videoConcept?.scenes} />
              </Section>
            </div>
          </div>

          <Section label="Publicacion" title="YouTube y seguridad">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: "var(--s-4)",
              }}
            >
              <div>
                <div className="cf-mono-sm">Titulo</div>
                <p style={{ color: "var(--paper)", lineHeight: 1.55 }}>{safeText(packageData.youtube?.title || packageData.title)}</p>
              </div>
              <div>
                <div className="cf-mono-sm">Miniatura</div>
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{safeText(packageData.youtube?.thumbnailText, "Texto pendiente")}</p>
              </div>
              <div>
                <div className="cf-mono-sm">Hook principal</div>
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{safeText(packageData.mainHook || packageData.mantra)}</p>
              </div>
            </div>
            {Array.isArray(packageData.safetyNotes) && packageData.safetyNotes.length > 0 && (
              <div style={{ marginTop: "var(--s-4)" }}>
                <div className="cf-mono-sm">Guardrails</div>
                <ul style={{ color: "var(--paper-mute)", lineHeight: 1.7, paddingLeft: 20 }}>
                  {packageData.safetyNotes.map((item, index) => (
                    <li key={`${safeText(item, "nota")}-${index}`}>{safeText(item)}</li>
                  ))}
                </ul>
              </div>
            )}
          </Section>
        </div>
      )}
    </main>
  );
}
