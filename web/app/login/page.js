"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Icon from "@/components/Icon";

/**
 * Login page — split editorial v2.
 *
 * Preserva 100% la lógica de auth del legacy:
 * - signInWithGoogle, signInWithEmail, signUpWithEmail
 * - mismo manejo de auth/invalid-credential
 * - redirect a /dashboard tras éxito
 *
 * Visual: panel izquierdo editorial (radial ember + brand + display
 * "Documentales, en serie." + 3 stats hardcoded) + panel derecho form
 * con tabs Entrar/Crear, inputs con icon adornments, Google SSO.
 *
 * Responsive: <900px colapsa a 1 columna, panel left arriba (compacto).
 */
export default function LoginPage() {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGoogle = async () => {
    try {
      setLoading(true);
      await signInWithGoogle();
      router.push("/dashboard");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEmail = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "signup") {
        await signUpWithEmail(email, password, name);
      } else {
        await signInWithEmail(email, password);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(
        err.code === "auth/invalid-credential"
          ? "Email o contraseña incorrectos"
          : err.message,
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cf-login-shell">
      {/* Panel izquierdo — editorial */}
      <div
        style={{
          position: "relative",
          background:
            "radial-gradient(ellipse at 30% 70%, rgba(224,83,61,0.18), transparent 60%), var(--ink-0)",
          padding: "64px 72px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          borderRight: "1px solid var(--rule-1)",
          minHeight: 480,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 800,
              fontSize: 11,
              letterSpacing: "0.22em",
              color: "var(--paper-dim)",
            }}
          >
            CONTENT
          </div>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 800,
              fontSize: 36,
              color: "var(--paper)",
              letterSpacing: "-0.02em",
            }}
          >
            Factory
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                background: "var(--ember)",
                marginLeft: 4,
              }}
            />
          </div>
        </div>

        <div className="cf-fade">
          <div
            style={{
              font: "var(--t-eyebrow)",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.18em",
              color: "var(--ember)",
              marginBottom: 18,
            }}
          >
            STUDIO ACCESS
          </div>
          <h1
            style={{
              font: "var(--t-display)",
              fontSize: "clamp(48px, 5vw, 72px)",
              margin: 0,
              color: "var(--paper)",
              lineHeight: 0.95,
              fontStyle: "italic",
              letterSpacing: "-0.025em",
            }}
          >
            Documentales,
            <br />
            <em style={{ color: "var(--ember)" }}>en serie.</em>
          </h1>
          <p
            style={{
              font: "var(--t-body-lg)",
              color: "var(--paper-dim)",
              maxWidth: 460,
              marginTop: 24,
              lineHeight: 1.5,
            }}
          >
            Veintiocho agentes especializados producen tu próximo documental
            mientras tú duermes. Investigación, guion, voz, montaje y
            publicación.
          </p>

          <div
            style={{
              marginTop: 48,
              display: "flex",
              gap: 32,
              flexWrap: "wrap",
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
            }}
          >
            <div>
              <div
                style={{
                  font: "var(--t-h2)",
                  color: "var(--paper)",
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 800,
                }}
              >
                2,143
              </div>
              DOCUMENTALES
            </div>
            <div>
              <div
                style={{
                  font: "var(--t-h2)",
                  color: "var(--paper)",
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 800,
                }}
              >
                28
              </div>
              AGENTES
            </div>
            <div>
              <div
                style={{
                  font: "var(--t-h2)",
                  color: "var(--paper)",
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 800,
                }}
              >
                14m
              </div>
              PROMEDIO
            </div>
          </div>
        </div>

        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            marginTop: 32,
          }}
        >
          © 2026 CONTENT FACTORY
        </div>
      </div>

      {/* Panel derecho — form */}
      <div
        style={{
          background: "var(--ink-0)",
          padding: "64px 72px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{ width: "100%", maxWidth: 380, position: "relative", zIndex: 5 }}
          className="cf-fade cf-fade--2"
        >
          {/* Tabs */}
          <div style={{ display: "flex", gap: 4, marginBottom: "var(--s-7)" }}>
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError("");
              }}
              style={{
                all: "unset",
                cursor: "pointer",
                padding: "10px 0",
                flex: 1,
                textAlign: "center",
                font: "var(--t-body)",
                fontWeight: mode === "login" ? 600 : 400,
                color: mode === "login" ? "var(--paper)" : "var(--paper-mute)",
                borderBottom: `2px solid ${
                  mode === "login" ? "var(--ember)" : "var(--rule-1)"
                }`,
                transition: "color var(--dur-base) var(--ease-out), border-color var(--dur-base) var(--ease-out)",
              }}
            >
              Entrar
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("signup");
                setError("");
              }}
              style={{
                all: "unset",
                cursor: "pointer",
                padding: "10px 0",
                flex: 1,
                textAlign: "center",
                font: "var(--t-body)",
                fontWeight: mode === "signup" ? 600 : 400,
                color: mode === "signup" ? "var(--paper)" : "var(--paper-mute)",
                borderBottom: `2px solid ${
                  mode === "signup" ? "var(--ember)" : "var(--rule-1)"
                }`,
                transition: "color var(--dur-base) var(--ease-out), border-color var(--dur-base) var(--ease-out)",
              }}
            >
              Crear cuenta
            </button>
          </div>

          <h2
            className="cf-h2"
            style={{ margin: "0 0 8px" }}
          >
            {mode === "login" ? "Bienvenida de vuelta." : "Empieza gratis."}
          </h2>
          <p
            className="cf-body"
            style={{ margin: "0 0 var(--s-6)" }}
          >
            {mode === "login"
              ? "Tres documentales gratis al mes. Sin tarjeta."
              : "Tres documentales al mes, sin tarjeta. Cancela cuando quieras."}
          </p>

          <form
            onSubmit={handleEmail}
            style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}
          >
            {mode === "signup" && (
              <label>
                <div
                  style={{
                    font: "var(--t-mono-sm)",
                    color: "var(--paper-mute)",
                    marginBottom: 6,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  NOMBRE
                </div>
                <div style={{ position: "relative" }}>
                  <Icon
                    name="user"
                    size={16}
                    style={{
                      position: "absolute",
                      left: 14,
                      top: 14,
                      color: "var(--paper-mute)",
                    }}
                  />
                  <input
                    className="cf-input"
                    type="text"
                    placeholder="Tu nombre"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    style={{ paddingLeft: 40 }}
                    disabled={loading}
                  />
                </div>
              </label>
            )}
            <label>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  marginBottom: 6,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                EMAIL
              </div>
              <div style={{ position: "relative" }}>
                <Icon
                  name="mail"
                  size={16}
                  style={{
                    position: "absolute",
                    left: 14,
                    top: 14,
                    color: "var(--paper-mute)",
                  }}
                />
                <input
                  className="cf-input"
                  type="email"
                  placeholder="tu@correo.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  style={{ paddingLeft: 40 }}
                  disabled={loading}
                  autoComplete="email"
                />
              </div>
            </label>
            <label>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  marginBottom: 6,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                CONTRASEÑA
              </div>
              <div style={{ position: "relative" }}>
                <Icon
                  name="lock"
                  size={16}
                  style={{
                    position: "absolute",
                    left: 14,
                    top: 14,
                    color: "var(--paper-mute)",
                  }}
                />
                <input
                  className="cf-input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  style={{ paddingLeft: 40 }}
                  disabled={loading}
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                />
              </div>
            </label>

            {mode === "login" && (
              <a
                href="#"
                style={{
                  font: "var(--t-caption)",
                  color: "var(--ember)",
                  alignSelf: "flex-end",
                  textDecoration: "none",
                  marginTop: 4,
                }}
              >
                ¿Olvidaste la contraseña?
              </a>
            )}

            {error && (
              <div
                role="alert"
                style={{
                  font: "var(--t-caption)",
                  color: "var(--bad)",
                  background: "rgba(216,98,90,0.08)",
                  border: "1px solid rgba(216,98,90,0.25)",
                  borderRadius: "var(--r-2)",
                  padding: "10px 14px",
                  marginTop: 4,
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="cf-btn cf-btn--primary"
              style={{ marginTop: "var(--s-3)", justifyContent: "center" }}
              disabled={loading}
            >
              {loading
                ? "Cargando…"
                : mode === "login"
                  ? "Entrar al estudio"
                  : "Crear cuenta"}
            </button>
          </form>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              margin: "var(--s-5) 0",
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            <div style={{ flex: 1, height: 1, background: "var(--rule-1)" }} />
            O CONTINÚA CON
            <div style={{ flex: 1, height: 1, background: "var(--rule-1)" }} />
          </div>
          <button
            type="button"
            onClick={handleGoogle}
            disabled={loading}
            className="cf-btn cf-btn--secondary"
            style={{ width: "100%", justifyContent: "center", gap: 10 }}
          >
            <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden>
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
            </svg>
            Continuar con Google
          </button>

          <div
            style={{
              marginTop: "var(--s-7)",
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              textAlign: "center",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            AL CONTINUAR ACEPTAS LOS{" "}
            <a href="#" style={{ color: "var(--paper-dim)" }}>
              TÉRMINOS
            </a>{" "}
            Y LA{" "}
            <a href="#" style={{ color: "var(--paper-dim)" }}>
              POLÍTICA DE PRIVACIDAD
            </a>
          </div>
        </div>
      </div>

      <style jsx>{`
        .cf-login-shell {
          min-height: 100vh;
          display: grid;
          grid-template-columns: 1fr 1fr;
        }
        @media (max-width: 900px) {
          .cf-login-shell {
            grid-template-columns: 1fr;
          }
          .cf-login-shell > div {
            padding: 32px 24px !important;
            border-right: none !important;
          }
        }
      `}</style>
    </div>
  );
}
