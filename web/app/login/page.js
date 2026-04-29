"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const router = useRouter();
  const [isSignUp, setIsSignUp] = useState(false);
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
      if (isSignUp) {
        await signUpWithEmail(email, password, name);
      } else {
        await signInWithEmail(email, password);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err.code === "auth/invalid-credential" ? "Email o contraseña incorrectos" : err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 20, background: "radial-gradient(ellipse at top, #1a1a2e 0%, #0a0a0f 70%)" }}>
      <div className="glass-card animate-fade-in" style={{ padding: 40, maxWidth: 420, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--accent)", letterSpacing: 2, marginBottom: 8 }}>⚡ CONTENT FACTORY</div>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>{isSignUp ? "Crea tu cuenta" : "Bienvenido de vuelta"}</h1>
          <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 8 }}>
            {isSignUp ? "Empieza a crear documentales con IA" : "Continúa creando contenido increíble"}
          </p>
        </div>

        {/* Google */}
        <button onClick={handleGoogle} disabled={loading} className="btn-secondary" style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, marginBottom: 20, padding: 14 }}>
          <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
          Continuar con Google
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
          <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>o</span>
          <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
        </div>

        {/* Email form */}
        <form onSubmit={handleEmail}>
          {isSignUp && (
            <input className="input-field" placeholder="Tu nombre" value={name} onChange={(e) => setName(e.target.value)} style={{ marginBottom: 12 }} required />
          )}
          <input className="input-field" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ marginBottom: 12 }} required />
          <input className="input-field" type="password" placeholder="Contraseña" value={password} onChange={(e) => setPassword(e.target.value)} style={{ marginBottom: 16 }} required minLength={6} />

          {error && <div style={{ color: "var(--danger)", fontSize: 13, marginBottom: 12, textAlign: "center" }}>{error}</div>}

          <button type="submit" className="btn-glow" disabled={loading} style={{ width: "100%", marginBottom: 16 }}>
            {loading ? "Cargando..." : isSignUp ? "Crear cuenta" : "Iniciar sesión"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-muted)" }}>
          {isSignUp ? "¿Ya tienes cuenta? " : "¿No tienes cuenta? "}
          <span onClick={() => { setIsSignUp(!isSignUp); setError(""); }} style={{ color: "var(--accent)", cursor: "pointer", fontWeight: 600 }}>
            {isSignUp ? "Inicia sesión" : "Regístrate gratis"}
          </span>
        </p>
      </div>
    </div>
  );
}
