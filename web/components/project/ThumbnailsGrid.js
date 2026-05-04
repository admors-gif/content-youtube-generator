"use client";
import Image from "next/image";
import Icon from "@/components/Icon";

/**
 * ThumbnailsGrid — Editorial Cinematic v2.
 *
 * cf-card outer con eyebrow THUMBNAILS · 16:9. Cada thumbnail en card
 * propia con Image + label mono + size + botón descargar ghost sm.
 */
const THUMB_LABELS = {
  early: "INICIO",
  mid: "PUNTO FUERTE",
  closing: "CIERRE",
};

export default function ThumbnailsGrid({ thumbnails }) {
  if (!Array.isArray(thumbnails) || thumbnails.length === 0) return null;

  return (
    <div
      className="cf-card cf-fade"
      style={{
        marginBottom: "var(--s-6)",
        padding: "var(--s-5)",
      }}
    >
      <div style={{ marginBottom: "var(--s-4)" }}>
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          THUMBNAILS · 16:9
        </div>
        <div
          style={{
            font: "var(--t-h3)",
            color: "var(--paper)",
            marginTop: 4,
            fontFamily: "var(--font-display)",
            fontWeight: 600,
          }}
        >
          {thumbnails.length} variante{thumbnails.length === 1 ? "" : "s"} ·
          1280×720
        </div>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "var(--s-4)",
        }}
      >
        {thumbnails.map((t) => (
          <div
            key={t.index}
            style={{
              background: "var(--ink-1)",
              borderRadius: "var(--r-2)",
              overflow: "hidden",
              border: "1px solid var(--rule-1)",
              display: "flex",
              flexDirection: "column",
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
              }}
            >
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper)",
                  letterSpacing: "0.12em",
                }}
              >
                {THUMB_LABELS[t.label] || (t.label || "").toUpperCase()}
                <span style={{ color: "var(--paper-dim)" }}>
                  {" · "}
                  {t.variant}
                </span>
              </span>
              <span
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                }}
              >
                {t.size_kb}KB
              </span>
            </div>
            <a
              href={t.signed_url}
              download
              className="cf-btn cf-btn--ghost cf-btn--sm"
              style={{
                margin: "0 12px 12px",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                textDecoration: "none",
              }}
            >
              <Icon name="download" size={14} /> Descargar
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
