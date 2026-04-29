"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { href: "/dashboard", icon: "📊", label: "Dashboard" },
  { href: "/dashboard/new", icon: "✨", label: "Nuevo Video" },
  { href: "/dashboard/gallery", icon: "🖼️", label: "Galería" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { profile, signOut } = useAuth();

  return (
    <nav className="sidebar">
      {/* Brand */}
      <div style={{ padding: "0 8px 24px", borderBottom: "1px solid var(--border)", marginBottom: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent)", letterSpacing: 1.5 }}>⚡ CONTENT</div>
        <div style={{ fontSize: 20, fontWeight: 800 }}>Factory</div>
      </div>

      {/* Nav links */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {navItems.map((item) => (
          <Link key={item.href} href={item.href} className={`sidebar-link ${pathname === item.href ? "active" : ""}`}>
            <span style={{ fontSize: 18 }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </div>

      {/* Credits */}
      {profile && (
        <div style={{ marginTop: 32, padding: "16px", background: "var(--bg-card)", borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Créditos</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent)" }}>
            {Math.max(0, (profile.credits?.included || 0) - (profile.credits?.used || 0)) + (profile.credits?.extra || 0)}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>videos disponibles</div>
          <div style={{ marginTop: 8 }}>
            <span className={`badge badge-${profile.plan}`}>{profile.plan}</span>
          </div>
        </div>
      )}

      {/* User / Logout */}
      <div style={{ position: "absolute", bottom: 24, left: 16, right: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 8px", borderTop: "1px solid var(--border)", paddingTop: 16 }}>
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700 }}>
            {profile?.displayName?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{profile?.displayName || "Usuario"}</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{profile?.email}</div>
          </div>
          <button onClick={signOut} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 16 }} title="Cerrar sesión">🚪</button>
        </div>
      </div>
    </nav>
  );
}
