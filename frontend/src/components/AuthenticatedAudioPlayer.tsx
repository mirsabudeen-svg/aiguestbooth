"use client";

import { useEffect, useState } from "react";
import { getAudioBlobUrl, revokeBlobUrl } from "@/lib/api";

interface Props {
  eventId: string;
  sessionId: string;
  autoPlay?: boolean;
}

export function AuthenticatedAudioPlayer({ eventId, sessionId, autoPlay = true }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let objectUrl: string | null = null;
    setError("");
    setSrc(null);

    getAudioBlobUrl(eventId, sessionId)
      .then((url) => {
        objectUrl = url;
        setSrc(url);
      })
      .catch((e) => setError(e.message));

    return () => {
      if (objectUrl) revokeBlobUrl(objectUrl);
    };
  }, [eventId, sessionId]);

  if (error) {
    return <span style={{ color: "var(--danger)", fontSize: "0.8rem" }}>{error}</span>;
  }
  if (!src) {
    return <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Loading audio…</span>;
  }

  return <audio controls autoPlay={autoPlay} src={src} style={{ maxWidth: 300, width: "100%" }} />;
}
