"use client";
import Image from "next/image";

/**
 * ScenesTab (presentacional).
 *
 * Recibe del container:
 *   - project: necesario para project.scenes + project.status
 *
 * Render:
 *   - empty state si no hay scenes (analizando)
 *   - contador de progreso de imágenes si está producing
 *   - grid de escenas con imageUrl o shimmer/icon según estado
 *
 * Fase 7.1: render IDÉNTICO al legacy.
 */
export default function ScenesTab({ project }) {
  const scenes = project.scenes || [];

  if (scenes.length === 0) {
    return (
      <div
        className="glass-card"
        style={{ padding: "48px", textAlign: "center" }}
      >
        <div
          style={{
            fontSize: "48px",
            marginBottom: "16px",
            animation: "pulse 2s infinite",
          }}
        >
          🎬
        </div>
        <h3
          style={{
            fontSize: "20px",
            fontWeight: "bold",
            margin: "0 0 8px 0",
          }}
        >
          Analizando Escenas
        </h3>
        <p style={{ color: "var(--text-muted)", margin: 0 }}>
          El Director de Fotografía está dividiendo tu guión en prompts
          visuales cada 5 segundos...
        </p>
      </div>
    );
  }

  const withImage = scenes.filter((s) => s.imageUrl).length;
  const total = scenes.length;

  return (
    <>
      {project.status === "producing" && (
        <div
          className="glass-card"
          style={{
            padding: "16px 24px",
            marginBottom: "24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "24px", animation: "pulse 2s infinite" }}>
              🎨
            </span>
            <div>
              <div style={{ fontSize: "14px", fontWeight: "bold" }}>
                Generando imágenes
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                {withImage} de {total} listas
              </div>
            </div>
          </div>
          <div
            style={{
              width: "120px",
              height: "8px",
              background: "var(--bg-primary)",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(withImage / total) * 100}%`,
                height: "100%",
                background:
                  "linear-gradient(90deg, var(--accent), var(--accent-secondary))",
                borderRadius: "4px",
                transition: "width 1s ease",
              }}
            />
          </div>
        </div>
      )}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: "24px",
        }}
      >
        {scenes.map((scene, idx) => (
          <div
            key={idx}
            className="glass-card"
            style={{ overflow: "hidden", transition: "all 0.3s" }}
          >
            <div
              style={{
                aspectRatio: "16/9",
                background: "var(--bg-dark)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {scene.imageUrl ? (
                <Image
                  src={scene.imageUrl}
                  alt={`Scene ${idx + 1}`}
                  fill
                  sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw"
                  style={{
                    objectFit: "cover",
                    animation: "fadeIn 0.8s ease",
                  }}
                  loading="lazy"
                  unoptimized={!/^https:\/\//.test(scene.imageUrl)}
                />
              ) : project.status === "producing" ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    position: "relative",
                    width: "100%",
                    height: "100%",
                    justifyContent: "center",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      background:
                        "linear-gradient(90deg, transparent 0%, rgba(139,92,246,0.08) 50%, transparent 100%)",
                      animation: "shimmer 2.5s infinite",
                    }}
                  />
                  <span
                    style={{
                      fontSize: "28px",
                      marginBottom: "8px",
                      animation: "pulse 3s infinite",
                    }}
                  >
                    🖌️
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      textTransform: "uppercase",
                      letterSpacing: "2px",
                      color: "var(--accent)",
                      fontWeight: "bold",
                    }}
                  >
                    Generando...
                  </span>
                </div>
              ) : (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: "24px", marginBottom: "8px" }}>
                    🎨
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      textTransform: "uppercase",
                      letterSpacing: "1px",
                      color: "var(--text-muted)",
                    }}
                  >
                    En cola
                  </span>
                </div>
              )}
              <div
                className="badge"
                style={{
                  position: "absolute",
                  top: "8px",
                  left: "8px",
                  background: "rgba(0,0,0,0.6)",
                  backdropFilter: "blur(4px)",
                }}
              >
                Escena {idx + 1}
              </div>
              {scene.imageUrl && (
                <div
                  className="badge"
                  style={{
                    position: "absolute",
                    top: "8px",
                    right: "8px",
                    background: "rgba(74,222,128,0.2)",
                    color: "#4ade80",
                    backdropFilter: "blur(4px)",
                  }}
                >
                  ✅
                </div>
              )}
            </div>
            <div style={{ padding: "16px" }}>
              <p
                style={{
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                  lineHeight: "1.5",
                  margin: 0,
                }}
              >
                {scene.prompt || scene}
              </p>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
