"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";
import { EventProvider } from "@/contexts/EventContext";
import { EventSelector } from "@/components/EventSelector";

const nav = [
  { href: "/dashboard", label: "Overview" },
  { href: "/messages", label: "Messages" },
  { href: "/events", label: "Events" },
  { href: "/booths", label: "Booths" },
  { href: "/analytics", label: "Analytics" },
  { href: "/booth-qr", label: "Booth QR" },
];

function ShellInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 240,
          borderRight: "1px solid var(--border)",
          padding: "1.5rem 1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
        }}
      >
        <div style={{ marginBottom: "0.5rem" }}>
          <strong style={{ color: "var(--accent)" }}>X- Booth</strong>
          <p style={{ fontSize: "0.75rem", color: "var(--muted)" }}>Operator Console</p>
        </div>

        <EventSelector />

        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            style={{
              padding: "0.5rem 0.75rem",
              borderRadius: 8,
              background: pathname === item.href ? "var(--surface)" : "transparent",
              color: pathname === item.href ? "var(--text)" : "var(--muted)",
            }}
          >
            {item.label}
          </Link>
        ))}
        <button
          onClick={logout}
          style={{
            marginTop: "auto",
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--muted)",
            borderRadius: 8,
            padding: "0.5rem",
          }}
        >
          Sign out
        </button>
      </aside>
      <main style={{ flex: 1, padding: "2rem", overflow: "auto" }}>{children}</main>
    </div>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <EventProvider>
      <ShellInner>{children}</ShellInner>
    </EventProvider>
  );
}
