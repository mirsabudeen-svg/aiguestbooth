"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { useEventContext } from "@/contexts/EventContext";
import { DeliverySettings, enableDelivery, getDeliverySettings, getToken } from "@/lib/api";

function BoothQrContent() {
  const router = useRouter();
  const { selectedEventId, selectedEvent } = useEventContext();
  const [delivery, setDelivery] = useState<DeliverySettings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    if (!selectedEventId) return;
    getDeliverySettings(selectedEventId)
      .then(setDelivery)
      .catch((e) => setError(e.message));
  }, [router, selectedEventId]);

  async function ensureEnabled() {
    if (!selectedEventId) return;
    const settings = await enableDelivery(selectedEventId);
    setDelivery(settings);
  }

  return (
    <>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Booth QR</h1>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
        Print or display this QR at the booth so guests can find the couple&apos;s memory page on their phones.
      </p>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!selectedEventId && <p style={{ color: "var(--muted)" }}>Select an event first.</p>}

      {selectedEventId && delivery && !delivery.delivery_enabled && (
        <button
          onClick={() => ensureEnabled().catch((e) => setError(e.message))}
          style={{
            background: "var(--accent)",
            color: "#111",
            border: "none",
            borderRadius: 8,
            padding: "0.65rem 1rem",
            fontWeight: 600,
            marginBottom: "1rem",
          }}
        >
          Enable delivery page for {selectedEvent?.name}
        </button>
      )}

      {delivery?.delivery_enabled && delivery.qr_url && (
        <div
          className="card"
          style={{
            maxWidth: 420,
            textAlign: "center",
            padding: "2rem",
          }}
        >
          <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>{selectedEvent?.name}</h2>
          <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
            Scan to hear guest messages
          </p>
          <img
            src={delivery.qr_url}
            alt="Delivery QR code"
            style={{ width: 280, height: 280, borderRadius: 12 }}
          />
          {delivery.share_url && (
            <p style={{ marginTop: "1.25rem", fontSize: "0.8rem", wordBreak: "break-all", color: "var(--muted)" }}>
              {delivery.share_url}
            </p>
          )}
          <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--muted)" }}>
            Tip: open this page on a tablet at the booth, or print for a sign.
          </p>
        </div>
      )}
    </>
  );
}

export default function BoothQrPage() {
  return (
    <DashboardShell>
      <BoothQrContent />
    </DashboardShell>
  );
}
