"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { authHeaders, getApiBase } from "@/lib/apiClient";
import { isAdminUser } from "@/lib/admin";
import Icon from "@/components/Icon";

const CUSTOM_AGENTS_ENABLED =
  process.env.NEXT_PUBLIC_CONTENT_FACTORY_CUSTOM_AGENTS_ENABLED !== "false";

const EMPTY_BRIEF = {
  niche: "",
  audience: "",
  promise: "",
  tone: "",
  styleReferences: "",
  mustInclude: "",
  mustAvoid: "",
  visualIdentity: "",
  safetyNotes: "",
};

const EMPTY_FORM = {
  customAgentId: "",
  templateKey: "documentary_10_section",
  name: "",
  description: "",
  category: "",
  color: "#E0533D",
  monogram: "Ag",
  exampleTopics: "",
  brief: EMPTY_BRIEF,
};

const STATUS_LABEL = {
  draft: "Borrador",
  testing: "En prueba",
  active: "Activo",
  archived: "Archivado",
};

function listToText(value) {
  if (Array.isArray(value)) return value.join("\n");
  return value || "";
}

function textToList(value) {
  return String(value || "")
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formFromAgent(agent) {
  return {
    customAgentId: agent.customAgentId || agent.id || "",
    templateKey: agent.templateKey || "documentary_10_section",
    name: agent.name || "",
    description: agent.description || "",
    category: agent.category || "",
    color: agent.color || "#E0533D",
    monogram: agent.monogram || "Ag",
    exampleTopics: listToText(agent.exampleTopics),
    brief: {
      ...EMPTY_BRIEF,
      ...(agent.brief || {}),
      styleReferences: listToText(agent.brief?.styleReferences),
      mustInclude: listToText(agent.brief?.mustInclude),
      mustAvoid: listToText(agent.brief?.mustAvoid),
    },
  };
}

function payloadFromForm(form) {
  return {
    templateKey: form.templateKey,
    name: form.name.trim(),
    description: form.description.trim(),
    category: form.category.trim(),
    color: form.color,
    monogram: form.monogram.trim().slice(0, 4) || "Ag",
    exampleTopics: textToList(form.exampleTopics),
    brief: {
      niche: form.brief.niche.trim(),
      audience: form.brief.audience.trim(),
      promise: form.brief.promise.trim(),
      tone: form.brief.tone.trim(),
      styleReferences: textToList(form.brief.styleReferences),
      mustInclude: textToList(form.brief.mustInclude),
      mustAvoid: textToList(form.brief.mustAvoid),
      visualIdentity: form.brief.visualIdentity.trim(),
      safetyNotes: form.brief.safetyNotes.trim(),
    },
  };
}

function StatusBadge({ status }) {
  const cls =
    status === "active"
      ? "cf-badge--ok"
      : status === "testing"
        ? "cf-badge--warn"
        : status === "archived"
          ? "cf-badge--muted"
          : "cf-badge--draft";
  return <span className={`cf-badge ${cls}`}>{STATUS_LABEL[status] || status}</span>;
}

function ScoreLine({ label, value }) {
  const score = Number(value || 0);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "120px 1fr 36px", gap: 10, alignItems: "center" }}>
      <div style={{ font: "var(--t-mono-sm)", color: "var(--paper-mute)", textTransform: "uppercase" }}>{label}</div>
      <div style={{ height: 5, borderRadius: 999, background: "var(--ink-2)", overflow: "hidden" }}>
        <div style={{ width: `${Math.max(0, Math.min(100, score))}%`, height: "100%", background: score >= 75 ? "var(--ok)" : "var(--ember)" }} />
      </div>
      <div style={{ font: "var(--t-mono-sm)", color: "var(--paper-dim)", textAlign: "right" }}>{score}</div>
    </div>
  );
}

export default function AgentsPage() {
  const { user, profile } = useAuth();
  const router = useRouter();
  const admin = isAdminUser(user, profile);

  const [templates, setTemplates] = useState([]);
  const [agents, setAgents] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [compiled, setCompiled] = useState(null);
  const [testTopic, setTestTopic] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.customAgentId === selectedId || agent.id === selectedId) || null,
    [agents, selectedId],
  );

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.templateKey === form.templateKey) || templates[0],
    [templates, form.templateKey],
  );

  const loadData = useCallback(async () => {
    if (!user || !admin || !CUSTOM_AGENTS_ENABLED) return;
    setLoading(true);
    setError("");
    try {
      const headers = await authHeaders(user);
      const [templatesRes, agentsRes] = await Promise.all([
        fetch(`${getApiBase()}/custom-agents/templates`, { headers }),
        fetch(`${getApiBase()}/custom-agents?includeArchived=true`, { headers }),
      ]);
      const templatesData = await templatesRes.json().catch(() => ({}));
      const agentsData = await agentsRes.json().catch(() => ({}));
      if (!templatesRes.ok) throw new Error(templatesData.detail || templatesData.error || "No se pudieron cargar plantillas.");
      if (!agentsRes.ok) throw new Error(agentsData.detail || agentsData.error || "No se pudieron cargar agentes.");
      setTemplates(templatesData.templates || []);
      setAgents(agentsData.agents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user, admin]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadData();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setCompiled(null);
  }

  function updateBrief(field, value) {
    setForm((current) => ({
      ...current,
      brief: { ...current.brief, [field]: value },
    }));
    setCompiled(null);
  }

  function newAgent() {
    setSelectedId("");
    setForm(EMPTY_FORM);
    setCompiled(null);
    setTestResult(null);
    setTestTopic("");
    setMessage("");
    setError("");
  }

  function selectExistingAgent(agent) {
    setSelectedId(agent.customAgentId);
    setForm(formFromAgent(agent));
    setCompiled({
      compiledPrompt: agent.compiledPrompt,
      validation: agent.validation,
    });
    setTestResult(agent.lastTest || null);
    setMessage("");
    setError("");
  }

  async function compilePrompt() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${getApiBase()}/custom-agents/compile`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
        body: JSON.stringify(payloadFromForm(form)),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo compilar.");
      setCompiled(data);
      setMessage("Prompt compilado. Revisa la validacion antes de guardar o probar.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function saveAgent() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const id = form.customAgentId;
      const res = await fetch(`${getApiBase()}/custom-agents${id ? `/${id}` : ""}`, {
        method: id ? "PATCH" : "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
        body: JSON.stringify(payloadFromForm(form)),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo guardar.");
      const saved = data.agent;
      setForm(formFromAgent(saved));
      setSelectedId(saved.customAgentId);
      setCompiled({ compiledPrompt: saved.compiledPrompt, validation: saved.validation });
      setMessage(data.requiresRetest ? "Guardado como borrador. Necesita nueva prueba." : "Agente guardado.");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function runTest() {
    if (!form.customAgentId) {
      setError("Guarda el agente antes de probarlo.");
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${getApiBase()}/custom-agents/${form.customAgentId}/test`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
        body: JSON.stringify({ topic: testTopic }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo probar.");
      setTestResult(data.test);
      setMessage(data.test?.status === "passed" ? "Prueba aprobada. Ya puedes activar." : "La prueba necesita ajustes.");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function activateAgent() {
    if (!form.customAgentId) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${getApiBase()}/custom-agents/${form.customAgentId}/activate`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo activar.");
      setMessage("Agente activado. Ya aparece en Nuevo video.");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function archiveAgent() {
    if (!form.customAgentId) return;
    if (!window.confirm("Archivar oculta el agente, pero no borra proyectos existentes. ¿Continuar?")) return;
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${getApiBase()}/custom-agents/${form.customAgentId}/archive`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo archivar.");
      setMessage("Agente archivado.");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!CUSTOM_AGENTS_ENABLED) {
    return <div className="cf-card" style={{ padding: "var(--s-7)" }}>Agentes personalizados desactivados.</div>;
  }

  if (!admin) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", color: "var(--paper-dim)" }}>
        Esta herramienta es solo para admin.
      </div>
    );
  }

  return (
    <div style={{ paddingBottom: "var(--s-7)" }}>
      <header className="cf-fade" style={{ marginBottom: "var(--s-6)" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "var(--ember)",
            font: "var(--t-mono-sm)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            marginBottom: 10,
          }}
        >
          <Icon name="settings" size={16} /> Agentes
        </div>
        <h1
          className="cf-display"
          style={{
            margin: 0,
            fontFamily: "var(--font-display)",
            fontStyle: "italic",
            fontWeight: 700,
            lineHeight: 0.95,
          }}
        >
          Constructor seguro
        </h1>
        <p style={{ color: "var(--paper-dim)", margin: "12px 0 0", maxWidth: 780, lineHeight: 1.5 }}>
          Crea agentes desde plantillas madre bloqueadas. El briefing compila un prompt profesional, se prueba y solo entonces puede activarse para proyectos reales.
        </p>
      </header>

      {(error || message) && (
        <div
          className="cf-card"
          style={{
            padding: "14px 16px",
            marginBottom: "var(--s-5)",
            borderColor: error ? "var(--bad)" : "rgba(99, 214, 151, 0.45)",
            color: error ? "var(--bad)" : "var(--ok)",
          }}
        >
          {error || message}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "320px minmax(0, 1fr)", gap: "var(--s-5)", alignItems: "start" }}>
        <aside className="cf-card" style={{ padding: "var(--s-4)", position: "sticky", top: 24 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <div style={{ font: "var(--t-mono-sm)", color: "var(--paper-mute)", letterSpacing: "0.16em", textTransform: "uppercase" }}>
              Mis agentes
            </div>
            <button className="cf-btn cf-btn--secondary cf-btn--sm" onClick={newAgent}>
              <Icon name="plus" size={14} /> Crear
            </button>
          </div>

          {loading && <div style={{ color: "var(--paper-dim)" }}>Cargando...</div>}
          {!loading && agents.length === 0 && (
            <div style={{ color: "var(--paper-dim)", font: "var(--t-caption)", lineHeight: 1.45 }}>
              Todavia no hay agentes personalizados.
            </div>
          )}
          <div style={{ display: "grid", gap: 8 }}>
            {agents.map((agent) => {
              const active = selectedId === agent.customAgentId;
              return (
                <button
                  key={agent.customAgentId}
                  type="button"
                  onClick={() => selectExistingAgent(agent)}
                  style={{
                    textAlign: "left",
                    padding: 12,
                    borderRadius: "var(--r-2)",
                    border: active ? `1px solid ${agent.color || "var(--ember)"}` : "1px solid var(--rule-1)",
                    background: active ? "var(--ember-tint)" : "var(--ink-0)",
                    color: "var(--paper)",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 8 }}>
                    <strong>{agent.name}</strong>
                    <StatusBadge status={agent.status} />
                  </div>
                  <div style={{ color: "var(--paper-dim)", font: "var(--t-caption)", lineHeight: 1.35 }}>
                    {agent.description || agent.templateKey}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <main style={{ display: "grid", gap: "var(--s-5)" }}>
          <section className="cf-card" style={{ padding: "var(--s-5)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: "var(--s-5)" }}>
              <div>
                <div style={{ font: "var(--t-mono-sm)", color: "var(--paper-mute)", letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 6 }}>
                  Briefing estructurado
                </div>
                <h2 style={{ margin: 0, color: "var(--paper)", font: "var(--t-h2)" }}>
                  {form.customAgentId ? "Editar agente" : "Crear agente"}
                </h2>
              </div>
              {selectedAgent && <StatusBadge status={selectedAgent.status} />}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14 }}>
              <label>
                <span className="cf-label">Plantilla</span>
                <select className="cf-input" value={form.templateKey} onChange={(e) => updateField("templateKey", e.target.value)}>
                  {templates.map((template) => (
                    <option key={template.templateKey} value={template.templateKey}>
                      {template.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="cf-label">Nombre</span>
                <input className="cf-input" value={form.name} onChange={(e) => updateField("name", e.target.value)} placeholder="Ej. Crimen corporativo" />
              </label>
              <label>
                <span className="cf-label">Descripcion</span>
                <input className="cf-input" value={form.description} onChange={(e) => updateField("description", e.target.value)} placeholder="Qué hace este agente" />
              </label>
              <label>
                <span className="cf-label">Categoria</span>
                <input className="cf-input" value={form.category} onChange={(e) => updateField("category", e.target.value)} placeholder="history, wellness, business..." />
              </label>
              <label>
                <span className="cf-label">Color</span>
                <input className="cf-input" type="color" value={form.color} onChange={(e) => updateField("color", e.target.value)} style={{ height: 52, padding: 10 }} />
              </label>
              <label>
                <span className="cf-label">Monograma</span>
                <input className="cf-input" value={form.monogram} maxLength={4} onChange={(e) => updateField("monogram", e.target.value)} />
              </label>
            </div>

            {selectedTemplate && (
              <div style={{ marginTop: 12, color: "var(--paper-dim)", font: "var(--t-caption)", lineHeight: 1.45 }}>
                Pipeline: {selectedTemplate.platform} · {selectedTemplate.format} · base {selectedTemplate.baseAgentFile}
              </div>
            )}

            <div style={{ display: "grid", gap: 14, marginTop: "var(--s-5)" }}>
              {[
                ["niche", "Nicho", "Ej. historias de fraudes corporativos y caidas empresariales"],
                ["audience", "Audiencia", "A quién le habla y qué ya sabe"],
                ["promise", "Promesa", "Qué transformación o claridad entrega"],
                ["tone", "Tono", "Cinemático, sobrio, íntimo, irónico..."],
                ["styleReferences", "Referencias de estilo", "Una por línea"],
                ["mustInclude", "Debe incluir", "Elementos obligatorios, uno por línea"],
                ["mustAvoid", "Debe evitar", "Límites de estilo y seguridad, uno por línea"],
                ["visualIdentity", "Identidad visual", "Metáforas, paleta, composición, negativos visuales"],
                ["safetyNotes", "Seguridad", "Límites médicos, legales, financieros, reputacionales..."],
              ].map(([field, label, placeholder]) => (
                <label key={field}>
                  <span className="cf-label">{label}</span>
                  <textarea
                    className="cf-input"
                    value={form.brief[field]}
                    onChange={(e) => updateBrief(field, e.target.value)}
                    placeholder={placeholder}
                    rows={field === "visualIdentity" || field === "safetyNotes" ? 4 : 3}
                    style={{ resize: "vertical" }}
                  />
                </label>
              ))}
              <label>
                <span className="cf-label">Temas de ejemplo</span>
                <textarea
                  className="cf-input"
                  value={form.exampleTopics}
                  onChange={(e) => updateField("exampleTopics", e.target.value)}
                  placeholder="Uno por linea"
                  rows={3}
                />
              </label>
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: "var(--s-5)" }}>
              <button className="cf-btn cf-btn--secondary" onClick={compilePrompt} disabled={saving}>
                <Icon name="cpu" size={16} /> Compilar prompt
              </button>
              <button className="cf-btn cf-btn--primary" onClick={saveAgent} disabled={saving}>
                <Icon name="check" size={16} /> {form.customAgentId ? "Guardar cambios" : "Guardar borrador"}
              </button>
              {form.customAgentId && (
                <button className="cf-btn cf-btn--ghost" onClick={archiveAgent} disabled={saving}>
                  <Icon name="trash" size={16} /> Archivar
                </button>
              )}
            </div>
          </section>

          <section className="cf-card" style={{ padding: "var(--s-5)" }}>
            <div style={{ font: "var(--t-mono-sm)", color: "var(--paper-mute)", letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 12 }}>
              Validacion y prompt compilado
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "260px minmax(0, 1fr)", gap: "var(--s-4)" }}>
              <div>
                <div style={{ fontFamily: "var(--font-display)", fontSize: 46, fontWeight: 800, color: compiled?.validation?.status === "passed" ? "var(--ok)" : "var(--ember)" }}>
                  {compiled?.validation?.score ?? selectedAgent?.validation?.score ?? 0}
                </div>
                <div style={{ color: "var(--paper-dim)", marginBottom: 14 }}>
                  {compiled?.validation?.status || selectedAgent?.validation?.status || "sin compilar"}
                </div>
                {(compiled?.validation?.issues || selectedAgent?.validation?.issues || []).map((issue) => (
                  <div key={issue} style={{ color: "var(--bad)", font: "var(--t-caption)", marginBottom: 6 }}>
                    {issue}
                  </div>
                ))}
                {(compiled?.validation?.warnings || selectedAgent?.validation?.warnings || []).map((warning) => (
                  <div key={warning} style={{ color: "var(--paper-dim)", font: "var(--t-caption)", marginBottom: 6 }}>
                    {warning}
                  </div>
                ))}
              </div>
              <textarea
                className="cf-input"
                readOnly
                value={compiled?.compiledPrompt || selectedAgent?.compiledPrompt || ""}
                placeholder="Compila el briefing para revisar el prompt profesional. No se edita libremente en v1."
                rows={18}
                style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.55, resize: "vertical" }}
              />
            </div>
          </section>

          <section className="cf-card" style={{ padding: "var(--s-5)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: "var(--s-4)" }}>
              <div>
                <div style={{ font: "var(--t-mono-sm)", color: "var(--paper-mute)", letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 6 }}>
                  Prueba obligatoria
                </div>
                <h2 style={{ margin: 0, color: "var(--paper)", font: "var(--t-h2)" }}>Preview sin producir video</h2>
              </div>
              {testResult?.status && <StatusBadge status={testResult.status === "passed" ? "active" : "draft"} />}
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: "var(--s-4)" }}>
              <input
                className="cf-input"
                value={testTopic}
                onChange={(e) => setTestTopic(e.target.value)}
                placeholder={form.exampleTopics.split("\n").find(Boolean) || "Tema de prueba"}
                style={{ flex: "1 1 320px" }}
              />
              <button className="cf-btn cf-btn--secondary" onClick={runTest} disabled={saving || !form.customAgentId}>
                <Icon name="play" size={16} /> Probar
              </button>
              <button className="cf-btn cf-btn--primary" onClick={activateAgent} disabled={saving || testResult?.status !== "passed"}>
                <Icon name="check" size={16} /> Activar
              </button>
              <button
                className="cf-btn cf-btn--ghost"
                onClick={() => router.push(`/dashboard/new?agentId=${encodeURIComponent(form.customAgentId)}`)}
                disabled={selectedAgent?.status !== "active"}
              >
                <Icon name="arrowRight" size={16} /> Usar en nuevo video
              </button>
            </div>
            {testResult && (
              <div style={{ display: "grid", gridTemplateColumns: "320px minmax(0, 1fr)", gap: "var(--s-4)" }}>
                <div style={{ display: "grid", gap: 8 }}>
                  {Object.entries(testResult.scores || {}).map(([key, value]) => (
                    <ScoreLine key={key} label={key} value={value} />
                  ))}
                  {(testResult.issues || []).map((issue) => (
                    <div key={issue} style={{ color: "var(--bad)", font: "var(--t-caption)" }}>{issue}</div>
                  ))}
                </div>
                <div style={{ whiteSpace: "pre-wrap", color: "var(--paper-dim)", lineHeight: 1.65 }}>
                  {testResult.scriptPreview}
                </div>
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}
