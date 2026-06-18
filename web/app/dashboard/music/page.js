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

const DEFAULT_IMPORT_FORM = {
  title: "",
  subtitle: "",
  intention: "disciplina",
  style: "latin_trap_anthem",
  energy: "alta, elegante, cinematica",
  visualIdentity:
    "visuales cinematograficos premium que sigan la letra: amanecer, movimiento, enfoque, simbolos de identidad, fuerza y avance",
  lyrics: "",
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
      className="cf-card cf-music-notice"
      style={{
        borderColor: error ? "var(--bad)" : "var(--ok)",
        color: error ? "var(--bad)" : "var(--ok)",
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
      className="cf-button cf-button--subtle"
      onClick={() => onCopy(label, value)}
      disabled={!value}
      style={{
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
    <section className="cf-card cf-music-panel" style={{ padding: "var(--s-5)" }}>
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
        {actions && <div className="cf-music-actions">{actions}</div>}
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

function MusicWorkflowGuide({ hasPackage, audioCount, renderCount, renderBusy }) {
  const steps = [
    {
      id: "package",
      title: "Crear paquete",
      copy: "Letra, prompt Suno, direccion visual y metadata.",
      done: hasPackage,
      active: !hasPackage,
    },
    {
      id: "suno",
      title: "Probar en Suno",
      copy: "Copia letra y prompt. Suno puede darte varias tomas.",
      done: audioCount > 0,
      active: hasPackage && audioCount === 0,
    },
    {
      id: "takes",
      title: "Subir tomas",
      copy: "Guarda v1.1, v1.2 o prompt alterno sin pisarlas.",
      done: audioCount > 0,
      active: hasPackage && audioCount > 0 && renderCount === 0,
    },
    {
      id: "render",
      title: "Renderizar",
      copy: "Cada toma puede generar su propio MP4 y miniatura.",
      done: renderCount > 0,
      active: renderBusy || (audioCount > 0 && renderCount === 0),
    },
  ];

  return (
    <div className="cf-music-workflow" aria-label="Flujo de trabajo de musica">
      {steps.map((step, index) => {
        const stateClass = step.done ? " is-done" : step.active ? " is-active" : "";
        return (
          <div key={step.id} className={`cf-music-step${stateClass}`}>
            <div className="cf-music-step-number">{String(index + 1).padStart(2, "0")}</div>
            <div className="cf-music-step-title">{step.title}</div>
            <div className="cf-music-step-copy">{step.copy}</div>
          </div>
        );
      })}
    </div>
  );
}

function TrackList({ tracks, selectedId, onSelect }) {
  if (!tracks.length) {
    return (
      <div className="cf-music-empty">
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
            className={`cf-music-track-card${active ? " is-active" : ""}`}
            style={{
              borderColor: active ? "var(--ember)" : undefined,
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

function renderStatusTone(status) {
  if (status === "completed") return "ok";
  if (status === "queued" || status === "running" || status === "failed") return "ember";
  return "neutral";
}

function renderStatusLabel(status) {
  if (status === "completed") return "video listo";
  if (status === "running") return "render";
  if (status === "queued") return "en cola";
  if (status === "failed") return "fallo";
  return "sin video";
}

function subtitleModeLabel(mode) {
  if (mode === "whisper_word_aligned") return "Whisper";
  if (mode === "lyric_blocks_estimated") return "SRT estimado";
  return "";
}

function AudioVersionList({
  versions,
  activeId,
  onActivate,
  activating,
  onProduce,
  producingVersionId,
  renderByVersion,
  anyRenderBusy,
}) {
  const items = Array.isArray(versions) ? versions : [];
  if (!items.length) {
    return (
      <div className="cf-music-empty" style={{ marginTop: "var(--s-4)" }}>
        Todavia no hay tomas de audio. Genera 2 versiones en Suno, descarga la mejor y subela aqui para comparar renders.
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: 10, marginTop: "var(--s-4)" }}>
      {items.map((version, index) => {
        const versionId = safeText(version.versionId || `take_${index + 1}`);
        const active = activeId ? activeId === versionId : version.isActive;
        const render = renderByVersion?.[versionId] || null;
        const renderBusy = render?.status === "queued" || render?.status === "running";
        const renderDone = render?.status === "completed" && render?.video?.url;
        const producingThis = producingVersionId === versionId;
        return (
          <div
            key={`${versionId}-${index}`}
            className={`cf-music-version-card${active ? " is-active" : ""}`}
            style={{
              borderColor: active ? "var(--ok)" : "var(--rule-1)",
            }}
          >
            <div className="cf-music-version-head">
              <div className="cf-music-version-index">v{index + 1}</div>
              <div>
                <strong style={{ color: "var(--paper)", display: "block", fontSize: 17 }}>{safeText(version.label, `Toma ${index + 1}`)}</strong>
                <div className="cf-caption">
                  {safeText(version.promptKind, "suno")} · {safeText(version.originalFileName || version.fileName, "audio")}
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                  {active && <span style={pillStyle("ok")}>toma activa</span>}
                  <span style={pillStyle(renderStatusTone(render?.status))}>{renderStatusLabel(render?.status)}</span>
                  {subtitleModeLabel(render?.subtitleMode) && <span style={pillStyle(render?.subtitleMode === "whisper_word_aligned" ? "ok" : "neutral")}>{subtitleModeLabel(render?.subtitleMode)}</span>}
                </div>
              </div>
              <div className="cf-music-version-actions">
                <button
                  type="button"
                  className="cf-button cf-button--subtle"
                  onClick={() => onActivate(versionId)}
                  disabled={active || activating}
                >
                  <Icon name="check" size={16} />
                  {active ? "Activa" : "Marcar activa"}
                </button>
                <button
                  type="button"
                  className="cf-button cf-button--primary"
                  onClick={() => onProduce(versionId)}
                  disabled={anyRenderBusy || producingThis || renderBusy || renderDone || (!version.url && !version.storagePath)}
                >
                  <Icon name={producingThis || renderBusy ? "refresh" : "clapperboard"} size={16} />
                  {renderDone ? "Video listo" : producingThis || renderBusy ? "Renderizando..." : "Renderizar"}
                </button>
              </div>
            </div>
            {version.url && <audio className="cf-music-version-audio" controls src={version.url} />}
            {render?.error && (
              <div className="cf-caption" style={{ color: "var(--bad)", marginTop: 10 }}>
                {safeText(render.error, "El render de esta toma fallo.")}
              </div>
            )}
            <div className="cf-music-actions" style={{ marginTop: 12 }}>
              {render?.video?.url && (
                <a className="cf-button cf-button--success" href={render.video.url} target="_blank" rel="noreferrer">
                  <Icon name="download" size={16} />
                  Abrir MP4
                </a>
              )}
              {render?.thumbnail?.url && (
                <a className="cf-button cf-button--subtle" href={render.thumbnail.url} target="_blank" rel="noreferrer">
                  <Icon name="image" size={16} />
                  Miniatura
                </a>
              )}
              {render?.subtitles?.url && (
                <a className="cf-button cf-button--subtle" href={render.subtitles.url} target="_blank" rel="noreferrer">
                  <Icon name="fileText" size={16} />
                  SRT
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RenderHistoryList({ renders, versions }) {
  const items = Array.isArray(renders)
    ? renders.filter((item) => item && (item.audioVersionId || item.video?.url || item.status))
    : [];
  if (!items.length) {
    return (
      <div className="cf-music-empty">
        Todavia no hay videos por toma. Cuando renderices una version de audio, su MP4 y miniatura apareceran aqui sin reemplazar las otras tomas.
      </div>
    );
  }
  const labelByVersion = new Map(
    (Array.isArray(versions) ? versions : []).map((item, index) => [
      safeText(item.versionId || `take_${index + 1}`),
      safeText(item.label, `Toma ${index + 1}`),
    ])
  );
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {items.map((render, index) => {
        const versionId = safeText(render.audioVersionId, `version_${index + 1}`);
        const label = safeText(render.audioLabel || labelByVersion.get(versionId), versionId);
        const duration = render.durationSeconds ? `${Math.round(Number(render.durationSeconds))}s` : "";
        const beatCount = render.visualBeatCount || render.sceneCount || 0;
        return (
          <div
            key={`${versionId}-${index}`}
            className="cf-music-render-row"
            style={{
              borderColor: render.status === "completed" ? "rgba(111,190,142,0.34)" : undefined,
            }}
          >
            <div style={{ display: "flex", gap: 14, alignItems: "center", minWidth: 0 }}>
              {render.thumbnail?.url && (
                <img className="cf-music-render-thumb" src={render.thumbnail.url} alt={`Miniatura ${label}`} />
              )}
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  <strong style={{ color: "var(--paper)" }}>{label}</strong>
                  <span style={pillStyle(renderStatusTone(render.status))}>{renderStatusLabel(render.status)}</span>
                </div>
                <div className="cf-caption" style={{ marginTop: 6 }}>
                  {[duration, beatCount ? `${beatCount} beats visuales` : "", render.visualProvider ? (render.visualProvider === "comfy_flux" ? "Flux/Comfy" : "fallback local") : "", subtitleModeLabel(render.subtitleMode), formatDate(render.completedAt || render.updatedAt || render.queuedAt)].filter(Boolean).join(" · ")}
                </div>
                {render.error && <div className="cf-caption" style={{ color: "var(--bad)", marginTop: 6 }}>{safeText(render.error)}</div>}
              </div>
            </div>
            <div className="cf-music-actions" style={{ justifyContent: "flex-end" }}>
              {render.video?.url && (
                <a className="cf-button cf-button--success" href={render.video.url} target="_blank" rel="noreferrer">
                  <Icon name="download" size={16} />
                  MP4
                </a>
              )}
              {render.thumbnail?.url && (
                <a className="cf-button cf-button--subtle" href={render.thumbnail.url} target="_blank" rel="noreferrer">
                  <Icon name="image" size={16} />
                  Miniatura
                </a>
              )}
              {render.subtitles?.url && (
                <a className="cf-button cf-button--subtle" href={render.subtitles.url} target="_blank" rel="noreferrer">
                  <Icon name="fileText" size={16} />
                  SRT
                </a>
              )}
            </div>
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
            className="cf-music-scene-card"
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
  const [importForm, setImportForm] = useState(DEFAULT_IMPORT_FORM);
  const [current, setCurrent] = useState(null);
  const [currentId, setCurrentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [importingSong, setImportingSong] = useState(false);
  const [uploadingAudio, setUploadingAudio] = useState(false);
  const [producingVideo, setProducingVideo] = useState(false);
  const [producingVersionId, setProducingVersionId] = useState("");
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
  const renderHistory = useMemo(() => {
    const sourceRender = current?.render || null;
    const list = Array.isArray(current?.renders) ? current.renders.filter(Boolean) : [];
    const renderVersionId = safeText(sourceRender?.audioVersionId);
    if (renderVersionId && !list.some((item) => safeText(item?.audioVersionId) === renderVersionId)) {
      return [...list, sourceRender];
    }
    return list;
  }, [current]);
  const renderByVersion = useMemo(() => {
    const map = {};
    for (const item of renderHistory) {
      const versionId = safeText(item?.audioVersionId);
      if (versionId) map[versionId] = item;
    }
    return map;
  }, [renderHistory]);
  const anyRenderBusy = useMemo(
    () => renderHistory.some((item) => item?.status === "queued" || item?.status === "running"),
    [renderHistory]
  );
  const completedRenderCount = useMemo(
    () => renderHistory.filter((item) => item?.status === "completed" && item?.video?.url).length,
    [renderHistory]
  );
  const activeRender = renderByVersion[activeAudioVersionId] || (safeText(renderData?.audioVersionId) === activeAudioVersionId ? renderData : null);
  const renderPanel = activeRender || (!activeAudioVersionId ? renderData : null);
  const renderBusy = anyRenderBusy || renderPanel?.status === "queued" || renderPanel?.status === "running";
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

  const updateImportForm = useCallback((key, value) => {
    setImportForm((prev) => ({ ...prev, [key]: value }));
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

  async function importExistingSong() {
    setError("");
    setNotice("");
    setCopied("");
    if (!importForm.title.trim()) {
      setError("Ponle titulo a la cancion para crear el track.");
      return;
    }
    if (importForm.lyrics.trim().length < 40) {
      setError("Pega la letra completa antes de crear el track para video.");
      return;
    }
    setImportingSong(true);
    try {
      const data = await apiFetch("/music/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...importForm }),
      });
      if (data.track) {
        setCurrent(data.track);
        setCurrentId(data.track.trackId || data.trackId || "");
      } else {
        setCurrent({
          trackId: data.trackId,
          package: data.package,
          status: "lyrics_ready",
          generationMode: data.generationMode,
        });
        setCurrentId(data.trackId || "");
      }
      setNotice("Cancion importada. Ahora sube el audio de Suno y produce el video con imagenes cada 5 segundos.");
      await loadTracks();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setImportingSong(false);
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

  async function produceVideo(versionId = "") {
    if (!currentId) {
      setError("Primero genera o selecciona un track.");
      return;
    }
    const selectedVersion = versionId
      ? audioVersions.find((item) => safeText(item.versionId) === versionId)
      : audioData;
    if (!selectedVersion?.url && !selectedVersion?.storagePath) {
      setError("Primero sube el audio final descargado de Suno.");
      return;
    }
    setError("");
    setNotice("");
    setProducingVideo(true);
    setProducingVersionId(versionId || activeAudioVersionId || "active");
    try {
      const path = versionId
        ? `/music/tracks/${encodeURIComponent(currentId)}/audio/${encodeURIComponent(versionId)}/produce`
        : `/music/tracks/${encodeURIComponent(currentId)}/produce`;
      const data = await apiFetch(path, {
        method: "POST",
      });
      if (data.track) {
        setCurrent(data.track);
        setCurrentId(data.track.trackId || currentId);
      }
      if (data.alreadyReady) {
        setNotice(versionId ? "Esta toma ya tiene video final listo." : "Este track ya tiene video final listo.");
      } else if (data.duplicateBlocked) {
        setNotice("Ya hay un render de este track en proceso. Espera a que termine para lanzar otra toma.");
      } else {
        setNotice(versionId ? "Render de esta toma enviado al VPS." : "Render musical enviado al VPS. Puedes cerrar esta pantalla; el worker seguira produciendo.");
      }
      await loadTracks();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setProducingVideo(false);
      setProducingVersionId("");
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
    <main className="cf-page cf-music-page">
      <header className="cf-music-hero">
        <div className="cf-music-hero-grid">
          <div>
            <div className="cf-kicker">POWER MUSIC</div>
            <h1 className="cf-music-title">Música de poder</h1>
            <p className="cf-music-subtitle">
              Crea letras premium, prompts para Suno, versiones de audio y videos visuales por toma sin perder el control editorial.
            </p>
          </div>
          <div className="cf-music-command">
            <p className="cf-music-command-title">Flujo recomendado</p>
            <p className="cf-music-command-body">
              Genera el paquete, prueba 2 o mas tomas en Suno, subelas como versiones y renderiza solo las que valgan la pena.
            </p>
            <div className="cf-music-actions" style={{ marginTop: 14 }}>
              <span style={pillStyle("neutral")}>{tracks.length} tracks</span>
              <span style={pillStyle(audioVersions.length ? "ok" : "neutral")}>{audioVersions.length} toma(s)</span>
              <span style={pillStyle(completedRenderCount ? "ok" : "neutral")}>{completedRenderCount} video(s)</span>
            </div>
          </div>
        </div>
      </header>

      <Notice error={error} notice={notice || (copied ? `${copied} listo para pegar.` : "")} />

      <MusicWorkflowGuide
        hasPackage={Boolean(packageData)}
        audioCount={audioVersions.length}
        renderCount={completedRenderCount}
        renderBusy={renderBusy}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "var(--s-5)",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "var(--s-5)" }}>
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

          <Section
            label="Ya tengo cancion"
            title="Importar letra"
            actions={<span style={pillStyle("neutral")}>video desde audio</span>}
          >
            <p className="cf-music-helper" style={{ marginTop: 0, marginBottom: "var(--s-4)" }}>
              Pega una letra ya creada en Suno o escrita por ti. Content Factory generara direccion visual, score, metadata, imagenes cada 5 segundos y subtitulos por bloques.
            </p>
            <div style={{ display: "grid", gap: "var(--s-4)" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--s-4)" }}>
                <Field label="Titulo" value={importForm.title} onChange={(value) => updateImportForm("title", value)} placeholder="Ej. Hoy no negocio conmigo" />
                <Field label="Subtitulo / promesa" value={importForm.subtitle} onChange={(value) => updateImportForm("subtitle", value)} placeholder="Ej. Disciplina para entrenar sin excusas" />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--s-4)" }}>
                <SelectField
                  label="Intencion"
                  value={importForm.intention}
                  onChange={(value) => updateImportForm("intention", value)}
                  options={presets.intentions.length ? presets.intentions : [{ id: DEFAULT_IMPORT_FORM.intention, label: "Disciplina" }]}
                />
                <SelectField
                  label="Estilo"
                  value={importForm.style}
                  onChange={(value) => updateImportForm("style", value)}
                  options={presets.styles.length ? presets.styles : [{ id: DEFAULT_IMPORT_FORM.style, label: "Latin Trap Anthem" }]}
                />
              </div>
              <Field label="Energia visual" value={importForm.energy} onChange={(value) => updateImportForm("energy", value)} />
              <TextArea
                label="Identidad visual"
                value={importForm.visualIdentity}
                onChange={(value) => updateImportForm("visualIdentity", value)}
                rows={3}
              />
              <TextArea
                label="Letra completa"
                value={importForm.lyrics}
                onChange={(value) => updateImportForm("lyrics", value)}
                placeholder="[Intro]\n...\n[Chorus]\n..."
                rows={9}
              />
              <button
                type="button"
                className="cf-button cf-button--primary"
                onClick={importExistingSong}
                disabled={importingSong || !importForm.title.trim() || importForm.lyrics.trim().length < 40}
                style={{ minHeight: 58, justifyContent: "center", fontSize: 18 }}
              >
                <Icon name={importingSong ? "refresh" : "plus"} size={20} />
                {importingSong ? "Creando track..." : "Crear track para video"}
              </button>
            </div>
          </Section>
        </div>

        <div style={{ display: "grid", gap: "var(--s-5)" }}>
          <Section label="Workflow" title="Comparar tomas">
            <div style={{ display: "grid", gap: 12 }}>
              {[
                ["01", "Usa Copiar letra y Copiar prompt Suno. En Suno normalmente salen 2 tomas por intento."],
                ["02", "Sube cada audio como v1.1, v1.2, prompt alterno A o intento manual."],
                ["03", "Marca como activa la toma que mas te guste para escucharla y producirla primero."],
                ["04", "Renderiza cada toma fuerte. Cada una conserva su propio MP4, miniatura y metadata."],
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
            <p className="cf-music-helper" style={{ marginBottom: "var(--s-4)" }}>
              Sube aqui cada version que Suno te entregue. Puedes conservar varias tomas para la misma letra y renderizar un video distinto para cada una.
            </p>
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
              onProduce={produceVideo}
              producingVersionId={producingVersionId}
              renderByVersion={renderByVersion}
              anyRenderBusy={anyRenderBusy}
            />
          </Section>

          <Section
            label="Render en VPS"
            title={renderPanel?.status === "completed" ? "Video de toma activa listo" : "Producir video final"}
            actions={
              renderPanel?.status === "completed" ? (
                <span style={pillStyle("ok")}>video_ready</span>
              ) : renderPanel?.status === "running" || renderPanel?.status === "queued" ? (
                <span style={pillStyle("ember")}>{renderPanel.status}</span>
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
                  {renderPanel?.status === "completed"
                    ? "La toma activa ya tiene video, miniatura, portada y metadata guardados."
                    : audioData?.url || audioData?.storagePath
                      ? `Renderiza el video completo en el VPS usando la version activa: ${safeText(audioData?.label, "toma seleccionada")}.`
                      : "Sube primero el audio final descargado de Suno para habilitar el render."}
                </p>
                {(renderPanel?.status === "running" || renderPanel?.status === "queued") && (
                  <div style={{ margin: "var(--s-4) 0" }}>
                    <div className="cf-music-progress">
                      <span
                        style={{
                          width: `${Math.max(2, Math.min(100, Number(renderPanel.progress || 2)))}%`,
                        }}
                      />
                    </div>
                    <div className="cf-caption" style={{ marginTop: 8 }}>
                      {renderPanel.progress || 2}% · {renderPanel.stepName || "Procesando en worker"}
                    </div>
                  </div>
                )}
                {renderPanel?.status === "failed" && (
                  <div className="cf-card" style={{ padding: "var(--s-4)", borderColor: "var(--bad)", color: "var(--bad)", marginBottom: "var(--s-4)" }}>
                    {renderPanel.error || "El render fallo. Puedes reintentar sin volver a crear la letra."}
                  </div>
                )}
                <div className="cf-music-actions">
                  <button
                    type="button"
                    className="cf-button cf-button--primary"
                    onClick={produceVideo}
                    disabled={
                      producingVideo ||
                      !currentId ||
                      (!audioData?.url && !audioData?.storagePath) ||
                      renderPanel?.status === "completed" ||
                      anyRenderBusy
                    }
                    style={{ minHeight: 52 }}
                  >
                    <Icon name={producingVideo || renderPanel?.status === "running" ? "refresh" : "clapperboard"} size={18} />
                    {renderPanel?.status === "completed" ? "Video de toma activa listo" : producingVideo ? "Enviando al VPS..." : "Producir toma activa"}
                  </button>
                  {renderPanel?.video?.url && (
                    <a className="cf-button cf-button--success" href={renderPanel.video.url} target="_blank" rel="noreferrer" style={{ minHeight: 52 }}>
                      <Icon name="download" size={18} />
                      Abrir MP4
                    </a>
                  )}
                  {renderPanel?.thumbnail?.url && (
                    <a className="cf-button cf-button--subtle" href={renderPanel.thumbnail.url} target="_blank" rel="noreferrer" style={{ minHeight: 52 }}>
                      <Icon name="image" size={18} />
                      Miniatura
                    </a>
                  )}
                  {renderPanel?.subtitles?.url && (
                    <a className="cf-button cf-button--subtle" href={renderPanel.subtitles.url} target="_blank" rel="noreferrer" style={{ minHeight: 52 }}>
                      <Icon name="fileText" size={18} />
                      Subtitulos SRT
                    </a>
                  )}
                </div>
              </div>
              <div>
                {renderPanel?.video?.url ? (
                  <video className="cf-music-render-preview" controls src={renderPanel.video.url} poster={renderPanel.thumbnail?.url || renderPanel.cover?.url} />
                ) : renderPanel?.thumbnail?.url || renderPanel?.cover?.url ? (
                  <img className="cf-music-render-preview" src={renderPanel.thumbnail?.url || renderPanel.cover?.url} alt="Miniatura musical" />
                ) : (
                  <div className="cf-music-preview-empty">
                    Vista previa pendiente
                  </div>
                )}
                {renderPanel?.durationSeconds && (
                  <div className="cf-caption" style={{ marginTop: 8 }}>
                    {Math.round(Number(renderPanel.durationSeconds))}s · {renderPanel.visualBeatCount || renderPanel.sceneCount || 0} beats visuales
                    {renderPanel.visualProvider ? ` · ${renderPanel.visualProvider === "comfy_flux" ? "Flux/Comfy" : "fallback local"}` : ""}
                    {renderPanel.visualIntervalSeconds ? ` · cada ${Math.round(Number(renderPanel.visualIntervalSeconds))}s` : ""}
                    {subtitleModeLabel(renderPanel.subtitleMode) ? ` · ${subtitleModeLabel(renderPanel.subtitleMode)}` : ""}
                  </div>
                )}
              </div>
            </div>
          </Section>

          <Section
            label="Videos generados por version"
            title="Historial de tomas"
            actions={<span style={pillStyle("neutral")}>{renderHistory.length} render(es)</span>}
          >
            <RenderHistoryList renders={renderHistory} versions={audioVersions} />
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
                className="cf-music-code-box"
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
