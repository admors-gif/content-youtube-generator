"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Icon from "@/components/Icon";
import { getCreditCounts } from "@/lib/credits";
import { isAdminUser } from "@/lib/admin";

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
  { id: "publications", icon: "listChecks", label: "Publicaciones", href: "/dashboard/publications" },
  { id: "gallery",   icon: "image",     label: "Galería",         href: "/dashboard/gallery" },
  { id: "library",   icon: "film",      label: "Biblioteca",      href: "/dashboard/library" },
  { id: "billing",   icon: "coins",     label: "Plan y créditos", href: "/dashboard/billing" },
];

const RADAR_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_RADAR_ENABLED !== "false";
const KNOWLEDGE_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_KNOWLEDGE_ENABLED !== "false";
const CUSTOM_AGENTS_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_CUSTOM_AGENTS_ENABLED !== "false";
const SOURCE_VIDEO_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_SOURCE_VIDEO_ENABLED !== "false";

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

function NavLink({ item, isActive, onNavigate }) {
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
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
  const { total, remaining } = getCreditCounts(profile);
  const isActivationPending = remaining <= 0 && total <= 0;
  const pct =
    total > 0
      ? Math.min(100, Math.max(0, (remaining / total) * 100))
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
        {isActivationPending
          ? "ACTIVACIÓN PENDIENTE"
          : `CRÉDITOS · ${remaining}/${total || "—"}`}
      </div>
      {isActivationPending && (
        <div
          style={{
            color: "var(--paper-dim)",
            fontSize: 12,
            lineHeight: 1.35,
            marginBottom: 10,
          }}
        >
          Solicita acceso antes de producir.
        </div>
      )}
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
        {isActivationPending ? "Solicitar activación" : "Mejorar plan"}
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
  const { user, profile, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const admin = isAdminUser(user, profile);
  const navItems = admin
    ? [
        ...NAV.slice(0, 2),
        ...(CUSTOM_AGENTS_ENABLED ? [{ id: "agents", icon: "settings", label: "Agentes", href: "/dashboard/agents" }] : []),
        ...(SOURCE_VIDEO_ENABLED ? [{ id: "inspiration", icon: "clapperboard", label: "Inspiración", href: "/dashboard/inspiration" }] : []),
        ...(RADAR_ENABLED ? [{ id: "radar", icon: "trendingUp", label: "Radar", href: "/dashboard/radar" }] : []),
        ...(KNOWLEDGE_ENABLED ? [{ id: "knowledge", icon: "bookOpen", label: "Conocimiento", href: "/dashboard/knowledge" }] : []),
        { id: "topics", icon: "fileText", label: "Temas", href: "/dashboard/topics" },
        ...NAV.slice(2),
        { id: "admin", icon: "lock", label: "Admin", href: "/dashboard/admin" },
      ]
    : NAV;

  // active = primer item cuyo href matchea el pathname
  // /dashboard sólo matchea exacto (no /dashboard/new)
  // /dashboard/new matchea /dashboard/new
  const activeId =
    navItems.find((n) =>
      n.href === "/dashboard"
        ? pathname === "/dashboard"
        : pathname?.startsWith(n.href),
    )?.id || null;

  return (
    <>
      <header className="cf-mobile-topbar">
        <button
          type="button"
          className="cf-mobile-menu-btn"
          onClick={() => setMobileOpen(true)}
          aria-label="Abrir navegación"
        >
          <Icon name="dashboard" size={18} />
        </button>
        <Link href="/dashboard" className="cf-mobile-brand" aria-label="Content Factory dashboard">
          <span>CONTENT</span>
          <strong>Factory</strong>
          <i />
        </Link>
        <Link href="/dashboard/new" className="cf-mobile-new" aria-label="Nuevo video">
          <Icon name="plus" size={18} />
        </Link>
      </header>

      {mobileOpen && (
        <button
          type="button"
          className="cf-sidebar-scrim"
          aria-label="Cerrar navegación"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`cf-sidebar ${mobileOpen ? "is-open" : ""}`}
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
          zIndex: 20,
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
          {navItems.map((n) => (
            <NavLink
              key={n.id}
              item={n}
              isActive={activeId === n.id}
              onNavigate={() => setMobileOpen(false)}
            />
          ))}
        </nav>

        <div style={{ flex: 1 }} />

        {profile && <PlanStrip profile={profile} />}
        {profile && <UserRow profile={profile} onSignOut={signOut} />}
      </aside>
    </>
  );
}
