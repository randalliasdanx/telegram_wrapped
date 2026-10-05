import type { SSEProgress, WrappedData } from "./types";

const API_BASE = "/api";

export async function sendCode(phone: string) {
  const res = await fetch(`${API_BASE}/auth/send-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Send code failed: ${res.status}`);
  }
  return res.json() as Promise<{ session_id: string; phone_code_hash: string }>;
}

export async function verifyCode(
  sessionId: string,
  phone: string,
  code: string,
  phoneCodeHash: string,
) {
  const res = await fetch(`${API_BASE}/auth/verify-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      phone,
      code,
      phone_code_hash: phoneCodeHash,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Verify failed: ${res.status}`);
  }
  return res.json() as Promise<{ success: boolean }>;
}

export async function startPipeline(sessionId: string) {
  // new Date().getTimezoneOffset() returns minutes WEST of UTC (negative for UTC+)
  // We negate it so UTC+8 (SGT) sends +480, which the backend adds to UTC hours.
  const utcOffsetMinutes = -new Date().getTimezoneOffset();
  const res = await fetch(`${API_BASE}/wrapped/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, utc_offset_minutes: utcOffsetMinutes }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Start failed: ${res.status}`);
  }
  return res.json() as Promise<{ status: string }>;
}

/** Thrown when the backend no longer knows the session (expired / server restart). */
export class SessionExpiredError extends Error {
  constructor() {
    super("Your session has expired. Please start again.");
    this.name = "SessionExpiredError";
  }
}

export function progressUrl(sessionId: string) {
  return `${API_BASE}/wrapped/progress/${encodeURIComponent(sessionId)}`;
}

export async function fetchResult(sessionId: string): Promise<WrappedData> {
  const res = await fetch(`${API_BASE}/wrapped/result/${encodeURIComponent(sessionId)}`);
  if (res.status === 404) throw new SessionExpiredError();
  // The backend answers 202 while the pipeline is still running.
  if (res.status !== 200) throw new Error(`Result not ready: ${res.status}`);
  return res.json();
}

/** Latest pipeline progress, polled once. Throws SessionExpiredError on 404. */
export async function fetchStatus(sessionId: string): Promise<SSEProgress> {
  const res = await fetch(`${API_BASE}/wrapped/status/${encodeURIComponent(sessionId)}`);
  if (res.status === 404) throw new SessionExpiredError();
  if (!res.ok) throw new Error(`Status failed: ${res.status}`);
  return res.json();
}
