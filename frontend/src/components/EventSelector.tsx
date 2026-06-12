"use client";

import { useEventContext } from "@/contexts/EventContext";

export function EventSelector() {
  const { events, selectedEventId, setSelectedEventId, loading } = useEventContext();

  if (loading) {
    return <p style={{ fontSize: "0.8rem", color: "var(--muted)" }}>Loading events…</p>;
  }

  if (events.length === 0) {
    return <p style={{ fontSize: "0.8rem", color: "var(--muted)" }}>No events</p>;
  }

  return (
    <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem", marginBottom: "1rem" }}>
      <span style={{ fontSize: "0.7rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        Event
      </span>
      <select
        value={selectedEventId ?? ""}
        onChange={(e) => setSelectedEventId(e.target.value || null)}
        style={{
          background: "var(--bg)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          color: "var(--text)",
          padding: "0.5rem 0.6rem",
          fontSize: "0.85rem",
          width: "100%",
        }}
      >
        {events.map((ev) => (
          <option key={ev.id} value={ev.id}>
            {ev.name}
          </option>
        ))}
      </select>
    </label>
  );
}
