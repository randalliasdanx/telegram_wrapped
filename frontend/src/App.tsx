import { useState, useCallback, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import type { WrappedData } from "./api/types";
import { startPipeline, fetchResult } from "./api/client";
import { AuthSlide } from "./components/slides/AuthSlide";
import { WaitingScreen } from "./components/WaitingScreen";
import { WrappedViewer } from "./components/WrappedViewer";
import { PrivacyPolicy } from "./components/PrivacyPolicy";

type AppState = "auth" | "waiting" | "viewing";

export default function App() {
  const [state, setState] = useState<AppState>("auth");
  const [sessionId, setSessionId] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [data, setData] = useState<WrappedData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [privacyOpen, setPrivacyOpen] = useState(false);

  // On mount: check for ?session= URL param (user returning from bot notification link)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("session");
    if (!sid) return;

    // Clean the URL without reloading
    window.history.replaceState({}, "", window.location.pathname);

    fetchResult(sid)
      .then((result) => {
        setData(result);
        setState("viewing");
      })
      .catch(() => {
        setError("Your session has expired. Please start again.");
      });
  }, []);

  const handleAuthenticated = useCallback(async (sid: string, phoneNumber: string) => {
    setSessionId(sid);
    setPhone(phoneNumber);
    setError(null);
    try {
      await startPipeline(sid);
      setState("waiting");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start pipeline");
    }
  }, []);

  return (
    <div className="h-dvh w-screen overflow-hidden bg-black">
      <AnimatePresence mode="wait">
        {state === "auth" && (
          <AuthSlide
            key="auth"
            onAuthenticated={handleAuthenticated}
            onPrivacyOpen={() => setPrivacyOpen(true)}
          />
        )}

        {state === "waiting" && (
          <WaitingScreen
            key="waiting"
            phone={phone}
            sessionId={sessionId}
          />
        )}

        {state === "viewing" && data && (
          <WrappedViewer key="viewer" data={data} />
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
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-red-500 text-white px-6 py-3 rounded-full shadow-lg text-sm max-w-[90vw] text-center">
            {error}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
