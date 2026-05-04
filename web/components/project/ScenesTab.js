"use client";
import Image from "next/image";
import Icon from "@/components/Icon";

/**
 * ScenesTab — Editorial Cinematic v2.
 *
 * cf-card storyboard:
 *   - eyebrow STORYBOARD + h3 contador "N escenas · N con imagen"
 *   - lista de escenas con thumbnail 110x62 (Image si hay imageUrl,
 *     shimmer ember + Icon image si está generándose)
 *   - número Fraunces italic ember + descripción + estado
 *
 * Empty state: cf-card con Icon clapperboard + headline + texto.
 */
export default function ScenesTab({ project }) {
  const scenes = project.scenes || [];
  const totalScenes = scenes.length;
  const withImage = scenes.filter((s) => s.imageUrl).length;
  const isProducing = project.status === "producing";

  if (totalScenes === 0) {
    return (
      <div
        className="cf-card cf-fade"
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
            width: 56,
            height: 56,
            borderRadius: "var(--r-2)",
            background: "var(--ember-tint)",
            color: "var(--ember)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: "cf-pulse 2.4s ease-in-out infinite",
          }}
        >
          <Icon name="clapperboard" size={26} />
        </div>
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--ember)",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          DIRIGIENDO ESCENAS
        </div>
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontStyle: "italic",
            fontWeight: 700,
            fontSize: 28,
            margin: 0,
            color: "var(--paper)",
            letterSpacing: "-0.02em",
          }}
        >
          Storyboard en preparación
        </h3>
        <p
          style={{
            color: "var(--paper-dim)",
            margin: 0,
            maxWidth: 420,
            lineHeight: 1.5,
          }}
        >
          El director de fotografía está dividiendo tu guión en prompts
          visuales cada 5 segundos.
        </p>
      </div>
    );
  }

  return (
    <div className="cf-card cf-fade" style={{ padding: "var(--s-5)" }}>
      <div
        style={{
          marginBottom: "var(--s-5)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--paper-mute)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            STORYBOARD
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
            {totalScenes} escena{totalScenes === 1 ? "" : "s"}
            <span
              style={{
                color: "var(--paper-dim)",
                font: "var(--t-mono-sm)",
                fontFamily: "var(--font-mono)",
                fontWeight: 400,
                marginLeft: 12,
                letterSpacing: "0.06em",
              }}
            >
              · {withImage}/{totalScenes} con imagen
            </span>
          </div>
        </div>

        {isProducing && totalScenes > 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              minWidth: 200,
            }}
          >
            <div
              style={{
                flex: 1,
                height: 4,
                background: "var(--ink-2)",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${(withImage / totalScenes) * 100}%`,
                  height: "100%",
                  background: "var(--ember)",
                  boxShadow: "0 0 8px var(--ember)",
                  transition: "width var(--dur-editorial) var(--ease-out)",
                }}
              />
            </div>
            <span
              style={{
                font: "var(--t-mono-sm)",
                color: "var(--paper-dim)",
                minWidth: 36,
                textAlign: "right",
              }}
            >
              {Math.round((withImage / totalScenes) * 100)}%
            </span>
          </div>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {scenes.map((scene, idx) => {
          const isOk = !!scene.imageUrl;
          const isLast = idx === scenes.length - 1;

          return (
            <div
              key={idx}
              style={{
                display: "flex",
                gap: "var(--s-4)",
                alignItems: "flex-start",
                padding: "var(--s-4) 0",
                borderBottom: !isLast ? "1px solid var(--rule-1)" : "none",
              }}
            >
              {/* Thumbnail */}
              <div
                style={{
                  width: 120,
                  height: 68,
                  borderRadius: "var(--r-1)",
                  border: `1px solid ${isOk ? "var(--rule-2)" : "var(--rule-1)"}`,
                  flex: "none",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                  overflow: "hidden",
                  background: isOk ? "var(--ink-0)" : "var(--ink-2)",
                }}
              >
                {isOk ? (
                  <Image
                    src={scene.imageUrl}
                    alt={`Escena ${idx + 1}`}
                    fill
                    sizes="120px"
                    style={{ objectFit: "cover" }}
                    loading="lazy"
                    unoptimized={!/^https:\/\//.test(scene.imageUrl)}
                  />
                ) : isProducing ? (
                  <>
                    <Icon
                      name="image"
                      size={20}
                      style={{ color: "var(--ember)", opacity: 0.5 }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background:
                          "linear-gradient(90deg, transparent, rgba(224,83,61,0.18), transparent)",
                        animation: "cf-shimmer 1.6s linear infinite",
                      }}
                    />
                  </>
                ) : (
                  <Icon
                    name="image"
                    size={20}
                    style={{ color: "var(--paper-mute)" }}
                  />
                )}
              </div>

              {/* Meta */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: "flex",
                    gap: 12,
                    alignItems: "baseline",
                    marginBottom: 6,
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      font: "var(--t-mono)",
                      fontFamily: "var(--font-mono)",
                      color: "var(--ember)",
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                    }}
                  >
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <span
                    style={{
                      font: "var(--t-mono-sm)",
                      color: isOk ? "var(--ok)" : "var(--paper-mute)",
                      letterSpacing: "0.16em",
                      textTransform: "uppercase",
                    }}
                  >
                    {isOk ? "LISTA" : isProducing ? "GENERANDO" : "EN COLA"}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: "var(--paper)",
                    lineHeight: 1.55,
                  }}
                >
                  {typeof scene === "string" ? scene : scene.prompt || "—"}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
