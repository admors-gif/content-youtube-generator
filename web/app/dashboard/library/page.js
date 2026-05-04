"use client";
import Icon from "@/components/Icon";

/**
 * Library stub — Editorial Cinematic v2.
 *
 * Pendiente: catálogo de guiones, voces y estilos reutilizables del usuario.
 * Por ahora empty state editorial.
 */
export default function LibraryPage() {
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
          BIBLIOTECA
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
          Tus{" "}
          <em style={{ color: "var(--ember)", fontStyle: "italic" }}>
            recursos
          </em>{" "}
          reutilizables
        </h1>
        <p
          style={{
            color: "var(--paper-dim)",
            margin: "12px 0 0",
            maxWidth: 580,
            lineHeight: 1.5,
          }}
        >
          Guiones aprobados, voces favoritas, estilos visuales. Todo lo que
          ya hiciste, listo para volver a usar sin gastar otro crédito.
        </p>
      </header>

      <div
        className="cf-card cf-fade cf-fade--1"
        style={{
          padding: "var(--s-7)",
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
          <Icon name="bookOpen" size={28} />
        </div>
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          PRÓXIMAMENTE
        </div>
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontStyle: "italic",
            fontWeight: 700,
            fontSize: 28,
            margin: 0,
            letterSpacing: "-0.02em",
            color: "var(--paper)",
          }}
        >
          Biblioteca en producción
        </h2>
        <p
          style={{
            color: "var(--paper-dim)",
            maxWidth: 460,
            margin: 0,
            lineHeight: 1.5,
          }}
        >
          Reutiliza guiones, voces y estilos de tus producciones anteriores.
          Llegará en la próxima actualización.
        </p>
      </div>
    </div>
  );
}
