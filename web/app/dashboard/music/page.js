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

function packageText(pkg, key) {
  if (!pkg) return "";
  if (key === "lyrics") return pkg.lyrics || "";
  if (key === "suno") return pkg.sunoPrompt || "";
  if (key === "sunoAlt") return pkg.sunoPromptAlt || "";
  if (key === "negative") return pkg.negativePrompt || "";
  if (key === "youtube") {
    const youtube = pkg.youtube || {};
    return [
      youtube.title,
      "",
      youtube.description,
      "",
      Array.isArray(youtube.hashtags) ? youtube.hashtags.join(" ") : "",
      Array.isArray(youtube.tags) ? `Tags: ${youtube.tags.join(", ")}` : "",
      youtube.thumbnailText ? `Miniatura: ${youtube.thumbnailText}` : "",
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
              <span style={pillStyle("neutral")}>{pkg.bpm || "--"} bpm</span>
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

function VisualSceneList({ scenes }) {
  const items = Array.isArray(scenes) ? scenes : [];
  if (!items.length) return <p className="cf-caption">El paquete aun no trae escenas visuales.</p>;
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {items.map((scene, index) => (
        <div
          key={`${scene.title || "scene"}-${index}`}
          style={{
            border: "1px solid var(--rule-1)",
            borderRadius: "var(--r-2)",
            padding: "var(--s-4)",
            background: "var(--ink-2)",
          }}
        >
          <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 6 }}>
            {String(index + 1).padStart(2, "0")} · {scene.title || "Escena"}
          </div>
          <div style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{scene.prompt || scene.description || scene}</div>
        </div>
      ))}
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
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [copied, setCopied] = useState("");

  const packageData = current?.package || null;

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
                ["03", "Descarga audio. El siguiente bloque permitira subirlo aqui."],
                ["04", "Content Factory generara visuales, miniatura y video para YouTube."],
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
            title={packageData.title || "Cancion generada"}
            actions={
              <>
                <span style={pillStyle("ember")}>{packageData.bpm || "--"} bpm</span>
                <span style={pillStyle("neutral")}>{packageData.energy || "energia"}</span>
              </>
            }
          >
            <p style={{ font: "var(--t-lead)", color: "var(--paper-dim)", marginTop: 0 }}>
              {packageData.subtitle || packageData.mainHook || "Lista para llevar a Suno."}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: "var(--s-4)" }}>
              <CopyButton label="Copiar letra" value={packageText(packageData, "lyrics")} onCopy={copyText} />
              <CopyButton label="Copiar prompt Suno" value={packageText(packageData, "suno")} onCopy={copyText} icon="zap" />
              <CopyButton label="Prompt alterno" value={packageText(packageData, "sunoAlt")} onCopy={copyText} icon="copy" />
              <CopyButton label="YouTube" value={packageText(packageData, "youtube")} onCopy={copyText} icon="fileText" />
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
            <Section label="Letra" title="Lyrics">
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
                {packageData.lyrics}
              </pre>
            </Section>

            <div style={{ display: "grid", gap: "var(--s-5)" }}>
              <Section label="Suno" title="Prompt maestro">
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.6 }}>{packageData.sunoPrompt}</p>
                {packageData.sunoPromptAlt && (
                  <div style={{ marginTop: "var(--s-4)" }}>
                    <div className="cf-mono-sm">Alternativa</div>
                    <p style={{ color: "var(--paper-dim)", lineHeight: 1.6 }}>{packageData.sunoPromptAlt}</p>
                  </div>
                )}
                {packageData.negativePrompt && (
                  <div style={{ marginTop: "var(--s-4)" }}>
                    <div className="cf-mono-sm">Evitar en Suno</div>
                    <p style={{ color: "var(--paper-mute)", lineHeight: 1.6 }}>{packageData.negativePrompt}</p>
                  </div>
                )}
              </Section>

              <Section label="Video" title="Direccion visual">
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.6 }}>
                  {packageData.videoConcept?.visualIdentity || packageData.coverPrompt || "Identidad visual pendiente."}
                </p>
                {Array.isArray(packageData.videoConcept?.palette) && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, margin: "var(--s-4) 0" }}>
                    {packageData.videoConcept.palette.map((color) => (
                      <span key={color} style={pillStyle("neutral")}>{color}</span>
                    ))}
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
                <p style={{ color: "var(--paper)", lineHeight: 1.55 }}>{packageData.youtube?.title || packageData.title}</p>
              </div>
              <div>
                <div className="cf-mono-sm">Miniatura</div>
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{packageData.youtube?.thumbnailText || "Texto pendiente"}</p>
              </div>
              <div>
                <div className="cf-mono-sm">Hook principal</div>
                <p style={{ color: "var(--paper-dim)", lineHeight: 1.55 }}>{packageData.mainHook || packageData.mantra}</p>
              </div>
            </div>
            {Array.isArray(packageData.safetyNotes) && packageData.safetyNotes.length > 0 && (
              <div style={{ marginTop: "var(--s-4)" }}>
                <div className="cf-mono-sm">Guardrails</div>
                <ul style={{ color: "var(--paper-mute)", lineHeight: 1.7, paddingLeft: 20 }}>
                  {packageData.safetyNotes.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
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
