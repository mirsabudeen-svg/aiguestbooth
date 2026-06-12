"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { useEventContext } from "@/contexts/EventContext";
import {
  BoothItem,
  DeviceItem,
  assignDeviceToBooth,
  createBooth,
  getBooths,
  getDevices,
  getToken,
  getUserRole,
} from "@/lib/api";

const inputStyle: React.CSSProperties = {
  background: "var(--bg)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.65rem 0.75rem",
  color: "var(--text)",
  width: "100%",
};

function BoothsContent() {
  const router = useRouter();
  const { selectedEventId, selectedEvent } = useEventContext();
  const [booths, setBooths] = useState<BoothItem[]>([]);
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const isAdmin = getUserRole() === "admin";

  const load = useCallback(async () => {
    if (!getToken()) return;
    const [b, d] = await Promise.all([
      getBooths(selectedEventId ?? undefined),
      getDevices(),
    ]);
    setBooths(b);
    setDevices(d);
  }, [selectedEventId]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load().catch((e) => setError(e.message));
  }, [router, load]);

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selectedEventId || !isAdmin) return;
    setSaving(true);
    setError("");
    const form = new FormData(e.currentTarget);
    try {
      await createBooth({
        event_id: selectedEventId,
        name: String(form.get("name")),
        location_label: String(form.get("location_label") || "") || undefined,
      });
      e.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleAssign(boothId: string, deviceId: string) {
    if (!isAdmin) return;
    setError("");
    try {
      await assignDeviceToBooth(boothId, deviceId || null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assign failed");
    }
  }

  return (
    <>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Booths</h1>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
        Assign devices to booths for {selectedEvent?.name ?? "the selected event"}.
      </p>

      {error && <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</p>}

      {!selectedEventId && (
        <p style={{ color: "var(--muted)" }}>Select an event in the sidebar first.</p>
      )}

      {isAdmin && selectedEventId && (
        <form onSubmit={handleCreate} className="card" style={{ marginBottom: "1.5rem", maxWidth: 480 }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Add booth</h2>
          <div style={{ display: "grid", gap: "0.5rem" }}>
            <input name="name" placeholder="Booth name" required style={inputStyle} />
            <input name="location_label" placeholder="Location label" style={inputStyle} />
            <button type="submit" disabled={saving} style={{ ...inputStyle, background: "var(--accent)", color: "#111" }}>
              {saving ? "Adding…" : "Add booth"}
            </button>
          </div>
        </form>
      )}

      <div style={{ display: "grid", gap: "1rem", maxWidth: 640 }}>
        {booths.map((booth) => (
          <div key={booth.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <strong>{booth.name}</strong>
              <span className={`badge ${booth.status === "online" ? "badge-online" : "badge-offline"}`}>
                {booth.status}
              </span>
            </div>
            {booth.location_label && (
              <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{booth.location_label}</p>
            )}
            {isAdmin ? (
              <label style={{ display: "block", marginTop: "0.75rem", fontSize: "0.85rem" }}>
                Assigned device
                <select
                  value={booth.assigned_device_id ?? ""}
                  onChange={(e) => handleAssign(booth.id, e.target.value)}
                  style={{ ...inputStyle, marginTop: 4 }}
                >
                  <option value="">— Unassigned —</option>
                  {devices.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.serial_number}
                      {d.assigned_booth_id && d.assigned_booth_id !== booth.id ? " (assigned elsewhere)" : ""}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "0.5rem" }}>
                Device:{" "}
                {devices.find((d) => d.id === booth.assigned_device_id)?.serial_number ?? "Unassigned"}
              </p>
            )}
          </div>
        ))}
        {selectedEventId && booths.length === 0 && (
          <p style={{ color: "var(--muted)" }}>No booths for this event yet.</p>
        )}
      </div>
    </>
  );
}

export default function BoothsPage() {
  return (
    <DashboardShell>
      <BoothsContent />
    </DashboardShell>
  );
}
