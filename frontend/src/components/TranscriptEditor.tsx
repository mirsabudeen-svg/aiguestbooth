"use client";

import { useState } from "react";
import { reprocessTranscript, updateTranscript } from "@/lib/api";

interface Props {
  transcriptId: string;
  cleanedText: string | null;
  summaryText: string | null;
  sentimentLabel: string | null;
  moderationLabel: string;
  onSaved: () => void;
}

export function TranscriptEditor({
  transcriptId,
  cleanedText,
  summaryText,
  sentimentLabel,
  moderationLabel,
  onSaved,
}: Props) {
  const [cleaned, setCleaned] = useState(cleanedText ?? "");
  const [summary, setSummary] = useState(summaryText ?? "");
  const [saving, setSaving] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await updateTranscript(transcriptId, {
        cleaned_text: cleaned,
        summary_text: summary,
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleReprocess() {
    setReprocessing(true);
    setError("");
    try {
      await reprocessTranscript(transcriptId);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reprocess failed");
    } finally {
      setReprocessing(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {sentimentLabel && <span className="badge badge-offline">{sentimentLabel}</span>}
        <span className="badge badge-offline">mod: {moderationLabel}</span>
      </div>

      <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>Transcript</span>
        <textarea
          value={cleaned}
          onChange={(e) => setCleaned(e.target.value)}
          rows={5}
          style={textareaStyle}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>Summary</span>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          style={textareaStyle}
        />
      </label>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button onClick={handleSave} disabled={saving} style={primaryBtn}>
          {saving ? "Saving…" : "Save edits"}
        </button>
        <button onClick={handleReprocess} disabled={reprocessing} style={secondaryBtn}>
          {reprocessing ? "Reprocessing…" : "Re-run AI"}
        </button>
      </div>

      {error && <p style={{ color: "var(--danger)", fontSize: "0.85rem" }}>{error}</p>}
    </div>
  );
}

const textareaStyle: React.CSSProperties = {
  background: "var(--bg)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.65rem 0.75rem",
  color: "var(--text)",
  resize: "vertical",
  fontFamily: "inherit",
};

const primaryBtn: React.CSSProperties = {
  background: "var(--accent)",
  color: "#111",
  border: "none",
  borderRadius: 8,
  padding: "0.5rem 1rem",
  fontWeight: 600,
};

const secondaryBtn: React.CSSProperties = {
  background: "var(--surface)",
  color: "var(--text)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.5rem 1rem",
};
