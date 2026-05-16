import Link from "next/link";

export const metadata = {
  title: "Sin conexión — Content Factory",
};

export default function OfflinePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "var(--s-6)",
        background:
          "radial-gradient(circle at 50% 0%, rgba(224,83,61,0.16), transparent 42%), var(--ink-0)",
      }}
    >
      <section
        className="cf-card"
        style={{
          width: "min(560px, 100%)",
          padding: "var(--s-7)",
          textAlign: "left",
        }}
      >
        <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 14 }}>
          MODO OFFLINE
        </div>
        <h1 className="cf-h1" style={{ margin: 0, fontStyle: "italic" }}>
          Sin conexión
        </h1>
        <p className="cf-body-lg" style={{ marginTop: 18 }}>
          Content Factory necesita internet para crear, producir y sincronizar proyectos.
          Puedes volver al estudio cuando recuperes conexión.
        </p>
        <Link
          href="/dashboard"
          className="cf-btn cf-btn--primary"
          style={{ marginTop: 24, textDecoration: "none" }}
        >
          Volver al dashboard
        </Link>
      </section>
    </main>
  );
}
