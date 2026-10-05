import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Check, Loader2, Plug, Hash, MessagesSquare, Users, Sparkles, Bell, RotateCcw, AlertTriangle, Timer,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { SSEProgress, WrappedData } from "../api/types";
import { fetchResult, SessionExpiredError } from "../api/client";
import { usePipelineProgress } from "../hooks/usePipelineProgress";
import { ARCHETYPES } from "../data/archetypes";
import { AnimatedNumber } from "./AnimatedNumber";
import { formatDuration, hashString } from "../lib/format";
import { GUESS_KEY, storageGet, storageRemove, storageSet } from "../lib/storage";

interface Props {
  sessionId: string;
  /** Only known right after login (not after a page refresh). */
  phone?: string;
  onReady: (data: WrappedData) => void;
  onRestart: () => void;
}

const BOT_USERNAME = import.meta.env.VITE_BOT_USERNAME ?? "TelegramWrappedBot";

interface Step {
  id: string;
  label: string;
  icon: LucideIcon;
  /** Overall-progress range [start, end] this phase covers. */
  range: [number, number];
}

const STEPS: Step[] = [
  { id: "init", label: "Connecting to Telegram", icon: Plug, range: [2, 6] },
  { id: "counting", label: "Counting your chats", icon: Hash, range: [6, 20] },
  { id: "fetching", label: "Reading your messages", icon: MessagesSquare, range: [20, 68] },
  { id: "conversations", label: "Studying your conversations", icon: Users, range: [68, 90] },
  { id: "computing", label: "Crunching the numbers", icon: Sparkles, range: [90, 99] },
];

/** Phase names emitted by older backends. */
const LEGACY_PHASES: Record<string, string> = { media: "fetching", sampling: "conversations" };

function normalisePhase(phase: string | undefined): string {
  if (!phase) return "init";
  return LEGACY_PHASES[phase] ?? phase;
}

function overallPercent(p: SSEProgress | null, phase: string): number {
  if (phase === "done") return 100;
  if (phase === "queued") return 1;
  const step = STEPS.find((s) => s.id === phase);
  if (!step) return 2;
  const [a, b] = step.range;
  const frac = p?.total ? Math.min(1, Math.max(0, (p.progress ?? 0) / p.total)) : 0.35;
  return Math.round(a + (b - a) * frac);
}

function maskPhone(phone: string): string {
  const cleaned = phone.replace(/\s/g, "");
  if (cleaned.length <= 5) return cleaned;
  return `${cleaned.slice(0, 4)}${"•".repeat(Math.max(0, cleaned.length - 6))}${cleaned.slice(-2)}`;
}

function formatEta(seconds: number): string {
  if (seconds < 10) return "Almost there";
  if (seconds < 60) return `~${Math.round(seconds / 5) * 5}s left`;
  return `~${Math.round(seconds / 60)} min left`;
}

function TelegramArrow({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 56 48" fill="none" className={className}>
      <path d="M4 24L52 4L36 24L52 44L4 24Z" fill="currentColor" />
    </svg>
  );
}

const BUBBLES = [
  { left: "8%", size: 26, delay: 0, duration: 9 },
  { left: "22%", size: 16, delay: 3, duration: 11 },
  { left: "70%", size: 22, delay: 1.5, duration: 10 },
  { left: "86%", size: 14, delay: 4.5, duration: 12 },
  { left: "48%", size: 12, delay: 6, duration: 9.5 },
];

/** Picks are seeded from the session id so they're stable across re-renders and refreshes. */
function pickArchetypes(seed: string) {
  const h = hashString(seed || "telegram-wrapped");
  const n = ARCHETYPES.length;
  const picked: typeof ARCHETYPES = [];
  for (let i = 0, k = h; picked.length < 4 && i < n * 2; i++, k = Math.imul(k ^ (k >>> 15), 2246822507) >>> 0) {
    const a = ARCHETYPES[k % n];
    if (!picked.includes(a)) picked.push(a);
  }
  return { options: picked, spotlightStart: h % n };
}

export function ProgressScreen({ sessionId, phone, onReady, onRestart }: Props) {
  const { progress, expired } = usePipelineProgress(sessionId);
  const [resultError, setResultError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [{ options, spotlightStart }] = useState(() => pickArchetypes(sessionId));
  const [spotlightOffset, setSpotlightOffset] = useState(0);
  const [guess, setGuess] = useState<string | null>(() => storageGet(GUESS_KEY));

  const phase = normalisePhase(progress?.phase);
  const isDone = phase === "done";
  const errorMessage = expired
    ? "This session has expired. Log in again to rebuild your Wrapped."
    : phase === "error"
      ? progress?.message || "Something went wrong while building your Wrapped."
      : resultError;
  const isError = !!errorMessage;

  // Elapsed clock + spotlight carousel.
  useEffect(() => {
    if (isDone || isError) return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [isDone, isError]);

  useEffect(() => {
    const t = setInterval(() => setSpotlightOffset((o) => o + 1), 7000);
    return () => clearInterval(t);
  }, []);

  // When the pipeline finishes, fetch the result and hand it over.
  useEffect(() => {
    if (!isDone) return;
    let cancelled = false;
    const startedAt = Date.now();
    (async () => {
      for (let attempt = 0; attempt < 5; attempt++) {
        try {
          const data = await fetchResult(sessionId);
          // Let the "ready" celebration breathe for a moment.
          const wait = Math.max(0, 1400 - (Date.now() - startedAt));
          await new Promise((r) => setTimeout(r, wait));
          if (!cancelled) onReady(data);
          return;
        } catch (e) {
          if (e instanceof SessionExpiredError) break;
          await new Promise((r) => setTimeout(r, 1000));
          if (cancelled) return;
        }
      }
      if (!cancelled) setResultError("We finished, but couldn't load your results. Please try again.");
    })();
    return () => {
      cancelled = true;
    };
  }, [isDone, sessionId, onReady]);

  const pct = overallPercent(progress, phase);
  const currentStepIdx = isDone ? STEPS.length : STEPS.findIndex((s) => s.id === phase);
  const queued = phase === "queued";
  const analysed = progress?.messages_analyzed ?? 0;
  const spotlight = ARCHETYPES[(spotlightStart + spotlightOffset) % ARCHETYPES.length];
  const botDeepLink = `https://t.me/${BOT_USERNAME}?start=${sessionId}`;

  const headline = isError
    ? "That didn't work"
    : isDone
      ? "Your Wrapped is ready!"
      : queued
        ? "You're in the queue"
        : "Cooking your Wrapped";

  const statusLine = isError
    ? errorMessage
    : progress?.message || (queued ? "Waiting for a free worker…" : "Getting things ready…");

  const chooseGuess = (code: string) => {
    const next = guess === code ? null : code;
    setGuess(next);
    if (next) storageSet(GUESS_KEY, next);
    else storageRemove(GUESS_KEY);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.04 }}
      transition={{ duration: 0.4 }}
      className="h-full w-full overflow-y-auto overflow-x-hidden relative"
      style={{ background: "linear-gradient(160deg, #d6edf8 0%, #eaf5fb 35%, #f7fcfe 60%, #ffffff 100%)" }}
    >
      {/* Rising chat bubbles */}
      {BUBBLES.map((b, i) => (
        <motion.div
          key={i}
          className="fixed bottom-0 rounded-full rounded-bl-sm bg-[#29B6F6]/15 pointer-events-none"
          style={{ left: b.left, width: b.size, height: b.size * 0.8 }}
          initial={{ y: 40, opacity: 0 }}
          animate={{ y: "-105vh", opacity: [0, 1, 1, 0] }}
          transition={{ duration: b.duration, delay: b.delay, repeat: Infinity, ease: "linear" }}
        />
      ))}

      <div className="relative max-w-md mx-auto px-5 pt-8 pb-10 flex flex-col gap-4">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-2 text-[#2AABEE]">
            <TelegramArrow className="w-7 h-6" />
            <span className="font-display font-extrabold text-gray-900 text-sm tracking-tight">
              Telegram Wrapped
            </span>
          </div>
          {phone && (
            <div className="flex items-center gap-1.5 bg-white/80 border border-gray-200 rounded-full px-3 py-1 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2AABEE]" />
              <span className="text-gray-600 text-xs font-mono tracking-wider">{maskPhone(phone)}</span>
            </div>
          )}
        </motion.div>

        {/* Hero card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="bg-white rounded-3xl shadow-[0_10px_40px_rgba(2,136,209,0.12)] border border-white p-6 text-center relative overflow-hidden"
        >
          {/* Shimmer sweep while working */}
          {!isDone && !isError && (
            <motion.div
              className="absolute inset-0 pointer-events-none"
              style={{ background: "linear-gradient(110deg, transparent 30%, rgba(41,182,246,0.08) 50%, transparent 70%)" }}
              animate={{ x: ["-100%", "100%"] }}
              transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut", repeatDelay: 1 }}
            />
          )}

          <AnimatePresence mode="wait">
            <motion.h1
              key={headline}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="font-display text-2xl font-extrabold text-gray-900"
            >
              {headline}
              {!isError && <>{"\u00a0"}{isDone ? "🎉" : "🍳"}</>}
            </motion.h1>
          </AnimatePresence>

          {/* Big number */}
          <div className="my-5 relative flex flex-col items-center">
            {isError ? (
              <div className="w-20 h-20 rounded-full bg-red-50 flex items-center justify-center">
                <AlertTriangle className="w-9 h-9 text-red-500" />
              </div>
            ) : isDone ? (
              <motion.div
                initial={{ scale: 0, rotate: -45 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: "spring", stiffness: 260, damping: 14 }}
                className="w-20 h-20 rounded-full flex items-center justify-center shadow-lg"
                style={{ background: "linear-gradient(135deg, #29B6F6 0%, #0288D1 100%)" }}
              >
                <Check className="w-10 h-10 text-white" strokeWidth={3} />
              </motion.div>
            ) : queued ? (
              <>
                <span className="font-display text-6xl font-extrabold text-[#0288D1] leading-none">
                  #{progress?.queue_position ?? "…"}
                </span>
                <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold mt-2">
                  in line
                </span>
              </>
            ) : (
              <>
                <AnimatedNumber
                  value={analysed}
                  duration={900}
                  className="font-display text-6xl font-extrabold text-gray-900 leading-none tabular-nums"
                />
                <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold mt-2">
                  messages analysed
                </span>
              </>
            )}
          </div>

          <AnimatePresence mode="wait">
            <motion.p
              key={statusLine ?? ""}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className={`text-sm min-h-[1.25rem] ${isError ? "text-red-600" : "text-gray-500"}`}
            >
              {isDone ? "Opening your story…" : statusLine}
            </motion.p>
          </AnimatePresence>

          {!isError && (
            <>
              <div className="mt-5 h-2.5 bg-[#E1F5FE] rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full relative overflow-hidden"
                  style={{ background: "linear-gradient(90deg, #29B6F6 0%, #0288D1 100%)" }}
                  initial={{ width: "0%" }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                >
                  <motion.div
                    className="absolute inset-y-0 w-1/2"
                    style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.45), transparent)" }}
                    animate={{ x: ["-100%", "250%"] }}
                    transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
                  />
                </motion.div>
              </div>
              <div className="flex items-center justify-between mt-2 text-xs text-gray-400 font-medium">
                <span className="tabular-nums">{pct}%</span>
                <span className="flex items-center gap-1 tabular-nums">
                  <Timer className="w-3.5 h-3.5" />
                  {isDone
                    ? "All done"
                    : progress?.eta_seconds != null
                      ? formatEta(progress.eta_seconds)
                      : `${formatDuration(elapsed)} elapsed`}
                </span>
              </div>
            </>
          )}

          {isError && (
            <button
              onClick={onRestart}
              className="mt-5 inline-flex items-center gap-2 bg-[#2AABEE] hover:bg-[#229ED9] text-white font-semibold text-sm px-6 py-3 rounded-full shadow-md active:scale-95 transition-all"
            >
              <RotateCcw className="w-4 h-4" />
              Try again
            </button>
          )}
        </motion.div>

        {/* Phase checklist */}
        {!isError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="bg-white/80 backdrop-blur rounded-3xl border border-white shadow-sm px-5 py-4"
          >
            <ol className="relative">
              {STEPS.map((step, i) => {
                const state = i < currentStepIdx ? "done" : i === currentStepIdx ? "active" : "pending";
                const Icon = step.icon;
                return (
                  <li key={step.id} className="flex items-center gap-3 py-1.5 relative">
                    {i < STEPS.length - 1 && (
                      <span
                        className={`absolute left-[13px] top-[30px] w-0.5 h-[calc(100%-20px)] rounded-full transition-colors duration-500 ${
                          state === "done" ? "bg-[#29B6F6]" : "bg-gray-200"
                        }`}
                      />
                    )}
                    <motion.span
                      layout
                      className={`relative z-10 w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-colors duration-500 ${
                        state === "done"
                          ? "bg-[#29B6F6] text-white"
                          : state === "active"
                            ? "bg-[#0288D1] text-white shadow-[0_0_0_4px_rgba(41,182,246,0.2)]"
                            : "bg-gray-100 text-gray-400"
                      }`}
                    >
                      {state === "done" ? (
                        <Check className="w-4 h-4" strokeWidth={3} />
                      ) : state === "active" ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Icon className="w-3.5 h-3.5" />
                      )}
                    </motion.span>
                    <span
                      className={`text-sm transition-colors duration-500 ${
                        state === "active"
                          ? "font-semibold text-gray-900"
                          : state === "done"
                            ? "text-gray-500"
                            : "text-gray-400"
                      }`}
                    >
                      {step.label}
                    </span>
                    {state === "active" && progress?.total ? (
                      <span className="ml-auto text-xs text-gray-400 tabular-nums">
                        {progress.progress ?? 0}/{progress.total}
                      </span>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          </motion.div>
        )}

        {/* Mini game */}
        {!isError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.5 }}
            className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5"
          >
            <p className="text-[10px] uppercase tracking-widest text-[#2AABEE] font-bold mb-1">While you wait</p>
            <p className="font-display text-lg font-bold text-gray-900 mb-3">Which archetype are you?</p>
            <div className="flex flex-wrap gap-2">
              {options.map((arch) => (
                <button
                  key={arch.code}
                  onClick={() => chooseGuess(arch.code)}
                  className={`text-xs font-semibold px-3.5 py-1.5 rounded-full border transition-all active:scale-95 ${
                    guess === arch.code
                      ? "bg-[#2AABEE] border-[#2AABEE] text-white shadow"
                      : "bg-white border-gray-300 text-gray-700 hover:border-[#2AABEE] hover:text-[#2AABEE]"
                  }`}
                >
                  {arch.name}
                </button>
              ))}
            </div>
            <AnimatePresence>
              {guess && options.some((o) => o.code === guess) && (
                <motion.p
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="text-xs text-gray-500 mt-3 italic"
                >
                  Locked in. We'll tell you if your Wrapped agrees ✨
                </motion.p>
              )}
            </AnimatePresence>

            <div className="mt-4 pt-4 border-t border-dashed border-gray-200 min-h-[92px]">
              <AnimatePresence mode="wait">
                <motion.div
                  key={spotlight.code}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.3 }}
                >
                  <span className="text-[10px] font-bold tracking-widest text-[#2AABEE] bg-[#2AABEE]/10 px-2 py-0.5 rounded-md uppercase">
                    Spotlight · {spotlight.name}
                  </span>
                  <p className="text-gray-600 text-sm leading-relaxed mt-2">{spotlight.description}</p>
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.div>
        )}

        {/* Optional bot notification */}
        {!isError && !isDone && (
          <motion.a
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            href={botDeepLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-2xl border border-[#2AABEE]/30 bg-white/60 px-4 py-3 hover:bg-white transition-colors"
          >
            <span className="w-9 h-9 rounded-full bg-[#2AABEE]/10 flex items-center justify-center shrink-0">
              <Bell className="w-4 h-4 text-[#2AABEE]" />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-sm font-semibold text-gray-800">Start the bot to get notified</span>
              <span className="block text-xs text-gray-500">Leaving? We'll message you on Telegram when it's ready.</span>
            </span>
          </motion.a>
        )}
      </div>
    </motion.div>
  );
}
