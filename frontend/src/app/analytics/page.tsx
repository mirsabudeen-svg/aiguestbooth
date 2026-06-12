"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { useEventContext } from "@/contexts/EventContext";
import { AnalyticsOverview, getAnalytics, getToken } from "@/lib/api";

function AnalyticsContent() {
  const router = useRouter();
  const { selectedEventId, selectedEvent } = useEventContext();
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    if (!getToken() || !selectedEventId) return Promise.resolve();
    return getAnalytics(selectedEventId).then(setData).catch((e) => setError(e.message));
  }, [selectedEventId]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [router, load]);

  const maxHour = Math.max(...(data?.by_hour.map((b) => b.count) ?? [1]), 1);
  const maxBooth = Math.max(...(data?.by_booth.map((b) => b.count) ?? [1]), 1);
  const maxTag = Math.max(...(data?.top_tags.map((t) => t.count) ?? [1]), 1);

  return (
    <>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Analytics</h1>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
        Insights for {selectedEvent?.name ?? "selected event"}
      </p>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!selectedEventId && <p style={{ color: "var(--muted)" }}>Select an event first.</p>}

      {data && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: "1rem",
              marginBottom: "2rem",
            }}
          >
            <Stat label="Total" value={data.total_messages} />
            <Stat label="Starred" value={data.starred_count} />
            <Stat label="With photo" value={data.with_snapshot_count} />
          </div>

          <Section title="Messages by hour">
            <BarChart
              items={data.by_hour.map((b) => ({
                label: `${b.hour}:00`,
                value: b.count,
                pct: (b.count / maxHour) * 100,
              }))}
            />
          </Section>

          <Section title="By booth">
            <BarChart
              items={data.by_booth.map((b) => ({
                label: b.booth_name,
                value: b.count,
                pct: (b.count / maxBooth) * 100,
              }))}
            />
          </Section>

          <Section title="Top tags">
            <BarChart
              items={data.top_tags.map((t) => ({
                label: t.tag,
                value: t.count,
                pct: (t.count / maxTag) * 100,
              }))}
            />
          </Section>
        </>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="card">
      <p style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{label}</p>
      <p style={{ fontSize: "1.75rem", fontWeight: 700 }}>{value}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "2rem" }}>
      <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>{title}</h2>
      {children}
    </div>
  );
}

function BarChart({ items }: { items: { label: string; value: number; pct: number }[] }) {
  if (items.length === 0) return <p style={{ color: "var(--muted)" }}>No data yet.</p>;
  return (
    <div style={{ display: "grid", gap: "0.5rem" }}>
      {items.map((item) => (
        <div key={item.label} style={{ display: "grid", gridTemplateColumns: "100px 1fr 40px", gap: "0.5rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{item.label}</span>
          <div style={{ background: "var(--border)", borderRadius: 4, height: 8 }}>
            <div
              style={{
                width: `${item.pct}%`,
                background: "var(--accent)",
                borderRadius: 4,
                height: 8,
                minWidth: item.value > 0 ? 4 : 0,
              }}
            />
          </div>
          <span style={{ fontSize: "0.85rem", textAlign: "right" }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <DashboardShell>
      <AnalyticsContent />
    </DashboardShell>
  );
}
