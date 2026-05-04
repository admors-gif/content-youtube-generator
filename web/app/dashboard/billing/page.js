"use client";
import { useAuth } from "@/context/AuthContext";
import Icon from "@/components/Icon";

/**
 * Billing stub — Editorial Cinematic v2.
 *
 * Pendiente: integración con Stripe para gestión de suscripción real.
 * Por ahora muestra el plan actual del usuario + tabla mock de planes
 * con ember en el plan recomendado.
 */
const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "/ mes",
    credits: "1 documental",
    features: [
      "Acceso a 5 agentes",
      "Calidad estándar 1080p",
      "Sin marca de agua",
    ],
    cta: "Empezar",
    accent: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: "$19",
    period: "/ mes",
    credits: "8 documentales",
    features: [
      "Acceso a los 28 agentes",
      "Voz ElevenLabs v3 premium",
      "Shorts + thumbnails incluidos",
      "Recomendador de agentes IA",
    ],
    cta: "Más popular",
    accent: true,
  },
  {
    id: "creator",
    name: "Creator",
    price: "$49",
    period: "/ mes",
    credits: "25 documentales",
    features: [
      "Todo lo de Starter",
      "Modo podcast 2 voces",
      "Verificación de datos automática",
      "Soporte prioritario",
    ],
    cta: "Mejorar",
    accent: false,
  },
];

export default function BillingPage() {
  const { profile } = useAuth();
  const plan = (profile?.plan || "free").toLowerCase();
  const included = profile?.credits?.included ?? 0;
  const used = profile?.credits?.used ?? 0;
  const extra = profile?.credits?.extra ?? 0;
  const available = Math.max(0, included - used) + extra;

  return (
    <div>
      <header className="cf-fade" style={{ marginBottom: "var(--s-7)" }}>
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--ember)",
            marginBottom: 8,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          PLAN Y CRÉDITOS
        </div>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 0.95,
            margin: 0,
            fontSize: "clamp(36px, 5vw, 56px)",
          }}
        >
          Tu{" "}
          <em style={{ color: "var(--ember)", fontStyle: "italic" }}>
            estudio
          </em>{" "}
          a tu medida
        </h1>
      </header>

      {/* Plan actual */}
      <div
        className="cf-card cf-fade cf-fade--1"
        style={{
          padding: "var(--s-5)",
          marginBottom: "var(--s-6)",
          display: "flex",
          alignItems: "center",
          gap: "var(--s-5)",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "var(--r-2)",
            background: "var(--ember-tint)",
            color: "var(--ember)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon name="crown" size={26} />
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              marginBottom: 4,
            }}
          >
            PLAN ACTUAL
          </div>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 700,
              fontSize: 24,
              color: "var(--paper)",
              letterSpacing: "-0.02em",
            }}
          >
            {plan.toUpperCase()}
          </div>
        </div>
        <div style={{ minWidth: 200 }}>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              letterSpacing: "0.18em",
              marginBottom: 4,
            }}
          >
            CRÉDITOS
          </div>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: 24,
              color: "var(--ember)",
            }}
          >
            {used}/{included || "—"}
          </div>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-dim)",
            }}
          >
            {available} disponible{available === 1 ? "" : "s"}
            {extra > 0 ? ` · ${extra} extra` : ""}
          </div>
        </div>
      </div>

      {/* Tabla de planes */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "var(--s-4)",
          marginBottom: "var(--s-6)",
        }}
      >
        {PLANS.map((p, i) => {
          const isCurrent = plan === p.id;
          return (
            <div
              key={p.id}
              className={`cf-card cf-fade cf-fade--${i + 1}`}
              style={{
                padding: "var(--s-5)",
                position: "relative",
                border: p.accent
                  ? "1px solid var(--ember)"
                  : "1px solid var(--rule-1)",
                boxShadow: p.accent ? "0 0 24px rgba(224,83,61,0.15)" : "none",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {p.accent && (
                <span
                  className="cf-badge cf-badge--creator"
                  style={{
                    position: "absolute",
                    top: -10,
                    left: 16,
                    background: "var(--ember)",
                    color: "#0B0B0E",
                    border: "none",
                  }}
                >
                  MÁS POPULAR
                </span>
              )}
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 700,
                  fontSize: 22,
                  color: "var(--paper)",
                  marginBottom: 6,
                  letterSpacing: "-0.02em",
                }}
              >
                {p.name}
              </div>
              <div style={{ marginBottom: 16, display: "flex", alignItems: "baseline", gap: 4 }}>
                <span
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 800,
                    fontSize: 36,
                    color: p.accent ? "var(--ember)" : "var(--paper)",
                    letterSpacing: "-0.02em",
                    lineHeight: 1,
                  }}
                >
                  {p.price}
                </span>
                <span
                  style={{
                    font: "var(--t-mono-sm)",
                    color: "var(--paper-dim)",
                  }}
                >
                  {p.period}
                </span>
              </div>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  marginBottom: 16,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                }}
              >
                {p.credits}
              </div>
              <ul
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: "0 0 20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  flex: 1,
                }}
              >
                {p.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                      fontSize: 14,
                      color: "var(--paper-dim)",
                      lineHeight: 1.45,
                    }}
                  >
                    <span style={{ color: "var(--ember)", marginTop: 3 }}>
                      <Icon name="check" size={14} stroke={2} />
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
              <button
                className={`cf-btn ${p.accent ? "cf-btn--primary" : "cf-btn--ghost"}`}
                disabled={isCurrent}
                style={{
                  width: "100%",
                  justifyContent: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                {isCurrent ? (
                  <>
                    <Icon name="check" size={14} /> Plan actual
                  </>
                ) : (
                  p.cta
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Footer note */}
      <div
        className="cf-card"
        style={{
          padding: "var(--s-4) var(--s-5)",
          display: "flex",
          alignItems: "center",
          gap: 12,
          color: "var(--paper-dim)",
          fontSize: 13,
        }}
      >
        <Icon
          name="alert"
          size={16}
          style={{ color: "var(--warn)", flexShrink: 0 }}
        />
        <span>
          Próximamente: gestión completa de tu suscripción, facturación y
          créditos extra. Por ahora los upgrades los procesamos manualmente
          — escríbenos.
        </span>
      </div>
    </div>
  );
}
