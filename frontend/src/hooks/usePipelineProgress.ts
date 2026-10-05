import { useEffect, useState } from "react";
import type { SSEProgress } from "../api/types";
import { fetchStatus, progressUrl, SessionExpiredError } from "../api/client";

const POLL_INTERVAL_MS = 2000;
/** If the SSE stream goes silent this long (e.g. a buffering proxy), poll once to catch up. */
const SSE_WATCHDOG_MS = 12000;

const isTerminal = (p: SSEProgress) => p.phase === "done" || p.phase === "error";

/**
 * Live pipeline progress for a session.
 *
 * Uses the SSE stream when available and falls back to polling
 * `/wrapped/status/{id}` every 2 s if the stream errors (or isn't supported).
 * `expired` flips to true when the backend no longer knows the session.
 */
export function usePipelineProgress(sessionId: string | null) {
  const [progress, setProgress] = useState<SSEProgress | null>(null);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;
    let finished = false;
    let source: EventSource | null = null;
    let pollTimer: ReturnType<typeof setTimeout> | undefined;
    let watchdog: ReturnType<typeof setTimeout> | undefined;

    const stop = () => {
      finished = true;
      source?.close();
      source = null;
      clearTimeout(pollTimer);
      clearTimeout(watchdog);
    };

    const handle = (p: SSEProgress) => {
      if (cancelled || finished) return;
      setProgress(p);
      if (isTerminal(p)) stop();
    };

    const poll = async () => {
      if (cancelled || finished) return;
      try {
        handle(await fetchStatus(sessionId));
      } catch (e) {
        if (e instanceof SessionExpiredError) {
          if (!cancelled) setExpired(true);
          stop();
          return;
        }
        // Network blip — keep trying.
      }
      if (!cancelled && !finished && !source) {
        pollTimer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    const armWatchdog = () => {
      clearTimeout(watchdog);
      watchdog = setTimeout(() => {
        void poll();
        armWatchdog();
      }, SSE_WATCHDOG_MS);
    };

    if (typeof EventSource === "undefined") {
      void poll();
    } else {
      source = new EventSource(progressUrl(sessionId));
      armWatchdog();
      source.onmessage = (e) => {
        armWatchdog();
        try {
          handle(JSON.parse(e.data) as SSEProgress);
        } catch {
          /* ignore malformed frames */
        }
      };
      source.onerror = () => {
        // Either the stream closed after a terminal event (already handled) or it
        // genuinely failed: drop it and switch to polling.
        source?.close();
        source = null;
        clearTimeout(watchdog);
        if (!finished) void poll();
      };
    }

    return () => {
      cancelled = true;
      stop();
    };
  }, [sessionId]);

  return { progress, expired };
}
