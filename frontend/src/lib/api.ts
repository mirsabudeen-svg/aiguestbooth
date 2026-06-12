const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("booth_token");
}

export function setToken(token: string) {
  localStorage.setItem("booth_token", token);
}

export function setUserRole(role: string) {
  localStorage.setItem("booth_role", role);
}

export function getUserRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("booth_role");
}

export function clearToken() {
  localStorage.removeItem("booth_token");
  localStorage.removeItem("booth_role");
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { ...extra };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = authHeaders(options.headers as Record<string, string>);
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail);
    throw new Error(message || "Request failed");
  }
  return res.json();
}

export async function login(email: string, password: string) {
  const res = await apiFetch<{ access_token: string; role: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setUserRole(res.role);
  return res;
}

export async function getDashboardOverview(eventId?: string) {
  const q = eventId ? `?event_id=${eventId}` : "";
  return apiFetch<DashboardOverview>(`/dashboard/overview${q}`);
}

export async function getMessages(params?: {
  eventId?: string;
  q?: string;
  page?: number;
  pageSize?: number;
}) {
  const search = new URLSearchParams();
  if (params?.eventId) search.set("event_id", params.eventId);
  if (params?.q) search.set("q", params.q);
  if (params?.page) search.set("page", String(params.page));
  if (params?.pageSize) search.set("page_size", String(params.pageSize));
  const qs = search.toString();
  return apiFetch<MessageListResponse>(`/messages${qs ? `?${qs}` : ""}`);
}

export async function getMessage(messageId: string) {
  return apiFetch<MessageDetail>(`/messages/${messageId}`);
}

export async function updateTranscript(
  transcriptId: string,
  data: { cleaned_text?: string; summary_text?: string }
) {
  return apiFetch<TranscriptDetail>(`/transcripts/${transcriptId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function reprocessTranscript(transcriptId: string) {
  return apiFetch<{ ok: boolean; message: string; job_id: string }>(
    `/transcripts/${transcriptId}/reprocess`,
    { method: "POST" }
  );
}

export async function getEvents() {
  return apiFetch<EventItem[]>("/events");
}

export async function getEvent(eventId: string) {
  return apiFetch<EventDetail>(`/events/${eventId}`);
}

export async function createEvent(data: EventCreateInput) {
  return apiFetch<EventDetail>("/events", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateEvent(eventId: string, data: EventUpdateInput) {
  return apiFetch<EventDetail>(`/events/${eventId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function uploadEventAsset(eventId: string, assetType: "prompt" | "thank_you", file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/events/${eventId}/assets/${assetType}`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Upload failed");
  }
  return res.json() as Promise<{ ok: boolean; url: string }>;
}

export async function getBooths(eventId?: string) {
  const q = eventId ? `?event_id=${eventId}` : "";
  return apiFetch<BoothItem[]>(`/booths${q}`);
}

export async function createBooth(data: { event_id: string; name: string; location_label?: string }) {
  return apiFetch<BoothItem>("/booths", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function assignDeviceToBooth(boothId: string, deviceId: string | null) {
  return apiFetch<BoothItem>(`/booths/${boothId}/assign-device`, {
    method: "PATCH",
    body: JSON.stringify({ device_id: deviceId }),
  });
}

export async function getDevices() {
  return apiFetch<DeviceItem[]>("/devices");
}

export async function createExport(
  eventId: string,
  format: "zip" | "csv" | "reel" | "slideshow" = "zip",
  messageIds?: string[]
) {
  return apiFetch<ExportJob>("/exports", {
    method: "POST",
    body: JSON.stringify({
      event_id: eventId,
      format,
      message_ids: messageIds,
    }),
  });
}

export async function downloadExport(exportId: string, format: string = "zip") {
  const res = await fetch(`${API_URL}/exports/${exportId}/download`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Download failed");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    format === "reel"
      ? `booth-reel-${exportId}.mp3`
      : format === "slideshow"
        ? `booth-slideshow-${exportId}.zip`
        : `booth-export-${exportId}.zip`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function getAnalytics(eventId: string) {
  return apiFetch<AnalyticsOverview>(`/analytics/overview?event_id=${eventId}`);
}

export async function updateMessage(messageId: string, data: { starred?: boolean }) {
  return apiFetch<MessageDetail>(`/messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getDeliverySettings(eventId: string) {
  return apiFetch<DeliverySettings>("/events/" + eventId + "/delivery");
}

export async function enableDelivery(eventId: string) {
  return apiFetch<DeliverySettings>(`/events/${eventId}/delivery/enable`, { method: "POST" });
}

export async function disableDelivery(eventId: string) {
  return apiFetch<DeliverySettings>(`/events/${eventId}/delivery/disable`, { method: "POST" });
}

export async function rotateDeliveryToken(eventId: string) {
  return apiFetch<DeliverySettings>(`/events/${eventId}/delivery/rotate`, { method: "POST" });
}

export async function moderateTranscript(transcriptId: string, action: "approve" | "block" | "review") {
  return apiFetch<TranscriptDetail>(`/transcripts/${transcriptId}/moderate`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export async function generateTTS(eventId: string, text: string, assetType: "prompt" | "thank_you" = "prompt") {
  return apiFetch<{ ok: boolean; url: string }>(`/events/${eventId}/tts`, {
    method: "POST",
    body: JSON.stringify({ text, asset_type: assetType }),
  });
}

export function getAudioStreamPath(eventId: string, sessionId: string) {
  return `${API_URL}/messages/audio/${eventId}/${sessionId}.wav`;
}

export async function getSnapshotBlobUrl(eventId: string, sessionId: string): Promise<string> {
  const res = await fetch(`${API_URL}/messages/snapshot/${eventId}/${sessionId}.jpg`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Could not load snapshot");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function getAudioBlobUrl(eventId: string, sessionId: string): Promise<string> {
  const res = await fetch(getAudioStreamPath(eventId, sessionId), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Could not load audio");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export function revokeBlobUrl(url: string) {
  URL.revokeObjectURL(url);
}

export interface PaginatedMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface MessageListResponse {
  items: MessageListItem[];
  meta: PaginatedMeta;
}

export interface DashboardOverview {
  event_id: string | null;
  event_name: string | null;
  total_messages: number;
  messages_today: number;
  pending_uploads: number;
  failed_uploads: number;
  processing_queue: number;
  booths: BoothStatus[];
  device_alerts: DeviceAlert[];
}

export interface DeviceAlert {
  device_id: string;
  serial_number: string;
  booth_name: string | null;
  error_code: string | null;
  error_message: string | null;
  error_at: string | null;
  status: string;
}

export interface BoothStatus {
  booth_id: string;
  booth_name: string;
  status: string;
  device_state: string | null;
  last_seen_at: string | null;
  messages_today: number;
  pending_uploads: number;
}

export interface MessageListItem {
  id: string;
  session_id: string;
  event_id: string;
  booth_name: string | null;
  duration_seconds: number | null;
  created_at: string;
  upload_status: string;
  processing_status: string;
  summary_text: string | null;
  sentiment_label: string | null;
  moderation_label: string | null;
  transcript_preview: string | null;
  tags: string[];
  starred: boolean;
  has_snapshot: boolean;
}

export interface TranscriptDetail {
  id: string;
  audio_message_id: string;
  transcript_text: string | null;
  cleaned_text: string | null;
  summary_text: string | null;
  sentiment_label: string | null;
  moderation_label: string;
  language_code: string | null;
  confidence_score: number | null;
}

export interface ProcessingJobSummary {
  id: string;
  status: string;
  attempts: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface MessageDetail {
  id: string;
  session_id: string;
  event_id: string;
  booth_id: string;
  duration_seconds: number | null;
  file_size_bytes: number | null;
  checksum: string;
  audio_url: string;
  created_at: string;
  processing_status: string;
  processing_job: ProcessingJobSummary | null;
  transcript: TranscriptDetail | null;
  tags: string[];
  starred: boolean;
  snapshot_url: string | null;
}

export interface AnalyticsOverview {
  event_id: string;
  event_name: string;
  total_messages: number;
  starred_count: number;
  with_snapshot_count: number;
  by_hour: { hour: number; count: number }[];
  by_booth: { booth_id: string; booth_name: string; count: number }[];
  top_tags: { tag: string; count: number }[];
}

export interface DeliverySettings {
  delivery_enabled: boolean;
  delivery_token: string | null;
  share_url: string | null;
  qr_url: string | null;
}

export interface EventItem {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface EventBranding {
  primary_color?: string;
  secondary_color?: string;
  logo_url?: string;
}

export interface EventDetail {
  id: string;
  name: string;
  slug: string;
  event_type: string;
  venue: string | null;
  max_record_seconds: number;
  is_active: boolean;
  moderation_enabled: boolean;
  retention_days: number;
  prompt_audio_url: string | null;
  thank_you_audio_url: string | null;
  branding_json: EventBranding | null;
  created_at: string;
}

export interface EventCreateInput {
  name: string;
  slug: string;
  event_type?: string;
  venue?: string;
  max_record_seconds?: number;
  retention_days?: number;
  moderation_enabled?: boolean;
  branding_json?: EventBranding;
}

export interface EventUpdateInput {
  name?: string;
  venue?: string;
  max_record_seconds?: number;
  retention_days?: number;
  is_active?: boolean;
  moderation_enabled?: boolean;
  branding_json?: EventBranding;
}

export interface BoothItem {
  id: string;
  event_id: string;
  name: string;
  location_label: string | null;
  status: string;
  assigned_device_id: string | null;
  created_at: string;
}

export interface DeviceItem {
  id: string;
  serial_number: string;
  display_name: string;
  status: string;
  current_state: string | null;
  firmware_version: string | null;
  last_seen_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  last_error_at: string | null;
  assigned_booth_id: string | null;
  assigned_booth_name: string | null;
  assigned_event_id: string | null;
}

export interface ExportJob {
  id: string;
  event_id: string;
  status: string;
  format: string;
  output_path: string | null;
  download_url: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}
