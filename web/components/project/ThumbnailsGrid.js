"use client";
import Image from "next/image";

/**
 * ThumbnailsGrid (presentacional).
 *
 * Recibe del container:
 *   - thumbnails: array de { index, signed_url, label, variant, size_kb }
 *
 * Fase 7.1: render IDÉNTICO. Fase 7.2 aplicará cf-card + iconos editoriales.
 */
export default function ThumbnailsGrid({ thumbnails }) {
  if (!Array.isArray(thumbnails) || thumbnails.length === 0) return null;

  return (
    <div
      className="glass-card animate-fade-in"
      style={{ marginBottom: "32px", padding: "20px" }}
    >
      <h3
        style={{
          margin: "0 0 14px 0",
          fontSize: "16px",
          fontWeight: "bold",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        🖼️ Thumbnails sugeridos
        <span
          style={{
            fontSize: "12px",
            color: "var(--text-muted)",
            fontWeight: "normal",
          }}
        >
          {thumbnails.length} variantes 1280×720
        </span>
      </h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "16px",
        }}
      >
        {thumbnails.map((t) => (
          <div
            key={t.index}
            style={{
              background: "var(--bg-dark)",
              borderRadius: "8px",
              overflow: "hidden",
              border: "1px solid var(--border)",
            }}
          >
            <Image
              src={t.signed_url}
              alt={`Thumbnail ${t.label}`}
              width={1280}
              height={720}
              style={{
                width: "100%",
                height: "auto",
                aspectRatio: "16/9",
                objectFit: "cover",
                display: "block",
              }}
              unoptimized
            />
            <div
              style={{
                padding: "10px 12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: "12px",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>
                {t.label === "early"
                  ? "🎬 Inicio"
                  : t.label === "mid"
                    ? "🔥 Punto fuerte"
                    : "🏆 Cierre"}
                {" · "}
                {t.variant}
              </span>
              <span style={{ color: "var(--text-muted)", fontFamily: "monospace" }}>
                {t.size_kb}KB
              </span>
            </div>
            <a
              href={t.signed_url}
              download
              className="btn-secondary"
              style={{
                margin: "0 12px 12px",
                padding: "6px 10px",
                fontSize: "12px",
                textAlign: "center",
                textDecoration: "none",
                display: "block",
              }}
            >
              ⬇ Descargar
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
