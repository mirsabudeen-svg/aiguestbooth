"use client";

const STYLES: Record<string, { bg: string; color: string; label: string }> = {
  queued: { bg: "#3f3f46", color: "#a1a1aa", label: "Queued" },
  running: { bg: "#1e3a5f", color: "#60a5fa", label: "Processing" },
  completed: { bg: "#14532d", color: "#4ade80", label: "Transcribed" },
  failed: { bg: "#7f1d1d", color: "#f87171", label: "Failed" },
  none: { bg: "#3f3f46", color: "#71717a", label: "No AI job" },
};

export function ProcessingBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? STYLES.none;
  return (
    <span
      className="badge"
      style={{ background: style.bg, color: style.color, textTransform: "capitalize" }}
    >
      {style.label}
    </span>
  );
}
