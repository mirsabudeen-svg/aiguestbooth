"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { ExportButton } from "@/components/ExportButton";
import { useEventContext } from "@/contexts/EventContext";
import {
  BoothStatus,
  DashboardOverview,
  DeviceAlert,
  getDashboardOverview,
  getToken,
} from "@/lib/api";

const REFRESH_MS = 15000;

function DashboardContent() {
  const router = useRouter();
  const { selectedEventId, selectedEvent } = useEventContext();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    if (!getToken()) return Promise.resolve();
    return getDashboardOverview(selectedEventId ?? undefined)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [selectedEventId]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [router, load]);

  return (
    <>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "1rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.75rem" }}>Live Overview</h1>
          <p style={{ color: "var(--muted)" }}>
            {selectedEvent?.name ?? data?.event_name ?? "Select an event"}
          </p>
        </div>
        <ExportButton />
      </header>

      {error && <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</p>}

      {data && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: "1rem",
              marginBottom: "2rem",
            }}
          >
            <StatCard label="Messages today" value={data.messages_today} />
            <StatCard label="Total messages" value={data.total_messages} />
            <StatCard
              label="Pending uploads"
              value={data.pending_uploads}
              highlight={data.pending_uploads > 0}
            />
            <StatCard
              label="Failed uploads"
              value={data.failed_uploads}
              highlight={data.failed_uploads > 0}
              warn
            />
            <StatCard label="AI queue" value={data.processing_queue} />
          </div>

          {data.device_alerts.length > 0 && (
            <>
              <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem", color: "var(--danger)" }}>
                Device alerts
              </h2>
              <div style={{ display: "grid", gap: "0.75rem", marginBottom: "2rem" }}>
                {data.device_alerts.map((alert) => (
                  <AlertCard key={alert.device_id} alert={alert} />
                ))}
              </div>
            </>
          )}

          <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Booths</h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "1rem",
            }}
          >
            {data.booths.map((booth) => (
              <BoothCard key={booth.booth_id} booth={booth} />
            ))}
            {data.booths.length === 0 && (
              <p style={{ color: "var(--muted)" }}>No booths configured for this event.</p>
            )}
          </div>
        </>
      )}
    </>
  );
}

export default function DashboardPage() {
  return (
    <DashboardShell>
      <DashboardContent />
    </DashboardShell>
  );
}

function StatCard({
  label,
  value,
  highlight,
  warn,
}: {
  label: string;
  value: number;
  highlight?: boolean;
  warn?: boolean;
}) {
  const color = highlight ? (warn ? "var(--danger)" : "var(--warning)") : "var(--text)";
  return (
    <div className="card">
      <p style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "0.35rem" }}>{label}</p>
      <p style={{ fontSize: "2rem", fontWeight: 700, color }}>{value}</p>
    </div>
  );
}

function AlertCard({ alert }: { alert: DeviceAlert }) {
  const when = alert.error_at ? new Date(alert.error_at).toLocaleString() : "—";
  return (
    <div className="card" style={{ borderColor: "var(--danger)" }}>
      <strong>{alert.serial_number}</strong>
      {alert.booth_name && (
        <span style={{ color: "var(--muted)", marginLeft: "0.5rem" }}>({alert.booth_name})</span>
      )}
      <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
        {alert.error_code}: {alert.error_message}
      </p>
      <p style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "0.25rem" }}>{when}</p>
    </div>
  );
}

function BoothCard({ booth }: { booth: BoothStatus }) {
  const online = booth.status === "online";
  const lastSeen = booth.last_seen_at ? new Date(booth.last_seen_at).toLocaleTimeString() : "—";

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.75rem",
        }}
      >
        <strong>{booth.booth_name}</strong>
        <span className={`badge ${online ? "badge-online" : "badge-offline"}`}>{booth.status}</span>
      </div>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
        Device state: {booth.device_state || "—"}
      </p>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "0.25rem" }}>
        Last seen: {lastSeen}
      </p>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "0.25rem" }}>
        Messages today: {booth.messages_today}
      </p>
      {booth.pending_uploads > 0 && (
        <p style={{ fontSize: "0.85rem", color: "var(--warning)", marginTop: "0.5rem" }}>
          {booth.pending_uploads} waiting to sync
        </p>
      )}
    </div>
  );
}
