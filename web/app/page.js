"use client";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { SYSTEM_AGENTS } from "@/lib/agents";
import { AgentMonogram } from "@/lib/agentVisual";
import Icon from "@/components/Icon";

/**
 * Landing pública v2 — Editorial Cinematic.
 * Preserva el redirect a /dashboard si el usuario está logueado.
 *
 * 5 secciones: header sticky + hero radial ember + process strip 4
 * pasos + agent preview 8 reales + pricing 3 cards + footer.
 */

const PROCESS_STEPS = [
  {
    n: "01",
    t: "Eliges agente",
    d: "28 especialistas: True Crime, Horror Histórico, Conspiraciones, Civilizaciones Perdidas…",
  },
  {
    n: "02",
    t: "Cuentas el tema",
    d: 'Una frase basta. Ej.: "La Peste Negra de 1347 y los pogromos antisemitas".',
  },
  {
    n: "03",
    t: "El agente investiga",
    d: "Cita fuentes verificables. Tú decides si lo apruebas o reescribes.",
  },
  {
    n: "04",
    t: "Producción y entrega",
    d: "Voz ElevenLabs, imágenes, montaje. MP4 + shorts + thumbnails.",
  },
];

const PRICING_PLANS = [
  {
    t: "Free",
    p: "€0",
    sub: "/mes",
    f: ["3 documentales/mes", "Resolución 720p", "Marca de agua Content Factory"],
    cta: "Empezar",
    highlight: false,
    badge: "free",
  },
  {
    t: "Starter",
    p: "€29",
    sub: "/mes",
    f: [
      "15 documentales/mes",
      "Resolución 1080p",
      "Sin marca de agua",
      "Soporte por email",
    ],
    cta: "Probar 14 días gratis",
    highlight: true,
    badge: "starter",
  },
  {
    t: "Creator",
    p: "€99",
    sub: "/mes",
    f: [
      "Documentales ilimitados",
      "Resolución 4K",
      "Voz personalizada",
      "Acceso a 28 agentes",
      "Soporte prioritario",
    ],
    cta: "Empezar",
    highlight: false,
    badge: "creator",
  },
];

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  const goLogin = () => router.push("/login");

  // 8 agentes representativos (uno por bucket de 4)
  const featured = SYSTEM_AGENTS.filter(
    (_, i) => i % Math.ceil(SYSTEM_AGENTS.length / 8) === 0,
  ).slice(0, 8);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--ink-0)",
        color: "var(--paper)",
      }}
    >
      {/* Header sticky */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          backdropFilter: "blur(12px)",
          background: "rgba(11, 11, 14, 0.7)",
          borderBottom: "1px solid var(--rule-1)",
          padding: "14px 48px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 800,
              fontSize: 9,
              letterSpacing: "0.22em",
              color: "var(--paper-dim)",
            }}
          >
            CONTENT
          </span>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 800,
              fontSize: 22,
              color: "var(--paper)",
            }}
          >
            Factory
            <span
              style={{
                display: "inline-block",
                width: 7,
                height: 7,
                background: "var(--ember)",
                marginLeft: 2,
              }}
            />
          </span>
        </div>
        <nav
          style={{
            display: "flex",
            gap: 28,
            font: "var(--t-caption)",
            color: "var(--paper-dim)",
          }}
        >
          <a href="#agentes" style={{ color: "inherit", textDecoration: "none" }}>
            Agentes
          </a>
          <a href="#proceso" style={{ color: "inherit", textDecoration: "none" }}>
            Cómo funciona
          </a>
          <a href="#precios" style={{ color: "inherit", textDecoration: "none" }}>
            Precios
          </a>
        </nav>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="cf-btn cf-btn--ghost cf-btn--sm" onClick={goLogin}>
            Entrar
          </button>
          <button
            className="cf-btn cf-btn--primary cf-btn--sm"
            onClick={goLogin}
          >
            Empezar gratis
          </button>
        </div>
      </header>

      {/* Hero */}
      <section
        style={{
          position: "relative",
          padding: "120px 48px 96px",
          textAlign: "center",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at 50% 30%, rgba(224,83,61,0.20), transparent 60%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{ position: "relative", maxWidth: 980, margin: "0 auto" }}
          className="cf-fade"
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 14px",
              borderRadius: "var(--r-pill)",
              border: "1px solid var(--rule-1)",
              background: "var(--ink-1)",
              font: "var(--t-mono-sm)",
              color: "var(--paper-dim)",
              marginBottom: 32,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--ok)",
              }}
            />
            {SYSTEM_AGENTS.length} AGENTES ACTIVOS · ÚLTIMO PROYECTO HACE 4 MIN
          </div>
          <h1
            style={{
              font: "var(--t-display)",
              fontSize: "clamp(56px, 8vw, 112px)",
              margin: 0,
              lineHeight: 0.92,
              letterSpacing: "-0.02em",
              fontStyle: "italic",
              fontWeight: 800,
            }}
          >
            Veintiocho agentes.
            <br />
            <em style={{ color: "var(--ember)" }}>Un documental.</em>
            <br />
            Doce minutos.
          </h1>
          <p
            style={{
              font: "var(--t-body-lg)",
              fontSize: 22,
              color: "var(--paper-dim)",
              maxWidth: 640,
              margin: "32px auto 0",
              lineHeight: 1.5,
              textWrap: "balance",
            }}
          >
            Investigación, guion, voz, imágenes y montaje — todo en una sola
            sesión. Tres documentales gratis al mes. Sin tarjeta.
          </p>
          <div
            style={{
              marginTop: 44,
              display: "flex",
              justifyContent: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <button
              className="cf-btn cf-btn--primary"
              onClick={goLogin}
              style={{ padding: "14px 28px", fontSize: 16 }}
            >
              Crear mi primer documental{" "}
              <Icon name="arrowRight" size={18} />
            </button>
            <button
              className="cf-btn cf-btn--ghost"
              style={{ padding: "14px 28px", fontSize: 16 }}
            >
              <Icon name="play" size={14} /> Ver demo (1:42)
            </button>
          </div>
        </div>
      </section>

      {/* Proceso */}
      <section
        id="proceso"
        style={{
          padding: "96px 48px",
          borderTop: "1px solid var(--rule-1)",
          maxWidth: 1280,
          margin: "0 auto",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: 64,
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div>
            <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 12 }}>
              EL PROCESO
            </div>
            <h2 className="cf-h1" style={{ margin: 0, maxWidth: 560 }}>
              De idea a publicación en{" "}
              <em style={{ color: "var(--ember)" }}>una sesión</em>.
            </h2>
          </div>
          <div className="cf-mono-sm">TIEMPO PROMEDIO · 12 MIN 04 SEG</div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "var(--s-4)",
          }}
        >
          {PROCESS_STEPS.map((s, i) => (
            <div
              key={s.n}
              className={`cf-card cf-fade cf-fade--${i + 1}`}
              style={{ padding: "var(--s-5)" }}
            >
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 800,
                  fontSize: 56,
                  color: "var(--ember)",
                  lineHeight: 1,
                  marginBottom: 16,
                }}
              >
                {s.n}
              </div>
              <div className="cf-h3" style={{ marginBottom: 8 }}>
                {s.t}
              </div>
              <div className="cf-caption" style={{ color: "var(--paper-dim)", lineHeight: 1.5 }}>
                {s.d}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Agentes preview */}
      <section
        id="agentes"
        style={{
          padding: "96px 48px",
          borderTop: "1px solid var(--rule-1)",
          background: "var(--ink-1)",
        }}
      >
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 12 }}>
              EL ELENCO
            </div>
            <h2 className="cf-h1" style={{ margin: 0 }}>
              Veintiocho{" "}
              <em style={{ color: "var(--ember)" }}>especialistas</em>.
            </h2>
            <p
              className="cf-body-lg"
              style={{ maxWidth: 540, margin: "12px auto 0" }}
            >
              Cada agente está entrenado en su género — voz, ritmo, archivo,
              fuentes.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "var(--s-3)",
            }}
          >
            {featured.map((a, i) => (
              <button
                key={a.agentId}
                onClick={goLogin}
                className={`cf-fade cf-fade--${(i % 4) + 1}`}
                style={{
                  all: "unset",
                  cursor: "pointer",
                  position: "relative",
                  overflow: "hidden",
                  background: "var(--ink-0)",
                  border: "1px solid var(--rule-1)",
                  borderRadius: "var(--r-3)",
                  padding: "var(--s-5)",
                  transition: "border-color var(--dur-base) var(--ease-out)",
                  display: "block",
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
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 2,
                    background: a.color,
                  }}
                />
                <AgentMonogram
                  agent={a}
                  size={44}
                  style={{ marginBottom: 14 }}
                />
                <div
                  className="cf-h3"
                  style={{ fontSize: 16, marginBottom: 4 }}
                >
                  {a.name}
                </div>
                <div className="cf-caption" style={{ lineHeight: 1.5 }}>
                  {a.description?.slice(0, 90)}
                  {a.description && a.description.length > 90 ? "…" : ""}
                </div>
              </button>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 48 }}>
            <button className="cf-btn cf-btn--secondary" onClick={goLogin}>
              Ver los {SYSTEM_AGENTS.length} agentes <Icon name="arrowRight" size={16} />
            </button>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section
        id="precios"
        style={{
          padding: "96px 48px",
          borderTop: "1px solid var(--rule-1)",
          textAlign: "center",
          maxWidth: 1280,
          margin: "0 auto",
        }}
      >
        <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 12 }}>
          PRECIOS
        </div>
        <h2 className="cf-h1" style={{ margin: 0, marginBottom: 48 }}>
          Tres planes. Cero sorpresas.
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "var(--s-4)",
            textAlign: "left",
          }}
        >
          {PRICING_PLANS.map((plan) => (
            <div
              key={plan.t}
              className="cf-card"
              style={{
                padding: "var(--s-6)",
                borderColor: plan.highlight ? "var(--ember)" : "var(--rule-1)",
                boxShadow: plan.highlight
                  ? "0 0 0 4px var(--ember-glow)"
                  : "var(--shadow-1)",
                position: "relative",
              }}
            >
              {plan.highlight && (
                <div
                  style={{
                    position: "absolute",
                    top: -12,
                    right: 24,
                    font: "var(--t-mono-sm)",
                    color: "var(--ember)",
                    background: "var(--ink-0)",
                    padding: "4px 10px",
                    border: "1px solid var(--ember)",
                    borderRadius: "var(--r-pill)",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  MÁS POPULAR
                </div>
              )}
              <span className={`cf-badge cf-badge--${plan.badge}`}>
                {plan.t.toUpperCase()}
              </span>
              <div
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 6,
                  marginTop: 16,
                  marginBottom: 24,
                }}
              >
                <span
                  style={{
                    font: "var(--t-display)",
                    fontSize: 64,
                    color: "var(--paper)",
                    lineHeight: 1,
                    fontStyle: "italic",
                    fontWeight: 800,
                  }}
                >
                  {plan.p}
                </span>
                <span
                  style={{
                    font: "var(--t-body)",
                    color: "var(--paper-mute)",
                  }}
                >
                  {plan.sub}
                </span>
              </div>
              <ul
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: "0 0 32px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                {plan.f.map((item) => (
                  <li
                    key={item}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 10,
                      font: "var(--t-body)",
                      color: "var(--paper-dim)",
                    }}
                  >
                    <Icon
                      name="check"
                      size={16}
                      style={{ color: "var(--ember)", marginTop: 4 }}
                    />
                    {item}
                  </li>
                ))}
              </ul>
              <button
                onClick={goLogin}
                className={`cf-btn ${plan.highlight ? "cf-btn--primary" : "cf-btn--secondary"}`}
                style={{ width: "100%", justifyContent: "center" }}
              >
                {plan.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          padding: "48px",
          borderTop: "1px solid var(--rule-1)",
          display: "flex",
          justifyContent: "space-between",
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          flexWrap: "wrap",
          gap: 16,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        <div>© 2026 CONTENT FACTORY</div>
        <div style={{ display: "flex", gap: 28 }}>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
            TÉRMINOS
          </a>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
            PRIVACIDAD
          </a>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
            BLOG
          </a>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
            SOPORTE
          </a>
        </div>
      </footer>
    </div>
  );
}
