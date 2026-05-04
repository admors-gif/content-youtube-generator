"use client";
import Icon from "@/components/Icon";

/**
 * Gallery stub — Editorial Cinematic v2.
 *
 * Pendiente conectar con Firestore para listar imágenes generadas en
 * todos los proyectos del usuario. Por ahora muestra un empty state
 * editorial con icon image + headline italic + body explicativo.
 */
export default function GalleryPage() {
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
          GALERÍA
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
            archivo
          </em>{" "}
          visual
        </h1>
        <p
          style={{
            color: "var(--paper-dim)",
            margin: "12px 0 0",
            maxWidth: 580,
            lineHeight: 1.5,
          }}
        >
          Cada escena que el estudio compone queda guardada acá — para
          reutilizar, descargar o inspirarte la próxima.
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
          <Icon name="image" size={28} />
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
          Galería en producción
        </h2>
        <p
          style={{
            color: "var(--paper-dim)",
            maxWidth: 460,
            margin: 0,
            lineHeight: 1.5,
          }}
        >
          Aquí verás todas las imágenes generadas en tus documentales —
          buscar por agente, por tema, por color. Llegará en la próxima
          actualización.
        </p>
      </div>
    </div>
  );
}
