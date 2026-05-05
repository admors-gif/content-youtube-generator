"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({ error, reset }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="es">
      <body>
        <main
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            padding: 24,
            background: "#11110f",
            color: "#f7f1e8",
            fontFamily: "system-ui, sans-serif",
          }}
        >
          <section style={{ width: "min(100%, 420px)" }}>
            <p
              style={{
                margin: "0 0 10px",
                color: "#e0533d",
                fontSize: 12,
                fontWeight: 800,
                letterSpacing: 0,
                textTransform: "uppercase",
              }}
            >
              Error inesperado
            </p>
            <h1
              style={{
                margin: 0,
                fontSize: 34,
                lineHeight: 1.05,
                letterSpacing: 0,
              }}
            >
              Algo se interrumpió.
            </h1>
            <p style={{ margin: "14px 0 22px", color: "#bdb4a7", lineHeight: 1.6 }}>
              Recarga esta vista para continuar.
            </p>
            <button
              type="button"
              onClick={() => reset()}
              style={{
                minHeight: 44,
                border: "1px solid rgba(247,241,232,.22)",
                background: "#e0533d",
                color: "#11110f",
                padding: "0 18px",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Reintentar
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
