"use client";

import { useState } from "react";
import { createExport, downloadExport } from "@/lib/api";
import { useEventContext } from "@/contexts/EventContext";

export function ExportButton() {
  const { selectedEventId } = useEventContext();
  const [loading, setLoading] = useState<"zip" | "reel" | "slideshow" | null>(null);
  const [error, setError] = useState("");

  async function handleExport(format: "zip" | "reel" | "slideshow") {
    if (!selectedEventId) return;
    setLoading(format);
    setError("");
    try {
      const job = await createExport(selectedEventId, format);
      if (job.status !== "completed") {
        throw new Error(job.error_message || "Export did not complete");
      }
      await downloadExport(job.id, format);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", alignItems: "flex-start" }}>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button
          onClick={() => handleExport("zip")}
          disabled={!selectedEventId || loading !== null}
          style={btnStyle}
        >
          {loading === "zip" ? "Building ZIP…" : "ZIP export"}
        </button>
        <button
          onClick={() => handleExport("reel")}
          disabled={!selectedEventId || loading !== null}
          style={{ ...btnStyle, background: "var(--surface)", color: "var(--text)", border: "1px solid var(--border)" }}
        >
          {loading === "reel" ? "Building reel…" : "Memory reel (MP3)"}
        </button>
        <button
          onClick={() => handleExport("slideshow")}
          disabled={!selectedEventId || loading !== null}
          style={{ ...btnStyle, background: "var(--surface)", color: "var(--text)", border: "1px solid var(--border)" }}
        >
          {loading === "slideshow" ? "Building…" : "Slideshow (ZIP)"}
        </button>
      </div>
      {error && <span style={{ color: "var(--danger)", fontSize: "0.8rem" }}>{error}</span>}
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: "var(--accent)",
  color: "#111",
  border: "none",
  borderRadius: 8,
  padding: "0.55rem 1rem",
  fontWeight: 600,
};
