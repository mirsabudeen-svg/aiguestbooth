"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface DeliveryMessage {
  id: string;
  session_id: string;
  duration_seconds: number | null;
  created_at: string;
  summary_text: string | null;
  transcript_preview: string | null;
  tags: string[];
  has_snapshot: boolean;
  audio_url: string;
  snapshot_url: string | null;
}

interface DeliveryPage {
  event_name: string;
  event_type: string;
  venue: string | null;
  branding_json: { primary_color?: string; secondary_color?: string; logo_url?: string } | null;
  message_count: number;
  messages: DeliveryMessage[];
}

export default function SharePage() {
  const params = useParams();
  const token = params.token as string;
  const [data, setData] = useState<DeliveryPage | null>(null);
  const [error, setError] = useState("");
  const [playingId, setPlayingId] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/delivery/${token}`)
      .then((res) => {
        if (!res.ok) throw new Error("This memory page is unavailable.");
        return res.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [token]);

  const primary = data?.branding_json?.primary_color || "#c9a962";
  const secondary = data?.branding_json?.secondary_color || "#1a1a2e";

  return (
    <main
      style={{
        minHeight: "100vh",
        background: `linear-gradient(160deg, ${secondary} 0%, #0f0f18 50%, ${secondary} 100%)`,
        color: "#f5f0e8",
        padding: "2rem 1rem 4rem",
      }}
    >
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        {error && <p style={{ textAlign: "center", color: "#f87171" }}>{error}</p>}

        {data && (
          <>
            <header style={{ textAlign: "center", marginBottom: "2.5rem" }}>
              {data.branding_json?.logo_url && (
                <img
                  src={data.branding_json.logo_url}
                  alt=""
                  style={{ maxHeight: 64, marginBottom: "1rem" }}
                />
              )}
              <p style={{ fontSize: "0.85rem", letterSpacing: "0.15em", color: primary, textTransform: "uppercase" }}>
                {data.event_type}
              </p>
              <h1 style={{ fontSize: "2rem", fontWeight: 300, margin: "0.5rem 0" }}>{data.event_name}</h1>
              {data.venue && <p style={{ color: "rgba(245,240,232,0.6)" }}>{data.venue}</p>}
              <p style={{ marginTop: "1rem", fontSize: "0.9rem", color: "rgba(245,240,232,0.5)" }}>
                {data.message_count} voice messages
              </p>
            </header>

            <div style={{ display: "grid", gap: "1.25rem" }}>
              {data.messages.map((msg) => (
                <article
                  key={msg.id}
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 16,
                    overflow: "hidden",
                  }}
                >
                  {msg.snapshot_url && (
                    <img
                      src={msg.snapshot_url}
                      alt=""
                      style={{ width: "100%", maxHeight: 280, objectFit: "cover" }}
                    />
                  )}
                  <div style={{ padding: "1.25rem" }}>
                    {msg.summary_text && (
                      <p style={{ fontSize: "1.05rem", lineHeight: 1.5, marginBottom: "0.75rem" }}>
                        {msg.summary_text}
                      </p>
                    )}
                    {msg.transcript_preview && !msg.summary_text && (
                      <p style={{ fontStyle: "italic", opacity: 0.85, marginBottom: "0.75rem" }}>
                        "{msg.transcript_preview}"
                      </p>
                    )}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginBottom: "0.75rem" }}>
                      {msg.tags.map((tag) => (
                        <span
                          key={tag}
                          style={{
                            fontSize: "0.75rem",
                            padding: "0.2rem 0.5rem",
                            borderRadius: 999,
                            background: "rgba(201,169,98,0.2)",
                            color: primary,
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                    <button
                      onClick={() => {
                        const audio = new Audio(msg.audio_url);
                        setPlayingId(msg.id);
                        audio.onended = () => setPlayingId(null);
                        audio.play().catch(console.error);
                      }}
                      style={{
                        background: primary,
                        color: "#111",
                        border: "none",
                        borderRadius: 8,
                        padding: "0.5rem 1rem",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      {playingId === msg.id ? "Playing…" : "Listen"}
                    </button>
                    <span style={{ marginLeft: "0.75rem", fontSize: "0.8rem", opacity: 0.5 }}>
                      {new Date(msg.created_at).toLocaleString()}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
