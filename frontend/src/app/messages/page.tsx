"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { ExportButton } from "@/components/ExportButton";
import { ProcessingBadge } from "@/components/ProcessingBadge";
import { useEventContext } from "@/contexts/EventContext";
import { MessageListItem, getMessages, getToken, updateMessage } from "@/lib/api";

function MessagesContent() {
  const router = useRouter();
  const { selectedEventId } = useEventContext();
  const [messages, setMessages] = useState<MessageListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const pageSize = 20;

  const load = useCallback(() => {
    if (!getToken()) return Promise.resolve();
    return getMessages({
      eventId: selectedEventId ?? undefined,
      q: query || undefined,
      page,
      pageSize,
    })
      .then((res) => {
        setMessages(res.items);
        setTotal(res.meta.total);
      })
      .catch((e) => setError(e.message));
  }, [selectedEventId, query, page]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [router, load]);

  useEffect(() => {
    const hasActive = messages.some(
      (m) => m.processing_status === "queued" || m.processing_status === "running"
    );
    if (!hasActive) return;
    const timer = setInterval(load, 4000);
    return () => clearInterval(timer);
  }, [messages, load]);

  useEffect(() => {
    setPage(1);
  }, [selectedEventId, query]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "1rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.75rem" }}>Guest Messages</h1>
          <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
            {total} message{total === 1 ? "" : "s"}
          </p>
        </div>
        <ExportButton />
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(search.trim());
        }}
        style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", maxWidth: 480 }}
      >
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search transcripts…"
          style={{
            flex: 1,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "0.6rem 0.75rem",
            color: "var(--text)",
          }}
        />
        <button type="submit" style={pagerBtnStyle}>
          Search
        </button>
      </form>

      {error && <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {messages.map((msg) => (
          <Link
            key={msg.id}
            href={`/messages/${msg.id}`}
            className="card"
            style={{
              display: "block",
              textDecoration: "none",
              color: "inherit",
              border: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 600 }}>{msg.booth_name || "Unknown booth"}</p>
                <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                  {new Date(msg.created_at).toLocaleString()}
                  {msg.duration_seconds ? ` · ${msg.duration_seconds.toFixed(1)}s` : ""}
                </p>
                {msg.summary_text && (
                  <p style={{ fontSize: "0.9rem", marginTop: "0.35rem" }}>{msg.summary_text}</p>
                )}
                {msg.transcript_preview && !msg.summary_text && (
                  <p style={{ fontSize: "0.9rem", marginTop: "0.35rem", color: "var(--muted)" }}>
                    {msg.transcript_preview}
                  </p>
                )}
                {msg.tags.length > 0 && (
                  <div style={{ display: "flex", gap: "0.35rem", marginTop: "0.35rem", flexWrap: "wrap" }}>
                    {msg.tags.map((t) => (
                      <span key={t} className="badge badge-offline">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", alignItems: "flex-end" }}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    updateMessage(msg.id, { starred: !msg.starred })
                      .then(() => load())
                      .catch((err) => setError(err.message));
                  }}
                  title={msg.starred ? "Remove from reel" : "Add to memory reel"}
                  style={{
                    background: "transparent",
                    border: "none",
                    fontSize: "1.25rem",
                    cursor: "pointer",
                    color: msg.starred ? "var(--accent)" : "var(--muted)",
                  }}
                >
                  {msg.starred ? "★" : "☆"}
                </button>
                <ProcessingBadge status={msg.processing_status} />
                <span
                  className={`badge ${msg.upload_status === "synced" ? "badge-online" : "badge-offline"}`}
                >
                  {msg.upload_status}
                </span>
              </div>
            </div>
          </Link>
        ))}
        {messages.length === 0 && !error && (
          <p style={{ color: "var(--muted)" }}>No messages yet for this event.</p>
        )}
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginTop: "1.5rem" }}>
          <button disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} style={pagerBtnStyle}>
            Previous
          </button>
          <span style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
            Page {page} of {totalPages}
          </span>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} style={pagerBtnStyle}>
            Next
          </button>
        </div>
      )}
    </>
  );
}

export default function MessagesPage() {
  return (
    <DashboardShell>
      <MessagesContent />
    </DashboardShell>
  );
}

const pagerBtnStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  borderRadius: 8,
  padding: "0.45rem 0.9rem",
};
