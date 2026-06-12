"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AuthenticatedAudioPlayer } from "@/components/AuthenticatedAudioPlayer";
import { DashboardShell } from "@/components/DashboardShell";
import { ProcessingBadge } from "@/components/ProcessingBadge";
import { TranscriptEditor } from "@/components/TranscriptEditor";
import {
  getMessage,
  getSnapshotBlobUrl,
  getToken,
  MessageDetail,
  moderateTranscript,
  revokeBlobUrl,
  updateMessage,
} from "@/lib/api";

function MessageDetailContent() {
  const params = useParams();
  const router = useRouter();
  const messageId = params.id as string;
  const [message, setMessage] = useState<MessageDetail | null>(null);
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    return getMessage(messageId)
      .then(setMessage)
      .catch((e) => setError(e.message));
  }, [messageId]);

  useEffect(() => {
    if (!message?.snapshot_url || !message.event_id) return;
    let url: string | null = null;
    getSnapshotBlobUrl(message.event_id, message.session_id)
      .then((blobUrl) => {
        url = blobUrl;
        setSnapshotUrl(blobUrl);
      })
      .catch(console.error);
    return () => {
      if (url) revokeBlobUrl(url);
    };
  }, [message?.snapshot_url, message?.event_id, message?.session_id]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
    const timer = setInterval(() => {
      if (message?.processing_status === "queued" || message?.processing_status === "running") {
        load();
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [router, load, message?.processing_status]);

  if (error) {
    return <p style={{ color: "var(--danger)" }}>{error}</p>;
  }

  if (!message) {
    return <p style={{ color: "var(--muted)" }}>Loading message…</p>;
  }

  return (
    <>
      <Link href="/messages" style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
        ← Back to messages
      </Link>

      <header style={{ marginTop: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "1.5rem" }}>Guest Message</h1>
          <ProcessingBadge status={message.processing_status} />
        </div>
        <p style={{ color: "var(--muted)", marginTop: "0.35rem" }}>
          {new Date(message.created_at).toLocaleString()}
          {message.duration_seconds ? ` · ${message.duration_seconds.toFixed(1)}s` : ""}
        </p>
      </header>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <button
          onClick={() =>
            updateMessage(message.id, { starred: !message.starred }).then(() => load())
          }
          style={actionBtnStyle}
        >
          {message.starred ? "★ Starred for reel" : "☆ Star for reel"}
        </button>
        {message.transcript && (
          <>
            <button
              onClick={() =>
                moderateTranscript(message.transcript!.id, "approve").then(() => load())
              }
              style={actionBtnStyle}
            >
              Approve for delivery
            </button>
            <button
              onClick={() =>
                moderateTranscript(message.transcript!.id, "block").then(() => load())
              }
              style={{ ...actionBtnStyle, borderColor: "var(--danger)", color: "var(--danger)" }}
            >
              Block
            </button>
          </>
        )}
      </div>

      {snapshotUrl && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Booth snapshot</h2>
          <img src={snapshotUrl} alt="Guest snapshot" style={{ maxWidth: "100%", borderRadius: 8 }} />
        </div>
      )}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Audio</h2>
        <AuthenticatedAudioPlayer eventId={message.event_id} sessionId={message.session_id} autoPlay={false} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Transcript</h2>
        {message.transcript ? (
          <TranscriptEditor
            transcriptId={message.transcript.id}
            cleanedText={message.transcript.cleaned_text}
            summaryText={message.transcript.summary_text}
            sentimentLabel={message.transcript.sentiment_label}
            moderationLabel={message.transcript.moderation_label}
            onSaved={load}
          />
        ) : (
          <p style={{ color: "var(--muted)" }}>No transcript yet.</p>
        )}
        {message.processing_job?.error_message && (
          <p style={{ color: "var(--danger)", fontSize: "0.85rem", marginTop: "0.75rem" }}>
            {message.processing_job.error_message}
          </p>
        )}
      </div>

      {message.tags.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Tags</h2>
          <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
            {message.tags.map((t) => (
              <span key={t} className="badge badge-offline">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export default function MessageDetailPage() {
  return (
    <DashboardShell>
      <MessageDetailContent />
    </DashboardShell>
  );
}

const actionBtnStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  borderRadius: 8,
  padding: "0.45rem 0.85rem",
  fontSize: "0.85rem",
  cursor: "pointer",
};
