"use client";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div className="cf-mono-sm">ENTRANDO AL ESTUDIO</div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="cf-shell">
      <Sidebar />
      <main className="cf-main">{children}</main>
    </div>
  );
}
