"use client";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import {
  collection,
  query,
  where,
  orderBy,
  onSnapshot,
  deleteDoc,
  doc,
  updateDoc,
  increment,
} from "firebase/firestore";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Icon from "@/components/Icon";
import {
  getAgent,
  getAgentColor,
  getMonogram,
} from "@/lib/agentVisual";
import { formatRelativeTime, getStatusBucket } from "@/lib/format";

/**
 * Dashboard Editorial — v2 design system.
 *
 * Preserva 100% la lógica del legacy:
 *   - useEffect con onSnapshot + fallback query sin orderBy (composite index)
 *   - handleDelete con devolución condicional de crédito (hasScript)
 *   - creditsLeft calculado igual
 *
 * Cambia SOLO la presentación: header eyebrow + display Fraunces italic,
 * stat trio en cf-card, filter strip + search, project rows con monograma
 * + status bucket (4 visuales) + meta mono + chevron + progress bar ember.
 */

const FILTERS = [
  { id: "all",         label: "Todos" },
  { id: "in_progress", label: "En curso" },
  { id: "completed",   label: "Completados" },
  { id: "failed",      label: "Fallidos" },
];

/* ── ProjectRow ─────────────────────────────────────────────────────────── */

function ProjectRow({ project, onOpen, onDelete, fadeClass }) {
  const agent = getAgent(project.agentId);
  const agentName = agent?.name || project.agentId?.replace("agent_", "")?.replace(/_/g, " ") || "Sin agente";
  const color = getAgentColor(project.agentId);
  const mono = getMonogram(project.agentId);

  const bucket = getStatusBucket(project.status);
  const isCompleted = project.status === "completed";
  const isFailed = project.status === "failed" || project.status === "error";
  const inProgress = !isCompleted && !isFailed;

  const scenes =
    project.outputs?.scenes?.length ||
    project.scenes?.length ||
    project.totalScenes ||
    0;

  const updated = formatRelativeTime(project.updatedAt || project.createdAt);
  const progressPct = Math.max(0, Math.min(100, project.progress?.percent || 0));

  return (
    <div className={`cf-fade ${fadeClass}`}>
      <div
        role="button"
        tabIndex={0}
        onClick={onOpen}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onOpen();
          }
        }}
        className="cf-card"
        style={{
          cursor: "pointer",
          display: "block",
          padding: "var(--s-5)",
          width: "100%",
          boxSizing: "border-box",
          borderRadius: "var(--r-2)",
          border: "1px solid var(--rule-1)",
          background: "var(--ink-1)",
          transition:
            "border-color var(--dur-base) var(--ease-out), transform var(--dur-base) var(--ease-out)",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "var(--rule-2)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = "var(--rule-1)";
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "var(--s-5)",
          }}
        >
          {/* Thumbnail con monograma */}
          <div
            style={{
              width: 120,
              height: 68,
              flex: "none",
              borderRadius: "var(--r-2)",
              background: `linear-gradient(135deg, ${color}33, ${color}11), var(--ink-2)`,
              border: "1px solid var(--rule-1)",
              position: "relative",
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontStyle: "italic",
                fontWeight: 800,
                fontSize: 28,
                color,
                opacity: 0.55,
                letterSpacing: "-0.02em",
                lineHeight: 1,
              }}
            >
              {mono}
            </div>
            {inProgress && progressPct > 0 && (
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  height: 2,
                  background: `linear-gradient(90deg, var(--ember) ${progressPct}%, transparent ${progressPct}%)`,
                }}
              />
            )}
          </div>

          {/* Meta */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: 6,
                flexWrap: "wrap",
              }}
            >
              <span className={`cf-badge ${bucket.cls}`}>
                {bucket.animate && (
                  <span
                    className="dot"
                    style={{
                      animation:
                        "cf-pulse 1.6s ease-in-out infinite",
                    }}
                  />
                )}
                {bucket.label}
              </span>
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                }}
              >
                {agentName}
              </span>
            </div>
            <div
              style={{
                font: "var(--t-h3)",
                color: "var(--paper)",
                marginBottom: 6,
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {project.title || "Sin título"}
            </div>
            <div
              style={{
                display: "flex",
                gap: 12,
                font: "var(--t-mono-sm)",
                color: "var(--paper-dim)",
                flexWrap: "wrap",
              }}
            >
              {scenes > 0 && (
                <>
                  <span>{scenes} escenas</span>
                  <span aria-hidden>·</span>
                </>
              )}
              {updated && <span>{updated}</span>}
            </div>
          </div>

          {/* Acciones */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              alignSelf: "center",
            }}
          >
            <button
              onClick={(e) => onDelete(e, project)}
              className="cf-btn cf-btn--ghost cf-btn--sm"
              aria-label="Eliminar proyecto"
              title="Eliminar proyecto"
              style={{
                color: "var(--paper-mute)",
                padding: "6px 8px",
              }}
            >
              <Icon name="trash" size={14} />
            </button>
            <span style={{ color: "var(--paper-mute)" }}>
              <Icon name="chevronRight" size={20} />
            </span>
          </div>
        </div>

        {/* Progress bar inferior */}
        {inProgress && (
          <div
            style={{
              marginTop: "var(--s-4)",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div
              style={{
                flex: 1,
                height: 3,
                background: "var(--ink-2)",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${progressPct}%`,
                  height: "100%",
                  background: "var(--ember)",
                  boxShadow: progressPct > 0 ? "0 0 8px var(--ember)" : "none",
                  transition: "width var(--dur-editorial) var(--ease-out)",
                }}
              />
            </div>
            <div
              style={{
                font: "var(--t-mono-sm)",
                color: "var(--paper-dim)",
                minWidth: 36,
                textAlign: "right",
              }}
            >
              {progressPct}%
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Stat ───────────────────────────────────────────────────────────────── */

function Stat({ label, value, sub, accent }) {
  return (
    <div
      className="cf-card"
      style={{
        padding: "var(--s-5)",
        flex: 1,
        minWidth: 200,
      }}
    >
      <div
        style={{
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          font: "var(--t-h1)",
          color: accent || "var(--paper)",
          marginBottom: 6,
          lineHeight: 1,
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </div>
      <div
        style={{
          font: "var(--t-caption)",
          color: "var(--paper-dim)",
        }}
      >
        {sub}
      </div>
    </div>
  );
}

/* ── DashboardPage ──────────────────────────────────────────────────────── */

export default function DashboardPage() {
  const { user, profile } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  /* PRESERVADO: delete con devolución condicional de crédito */
  const handleDelete = async (e, project) => {
    e.stopPropagation();
    const hasScript =
      (project.script?.wordCount > 0) || (project.script?.plain?.length > 0);
    const msg = hasScript
      ? `¿Eliminar "${project.title}"?\n\nEl guión ya fue generado. El crédito NO será devuelto.`
      : `¿Eliminar "${project.title}"?\n\nNo se generó guión. Se te devolverá el crédito.`;
    if (!confirm(msg)) return;
    try {
      await deleteDoc(doc(db, "projects", project.id));
      if (!hasScript) {
        await updateDoc(doc(db, "users", user.uid), {
          "credits.used": increment(-1),
        });
      }
    } catch (err) {
      alert("Error al eliminar: " + err.message);
    }
  };

  /* PRESERVADO: onSnapshot + fallback query sin orderBy */
  useEffect(() => {
    if (!user) return;
    const q = query(
      collection(db, "projects"),
      where("userId", "==", user.uid),
      orderBy("createdAt", "desc"),
    );
    const unsub = onSnapshot(
      q,
      (snap) => {
        setProjects(snap.docs.map((d) => ({ id: d.id, ...d.data() })));
        setLoadingProjects(false);
      },
      (error) => {
        console.warn(
          "Firestore index missing, using fallback query:",
          error.message,
        );
        const fallbackQ = query(
          collection(db, "projects"),
          where("userId", "==", user.uid),
        );
        const unsub2 = onSnapshot(fallbackQ, (snap) => {
          const sorted = snap.docs
            .map((d) => ({ id: d.id, ...d.data() }))
            .sort(
              (a, b) =>
                (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0),
            );
          setProjects(sorted);
          setLoadingProjects(false);
        });
        return () => unsub2();
      },
    );
    return () => unsub();
  }, [user]);

  /* PRESERVADO: créditos */
  const included = profile?.credits?.included ?? 0;
  const used = profile?.credits?.used ?? 0;
  const extra = profile?.credits?.extra ?? 0;
  const creditsLeft = Math.max(0, included - used) + extra;

  /* Métricas derivadas para el stat trio */
  const totalProjects = projects.length;
  const completedProjects = useMemo(
    () => projects.filter((p) => p.status === "completed").length,
    [projects],
  );
  const inProgressCount = useMemo(
    () =>
      projects.filter(
        (p) => !["completed", "failed", "error"].includes(p.status),
      ).length,
    [projects],
  );
  // Estimación honesta: 12 min por video producido (sin duration real en Firestore aún)
  const estimatedMinutes = completedProjects * 12;
  const hoursLabel =
    completedProjects === 0
      ? "—"
      : estimatedMinutes >= 60
        ? `${Math.floor(estimatedMinutes / 60)}h ${estimatedMinutes % 60}m`
        : `${estimatedMinutes}m`;

  /* Filtrado + búsqueda */
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return projects.filter((p) => {
      // Filtro de status
      if (filter !== "all") {
        const isCompleted = p.status === "completed";
        const isFailed = p.status === "failed" || p.status === "error";
        if (filter === "completed" && !isCompleted) return false;
        if (filter === "failed" && !isFailed) return false;
        if (filter === "in_progress" && (isCompleted || isFailed)) return false;
      }
      // Búsqueda en título o agente
      if (q) {
        const agent = getAgent(p.agentId);
        const haystack = `${p.title || ""} ${agent?.name || ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [projects, filter, search]);

  const firstName = profile?.displayName?.split(" ")[0] || "Creador";

  return (
    <div>
      {/* Header */}
      <header
        className="cf-fade"
        style={{ marginBottom: "var(--s-7)" }}
      >
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--ember)",
            marginBottom: 8,
            textTransform: "uppercase",
            letterSpacing: "0.18em",
          }}
        >
          BIENVENIDA · {firstName.toUpperCase()}
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
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              lineHeight: 0.95,
            }}
          >
            Tus{" "}
            <em
              style={{
                color: "var(--ember)",
                fontStyle: "italic",
              }}
            >
              documentales
            </em>
          </h1>
          <button
            className="cf-btn cf-btn--primary"
            onClick={() => router.push("/dashboard/new")}
            style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <Icon name="plus" size={16} />
            Nuevo documental
          </button>
        </div>
      </header>

      {/* Stat trio */}
      <div
        style={{
          display: "flex",
          gap: "var(--s-4)",
          marginBottom: "var(--s-7)",
          flexWrap: "wrap",
        }}
      >
        <div className="cf-fade cf-fade--1" style={{ flex: 1, minWidth: 200 }}>
          <Stat
            label="DOCUMENTALES"
            value={totalProjects}
            sub={
              completedProjects === 0
                ? "Aún no has producido ninguno"
                : `${completedProjects} producido${completedProjects === 1 ? "" : "s"}${inProgressCount > 0 ? ` · ${inProgressCount} en curso` : ""}`
            }
          />
        </div>
        <div className="cf-fade cf-fade--2" style={{ flex: 1, minWidth: 200 }}>
          <Stat
            label="HORAS PRODUCIDAS"
            value={hoursLabel}
            sub={
              completedProjects === 0
                ? "Crea tu primer documental"
                : "≈ 12 min por video"
            }
          />
        </div>
        <div className="cf-fade cf-fade--3" style={{ flex: 1, minWidth: 200 }}>
          <Stat
            label="CRÉDITOS"
            value={`${used}/${included || "—"}`}
            sub={
              creditsLeft === 0
                ? "Sin créditos disponibles"
                : `${creditsLeft} disponible${creditsLeft === 1 ? "" : "s"}${extra > 0 ? ` · ${extra} extra` : ""}`
            }
            accent="var(--ember)"
          />
        </div>
      </div>

      {/* Filter strip */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: "var(--s-5)",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            textTransform: "uppercase",
            letterSpacing: "0.18em",
          }}
        >
          FILTRAR
        </div>
        {FILTERS.map((f) => {
          const active = filter === f.id;
          return (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`cf-btn cf-btn--sm ${active ? "cf-btn--secondary" : "cf-btn--ghost"}`}
              style={
                active
                  ? {
                      borderColor: "var(--ember)",
                      color: "var(--ember)",
                    }
                  : undefined
              }
            >
              {f.label}
            </button>
          );
        })}
        <div style={{ flex: 1 }} />
        <div style={{ position: "relative" }}>
          <span
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--paper-mute)",
              pointerEvents: "none",
              display: "flex",
            }}
          >
            <Icon name="search" size={16} />
          </span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar título o agente"
            className="cf-input"
            style={{ paddingLeft: 36, width: 280, maxWidth: "100%" }}
          />
        </div>
      </div>

      {/* Project list */}
      {loadingProjects ? (
        <div
          style={{
            padding: "60px 0",
            textAlign: "center",
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            textTransform: "uppercase",
            letterSpacing: "0.18em",
          }}
        >
          CARGANDO PROYECTOS
        </div>
      ) : projects.length === 0 ? (
        /* Empty state ─ sin proyectos */
        <div
          className="cf-card cf-fade"
          style={{
            padding: "60px 32px",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: "var(--r-2)",
              background: "var(--ember-tint)",
              color: "var(--ember)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name="film" size={28} />
          </div>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              textTransform: "uppercase",
              letterSpacing: "0.18em",
            }}
          >
            ESTUDIO VACÍO
          </div>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 700,
              fontSize: 32,
              margin: 0,
              letterSpacing: "-0.02em",
            }}
          >
            Tu primer documental
            <br />
            está a un crédito.
          </h2>
          <p
            style={{
              color: "var(--paper-dim)",
              maxWidth: 420,
              margin: "0 auto 8px",
              lineHeight: 1.5,
            }}
          >
            Elige un agente, dale un tema y deja que el estudio escriba,
            narre y monte tu video en minutos.
          </p>
          <button
            className="cf-btn cf-btn--primary"
            onClick={() => router.push("/dashboard/new")}
            style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <Icon name="sparkles" size={16} />
            Crear mi primer documental
          </button>
        </div>
      ) : filtered.length === 0 ? (
        /* Empty state ─ filtros sin resultados */
        <div
          className="cf-card"
          style={{
            padding: "40px 24px",
            textAlign: "center",
            color: "var(--paper-dim)",
          }}
        >
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              marginBottom: 8,
              textTransform: "uppercase",
              letterSpacing: "0.18em",
            }}
          >
            SIN COINCIDENCIAS
          </div>
          <div>
            Ningún documental coincide con{" "}
            <span style={{ color: "var(--paper)" }}>
              {search ? `"${search}"` : FILTERS.find((f) => f.id === filter)?.label}
            </span>
            .
          </div>
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--s-3)",
          }}
        >
          {filtered.map((p, i) => (
            <ProjectRow
              key={p.id}
              project={p}
              fadeClass={`cf-fade--${(i % 4) + 1}`}
              onOpen={() => router.push(`/dashboard/project/${p.id}`)}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
