"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { useEventContext } from "@/contexts/EventContext";
import {
  EventBranding,
  EventCreateInput,
  EventDetail,
  EventUpdateInput,
  DeliverySettings,
  createEvent,
  disableDelivery,
  enableDelivery,
  generateTTS,
  getDeliverySettings,
  getEvent,
  getToken,
  getUserRole,
  rotateDeliveryToken,
  updateEvent,
  uploadEventAsset,
} from "@/lib/api";

const inputStyle: React.CSSProperties = {
  background: "var(--bg)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.65rem 0.75rem",
  color: "var(--text)",
  width: "100%",
};

function EventsContent() {
  const router = useRouter();
  const { events, selectedEventId, setSelectedEventId, loading, refreshEvents } = useEventContext();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [detail, setDetail] = useState<EventDetail | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [delivery, setDelivery] = useState<DeliverySettings | null>(null);
  const [ttsText, setTtsText] = useState("Leave a short voice message for the happy couple!");
  const isAdmin = getUserRole() === "admin";

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    refreshEvents().catch(console.error);
  }, [router, refreshEvents]);

  useEffect(() => {
    if (!editingId || !isAdmin) {
      setDetail(null);
      return;
    }
    getEvent(editingId)
      .then(setDetail)
      .catch((e) => setError(e.message));
    getDeliverySettings(editingId)
      .then(setDelivery)
      .catch(() => setDelivery(null));
  }, [editingId, isAdmin]);

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError("");
    const form = new FormData(e.currentTarget);
    const branding: EventBranding = {
      primary_color: String(form.get("primary_color") || "") || undefined,
      secondary_color: String(form.get("secondary_color") || "") || undefined,
      logo_url: String(form.get("logo_url") || "") || undefined,
    };
    const payload: EventCreateInput = {
      name: String(form.get("name")),
      slug: String(form.get("slug")),
      venue: String(form.get("venue") || "") || undefined,
      max_record_seconds: Number(form.get("max_record_seconds") || 120),
      retention_days: Number(form.get("retention_days") || 90),
      branding_json: branding,
    };
    try {
      const created = await createEvent(payload);
      await refreshEvents();
      setSelectedEventId(created.id);
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editingId) return;
    setSaving(true);
    setError("");
    const form = new FormData(e.currentTarget);
    const branding: EventBranding = {
      primary_color: String(form.get("primary_color") || "") || undefined,
      secondary_color: String(form.get("secondary_color") || "") || undefined,
      logo_url: String(form.get("logo_url") || "") || undefined,
    };
    const payload: EventUpdateInput = {
      name: String(form.get("name")),
      venue: String(form.get("venue") || "") || undefined,
      max_record_seconds: Number(form.get("max_record_seconds") || 120),
      retention_days: Number(form.get("retention_days") || 90),
      is_active: form.get("is_active") === "on",
      moderation_enabled: form.get("moderation_enabled") === "on",
      branding_json: branding,
    };
    try {
      await updateEvent(editingId, payload);
      const promptFile = form.get("prompt_file") as File | null;
      const thankFile = form.get("thank_you_file") as File | null;
      if (promptFile?.size) await uploadEventAsset(editingId, "prompt", promptFile);
      if (thankFile?.size) await uploadEventAsset(editingId, "thank_you", thankFile);
      await refreshEvents();
      setDetail(await getEvent(editingId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <header style={{ display: "flex", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Events</h1>
          <p style={{ color: "var(--muted)" }}>
            Manage events, branding, prompt audio, and retention policy.
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => {
              setShowCreate((v) => !v);
              setEditingId(null);
            }}
            style={{
              background: "var(--accent)",
              color: "#111",
              border: "none",
              borderRadius: 8,
              padding: "0.5rem 1rem",
              fontWeight: 600,
            }}
          >
            {showCreate ? "Cancel" : "New event"}
          </button>
        )}
      </header>

      {error && <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</p>}

      {showCreate && isAdmin && (
        <form onSubmit={handleCreate} className="card" style={{ marginBottom: "1.5rem", maxWidth: 560 }}>
          <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Create event</h2>
          <div style={{ display: "grid", gap: "0.75rem" }}>
            <input name="name" placeholder="Event name" required style={inputStyle} />
            <input name="slug" placeholder="slug-lowercase" required pattern="[a-z0-9-]+" style={inputStyle} />
            <input name="venue" placeholder="Venue" style={inputStyle} />
            <input name="max_record_seconds" type="number" defaultValue={120} min={10} max={300} style={inputStyle} />
            <input name="retention_days" type="number" defaultValue={90} min={1} style={inputStyle} />
            <input name="primary_color" placeholder="Primary color (#hex)" style={inputStyle} />
            <input name="secondary_color" placeholder="Secondary color (#hex)" style={inputStyle} />
            <input name="logo_url" placeholder="Logo URL" style={inputStyle} />
            <button type="submit" disabled={saving} style={{ ...inputStyle, background: "var(--accent)", color: "#111" }}>
              {saving ? "Creating…" : "Create event"}
            </button>
          </div>
        </form>
      )}

      <div style={{ display: "grid", gap: "0.75rem", maxWidth: 560, marginBottom: "2rem" }}>
        {loading && <p style={{ color: "var(--muted)" }}>Loading…</p>}
        {events.map((ev) => (
          <button
            key={ev.id}
            onClick={() => {
              setSelectedEventId(ev.id);
              if (isAdmin) setEditingId(ev.id);
            }}
            className="card"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              textAlign: "left",
              cursor: "pointer",
              border: ev.id === selectedEventId ? "1px solid var(--accent)" : "1px solid var(--border)",
              background: "var(--surface)",
              width: "100%",
            }}
          >
            <div>
              <strong>{ev.name}</strong>
              <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{ev.slug}</p>
            </div>
            <span className={`badge ${ev.is_active ? "badge-online" : "badge-offline"}`}>
              {ev.is_active ? "active" : "inactive"}
            </span>
          </button>
        ))}
      </div>

      {isAdmin && detail && editingId && (
        <form onSubmit={handleUpdate} className="card" style={{ maxWidth: 560 }}>
          <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Edit {detail.name}</h2>
          <div style={{ display: "grid", gap: "0.75rem" }}>
            <input name="name" defaultValue={detail.name} required style={inputStyle} />
            <input name="venue" defaultValue={detail.venue ?? ""} style={inputStyle} />
            <input
              name="max_record_seconds"
              type="number"
              defaultValue={detail.max_record_seconds}
              min={10}
              max={300}
              style={inputStyle}
            />
            <input name="retention_days" type="number" defaultValue={detail.retention_days} min={1} style={inputStyle} />
            <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input name="is_active" type="checkbox" defaultChecked={detail.is_active} />
              Active
            </label>
            <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input name="moderation_enabled" type="checkbox" defaultChecked={detail.moderation_enabled} />
              AI moderation enabled
            </label>
            <input
              name="primary_color"
              defaultValue={detail.branding_json?.primary_color ?? ""}
              placeholder="Primary color"
              style={inputStyle}
            />
            <input
              name="secondary_color"
              defaultValue={detail.branding_json?.secondary_color ?? ""}
              placeholder="Secondary color"
              style={inputStyle}
            />
            <input
              name="logo_url"
              defaultValue={detail.branding_json?.logo_url ?? ""}
              placeholder="Logo URL"
              style={inputStyle}
            />
            <label style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              Prompt WAV
              <input name="prompt_file" type="file" accept="audio/wav,audio/*" style={{ display: "block", marginTop: 4 }} />
            </label>
            <label style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              Thank-you WAV
              <input name="thank_you_file" type="file" accept="audio/wav,audio/*" style={{ display: "block", marginTop: 4 }} />
            </label>
            {detail.prompt_audio_url && (
              <p style={{ fontSize: "0.8rem", color: "var(--muted)" }}>Prompt: {detail.prompt_audio_url}</p>
            )}
            <button type="submit" disabled={saving} style={{ ...inputStyle, background: "var(--accent)", color: "#111" }}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      )}

      {isAdmin && editingId && delivery && (
        <div className="card" style={{ maxWidth: 560, marginTop: "1.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Couple delivery page</h2>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "1rem" }}>
            Share a private link or QR code so couples can browse voice messages and photos.
          </p>
          {delivery.delivery_enabled && delivery.share_url ? (
            <>
              <input readOnly value={delivery.share_url} style={inputStyle} />
              {delivery.qr_url && (
                <img src={delivery.qr_url} alt="QR code" style={{ marginTop: "0.75rem", borderRadius: 8 }} />
              )}
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => rotateDeliveryToken(editingId).then(setDelivery)}
                  style={{ ...inputStyle, background: "var(--surface)" }}
                >
                  Rotate link
                </button>
                <button
                  type="button"
                  onClick={() => disableDelivery(editingId).then(setDelivery)}
                  style={{ ...inputStyle, background: "var(--surface)" }}
                >
                  Disable
                </button>
              </div>
            </>
          ) : (
            <button
              type="button"
              onClick={() => enableDelivery(editingId).then(setDelivery)}
              style={{ ...inputStyle, background: "var(--accent)", color: "#111" }}
            >
              Enable delivery page
            </button>
          )}

          <h3 style={{ fontSize: "1rem", marginTop: "1.5rem", marginBottom: "0.5rem" }}>AI voice prompt (TTS)</h3>
          <textarea
            value={ttsText}
            onChange={(e) => setTtsText(e.target.value)}
            rows={3}
            style={{ ...inputStyle, resize: "vertical" }}
          />
          <button
            type="button"
            disabled={saving}
            onClick={() => {
              setSaving(true);
              generateTTS(editingId, ttsText, "prompt")
                .then(() => getEvent(editingId).then(setDetail))
                .catch((e) => setError(e.message))
                .finally(() => setSaving(false));
            }}
            style={{ ...inputStyle, marginTop: "0.5rem", background: "var(--accent)", color: "#111" }}
          >
            Generate prompt audio
          </button>
        </div>
      )}
    </>
  );
}

export default function EventsPage() {
  return (
    <DashboardShell>
      <EventsContent />
    </DashboardShell>
  );
}
