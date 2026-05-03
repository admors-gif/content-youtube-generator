"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Icon from "@/components/Icon";

/**
 * Sidebar Editorial / Cinematic — v2 design system.
 *
 * Diferencia clave vs legacy: brand "CONTENT/Factory" en Inter+Fraunces
 * italic con ember dot, navegación con icons lucide (sin emojis), active
 * state ember tint + barrita izquierda, plan strip con créditos progress
 * en ember, user row inferior con avatar Fraunces italic + logout icon.
 *
 * Las 3 rutas /dashboard/gallery, /library, /billing no existen aún —
 * se crean stubs en Fase 8. Los links navegan ahí; durante el período
 * intermedio Next.js renderiza 404.
 */

const NAV = [
  { id: "dashboard", icon: "dashboard", label: "Dashboard",       href: "/dashboard" },
  { id: "new",       icon: "sparkles",  label: "Nuevo video",     href: "/dashboard/new" },
  { id: "gallery",   icon: "image",     label: "Galería",         href: "/dashboard/gallery" },
  { id: "library",   icon: "film",      label: "Biblioteca",      href: "/dashboard/library" },
  { id: "billing",   icon: "coins",     label: "Plan y créditos", href: "/dashboard/billing" },
];

const PLAN_LABELS = {
  free:    { label: "FREE",    badgeClass: "cf-badge--free" },
  starter: { label: "STARTER", badgeClass: "cf-badge--starter" },
  creator: { label: "CREATOR", badgeClass: "cf-badge--creator" },
  pro:     { label: "PRO",     badgeClass: "cf-badge--creator" },
};

function Brand() {
  return (
    <div
      style={{
        padding: "0 6px 18px",
        borderBottom: "1px solid var(--rule-1)",
        marginBottom: "var(--s-5)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontWeight: 800,
          fontSize: 10,
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
          fontSize: 28,
          lineHeight: 0.95,
          color: "var(--paper)",
          letterSpacing: "-0.02em",
          marginTop: 2,
        }}
      >
        Factory
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            background: "var(--ember)",
            marginLeft: 3,
            verticalAlign: "baseline",
          }}
        />
      </div>
    </div>
  );
}

function NavLink({ item, isActive }) {
  return (
    <Link
      href={item.href}
      style={{
        textDecoration: "none",
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        borderRadius: "var(--r-2)",
        font: "var(--t-body)",
        fontWeight: isActive ? 600 : 400,
        color: isActive ? "var(--ember)" : "var(--paper-dim)",
        background: isActive ? "var(--ember-tint)" : "transparent",
        position: "relative",
        transition:
          "background var(--dur-base) var(--ease-out), color var(--dur-base) var(--ease-out)",
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = "var(--ink-2)";
          e.currentTarget.style.color = "var(--paper)";
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = "var(--paper-dim)";
        }
      }}
    >
      {isActive && (
        <span
          style={{
            position: "absolute",
            left: 0,
            top: 8,
            bottom: 8,
            width: 2,
            background: "var(--ember)",
            borderRadius: 2,
          }}
        />
      )}
      <Icon name={item.icon} size={18} />
      {item.label}
    </Link>
  );
}

function PlanStrip({ profile }) {
  const plan = (profile?.plan || "free").toLowerCase();
  const meta = PLAN_LABELS[plan] || PLAN_LABELS.free;
  const included = profile?.credits?.included ?? 0;
  const used = profile?.credits?.used ?? 0;
  const extra = profile?.credits?.extra ?? 0;
  const totalAvailable = Math.max(0, included - used) + extra;
  const totalCapacity = included + extra;
  const pct =
    totalCapacity > 0
      ? Math.min(100, Math.max(0, (totalAvailable / totalCapacity) * 100))
      : 0;

  return (
    <div
      className="cf-card"
      style={{
        padding: 14,
        borderRadius: "var(--r-2)",
        background:
          "linear-gradient(180deg, rgba(224,83,61,0.06), transparent 60%), var(--ink-1)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 10,
        }}
      >
        <span className={`cf-badge ${meta.badgeClass}`}>{meta.label}</span>
        <Icon name="crown" size={14} style={{ color: "var(--paper-dim)" }} />
      </div>
      <div
        style={{
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          marginBottom: 6,
        }}
      >
        CRÉDITOS · {totalAvailable}/{totalCapacity || "—"}
      </div>
      <div
        style={{
          height: 4,
          background: "var(--ink-2)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "var(--ember)",
            boxShadow: "0 0 10px var(--ember)",
            transition: "width var(--dur-editorial) var(--ease-out)",
          }}
        />
      </div>
      <Link
        href="/dashboard/billing"
        className="cf-btn cf-btn--secondary cf-btn--sm"
        style={{
          marginTop: 12,
          width: "100%",
          justifyContent: "center",
          textDecoration: "none",
        }}
      >
        Mejorar plan
      </Link>
    </div>
  );
}

function UserRow({ profile, onSignOut }) {
  const initial = profile?.displayName?.charAt(0)?.toUpperCase() || "U";
  const email = profile?.email || "";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 8px",
        borderTop: "1px solid var(--rule-1)",
        marginTop: 4,
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "var(--r-pill)",
          background: "var(--ink-3)",
          color: "var(--paper)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "var(--font-display)",
          fontStyle: "italic",
          fontWeight: 700,
          fontSize: 14,
        }}
      >
        {initial}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            font: "var(--t-caption)",
            color: "var(--paper)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {email}
        </div>
      </div>
      <button
        onClick={onSignOut}
        style={{
          all: "unset",
          cursor: "pointer",
          color: "var(--paper-mute)",
          padding: 4,
          transition: "color var(--dur-base) var(--ease-out)",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "var(--paper)")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "var(--paper-mute)")}
        aria-label="Cerrar sesión"
        title="Cerrar sesión"
      >
        <Icon name="logOut" size={16} />
      </button>
    </div>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const { profile, signOut } = useAuth();

  // active = primer item cuyo href matchea el pathname
  // /dashboard sólo matchea exacto (no /dashboard/new)
  // /dashboard/new matchea /dashboard/new
  const activeId =
    NAV.find((n) =>
      n.href === "/dashboard"
        ? pathname === "/dashboard"
        : pathname?.startsWith(n.href),
    )?.id || null;

  return (
    <aside
      style={{
        position: "fixed",
        left: 0,
        top: 0,
        bottom: 0,
        width: "var(--sidebar-w)",
        background: "var(--ink-0)",
        borderRight: "1px solid var(--rule-1)",
        padding: "24px 16px",
        display: "flex",
        flexDirection: "column",
        gap: "var(--s-3)",
        zIndex: 5,
      }}
    >
      <Brand />

      <div
        style={{
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          padding: "0 12px",
          marginBottom: 4,
        }}
      >
        NAVEGACIÓN
      </div>
      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {NAV.map((n) => (
          <NavLink key={n.id} item={n} isActive={activeId === n.id} />
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      {profile && <PlanStrip profile={profile} />}
      {profile && <UserRow profile={profile} onSignOut={signOut} />}
    </aside>
  );
}
