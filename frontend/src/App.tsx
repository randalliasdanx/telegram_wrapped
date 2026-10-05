import { useState, useCallback, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Send } from "lucide-react";
import type { WrappedData } from "./api/types";
import { startPipeline, fetchResult, fetchStatus, SessionExpiredError } from "./api/client";
import { AuthSlide } from "./components/slides/AuthSlide";
import { ProgressScreen } from "./components/ProgressScreen";
import { WrappedViewer } from "./components/WrappedViewer";
import { PrivacyPolicy } from "./components/PrivacyPolicy";
import { GUESS_KEY, SESSION_KEY, storageGet, storageRemove, storageSet } from "./lib/storage";

type AppState = "boot" | "auth" | "progress" | "viewing";

type BootTarget =
  | { kind: "demo" }
  | { kind: "resume"; sessionId: string; deepLink: boolean };

/** Decide what to do on first load: demo deck, resume a session, or fresh login. */
function getBootTarget(): BootTarget | null {
  const params = new URLSearchParams(window.location.search);
  if (params.get("demo") === "1") return { kind: "demo" };
  const deep = params.get("session");
  if (deep) return { kind: "resume", sessionId: deep, deepLink: true };
  const stored = storageGet(SESSION_KEY);
  if (stored) return { kind: "resume", sessionId: stored, deepLink: false };
  return null;
}

type ResumeOutcome =
  | { kind: "viewing"; data: WrappedData }
  | { kind: "progress" }
  | { kind: "expired" }
  | { kind: "error"; message: string };

async function resolveSession(sessionId: string): Promise<ResumeOutcome> {
  try {
    const status = await fetchStatus(sessionId);
    if (status.phase === "done") return { kind: "viewing", data: await fetchResult(sessionId) };
    if (status.phase === "error") return { kind: "error", message: status.message || "Something went wrong." };
    return { kind: "progress" };
  } catch (e) {
    if (e instanceof SessionExpiredError) return { kind: "expired" };
    // Status unavailable (network blip / older backend): try the result directly,
    // otherwise let the progress screen keep polling.
    try {
      return { kind: "viewing", data: await fetchResult(sessionId) };
    } catch (e2) {
      if (e2 instanceof SessionExpiredError) return { kind: "expired" };
      return { kind: "progress" };
    }
  }
}

function isAlreadyRunning(e: unknown) {
  return e instanceof Error && /already running/i.test(e.message);
}

export default function App() {
  const [boot] = useState(getBootTarget);
  const [state, setState] = useState<AppState>(() => (boot ? "boot" : "auth"));
  const [sessionId, setSessionId] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [data, setData] = useState<WrappedData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [privacyOpen, setPrivacyOpen] = useState(false);

  // First load: demo mode, ?session= deep link (bot notification), or resume after refresh.
  useEffect(() => {
    if (!boot) return;
    let cancelled = false;

    if (boot.kind === "demo") {
      import("./data/demoData").then(({ DEMO_DATA }) => {
        if (cancelled) return;
        setData(DEMO_DATA);
        setState("viewing");
      });
      return () => {
        cancelled = true;
      };
    }

    // Clean the URL without reloading
    if (boot.deepLink) window.history.replaceState({}, "", window.location.pathname);

    resolveSession(boot.sessionId).then((outcome) => {
      if (cancelled) return;
      switch (outcome.kind) {
        case "viewing":
          storageSet(SESSION_KEY, boot.sessionId);
          setSessionId(boot.sessionId);
          setData(outcome.data);
          setState("viewing");
          break;
        case "progress":
          storageSet(SESSION_KEY, boot.sessionId);
          setSessionId(boot.sessionId);
          setState("progress");
          break;
        case "expired":
          storageRemove(SESSION_KEY);
          if (boot.deepLink) setError("Your session has expired. Please start again.");
          setState("auth");
          break;
        case "error":
          storageRemove(SESSION_KEY);
          setError(outcome.message);
          setState("auth");
          break;
      }
    });

    return () => {
      cancelled = true;
    };
  }, [boot]);

  // Auto-dismiss the error toast.
  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 6000);
    return () => clearTimeout(t);
  }, [error]);

  const handleAuthenticated = useCallback(async (sid: string, phoneNumber: string) => {
    setSessionId(sid);
    setPhone(phoneNumber);
    setError(null);
    storageRemove(GUESS_KEY);
    try {
      await startPipeline(sid);
    } catch (e) {
      if (!isAlreadyRunning(e)) {
        setError(e instanceof Error ? e.message : "Failed to start pipeline");
        return;
      }
    }
    storageSet(SESSION_KEY, sid);
    setState("progress");
  }, []);

  const handleReady = useCallback((result: WrappedData) => {
    setData(result);
    setState("viewing");
  }, []);

  const handleRestart = useCallback(() => {
    storageRemove(SESSION_KEY);
    setSessionId("");
    setData(null);
    setState("auth");
  }, []);

  return (
    <div className="h-dvh w-screen overflow-hidden bg-black">
      <AnimatePresence mode="wait">
        {state === "boot" && (
          <motion.div
            key="boot"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-full w-full flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #29B6F6 0%, #0288D1 100%)" }}
          >
            <motion.div
              animate={{ y: [0, -8, 0], rotate: [0, 6, -6, 0] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              className="w-16 h-16 rounded-full bg-white/15 flex items-center justify-center"
            >
              <Send className="w-7 h-7 text-white" />
            </motion.div>
          </motion.div>
        )}

        {state === "auth" && (
          <AuthSlide
            key="auth"
            onAuthenticated={handleAuthenticated}
            onPrivacyOpen={() => setPrivacyOpen(true)}
          />
        )}

        {state === "progress" && sessionId && (
          <ProgressScreen
            key={`progress-${sessionId}`}
            sessionId={sessionId}
            phone={phone || undefined}
            onReady={handleReady}
            onRestart={handleRestart}
          />
        )}

        {state === "viewing" && data && (
          <motion.div
            key="viewer"
            className="h-full w-full"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
          >
            <WrappedViewer data={data} />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {privacyOpen && (
          <PrivacyPolicy
            key="privacy"
            onClose={() => setPrivacyOpen(false)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div
            key="error-toast"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => setError(null)}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-red-500 text-white px-5 py-3 rounded-2xl shadow-lg text-sm w-max max-w-[90vw] text-center cursor-pointer"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
