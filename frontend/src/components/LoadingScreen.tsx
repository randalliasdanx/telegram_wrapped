import { motion } from "framer-motion";
import { Send } from "lucide-react";
import { useSSE } from "../hooks/useSSE";
import { useEffect } from "react";

interface Props {
  sessionId: string;
  onComplete: () => void;
}

const PHASE_MESSAGES: Record<string, string> = {
  init: "Connecting to Telegram...",
  counting: "Counting your messages...",
  media: "Analyzing your media...",
  sampling: "Sampling conversations...",
  computing: "Crunching the numbers...",
  done: "Your Wrapped is ready!",
  error: "Something went wrong",
};

const floatingBubbles = [
  { x: "10%", y: "15%", size: 40, delay: 0 },
  { x: "80%", y: "20%", size: 30, delay: 0.5 },
  { x: "20%", y: "70%", size: 35, delay: 1.0 },
  { x: "75%", y: "65%", size: 25, delay: 1.5 },
  { x: "50%", y: "85%", size: 28, delay: 0.8 },
  { x: "15%", y: "45%", size: 22, delay: 1.2 },
  { x: "85%", y: "40%", size: 32, delay: 0.3 },
];

export function LoadingScreen({ sessionId, onComplete }: Props) {
  const { progress, done } = useSSE(`/api/wrapped/progress/${sessionId}`);

  const phase = progress?.phase ?? "init";
  const message = progress?.message ?? PHASE_MESSAGES[phase] ?? "Processing...";
  const current = progress?.progress ?? 0;
  const total = progress?.total ?? 0;

  useEffect(() => {
    if (done && phase === "done") {
      const t = setTimeout(onComplete, 1200);
      return () => clearTimeout(t);
    }
  }, [done, phase, onComplete]);

  const progressPct =
    total > 0 ? Math.round((current / total) * 100) : phase === "done" ? 100 : 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="h-full w-full flex flex-col items-center justify-center px-6 text-center relative overflow-hidden select-none"
      style={{
        background: "linear-gradient(135deg, #29B6F6 0%, #0288D1 100%)",
      }}
    >
      {floatingBubbles.map((b, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-white/5"
          style={{ left: b.x, top: b.y, width: b.size, height: b.size }}
          animate={{
            y: [0, -15, 0],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 3 + i * 0.3,
            repeat: Infinity,
            ease: "easeInOut",
            delay: b.delay,
          }}
        />
      ))}

      <motion.div
        animate={{ y: [0, -8, 0], rotate: [0, 5, -5, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="w-20 h-20 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center mb-8"
      >
        <Send className="w-8 h-8 text-white" />
      </motion.div>

      <motion.h2
        key={phase}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="font-display text-xl md:text-2xl font-bold text-white mb-3"
      >
        {message}
      </motion.h2>

      {total > 0 && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-white/60 text-sm mb-6"
        >
          {current} / {total}
        </motion.p>
      )}

      <div className="w-full max-w-xs mb-8">
        <div className="h-1.5 bg-white/15 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-white rounded-full"
            initial={{ width: "0%" }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
      </div>

      <motion.p
        animate={{ opacity: [0.4, 0.7, 0.4] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="text-white/50 text-xs"
      >
        This may take 1-2 minutes
      </motion.p>

      {phase === "error" && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-4 text-red-200 text-sm bg-red-500/20 px-4 py-2 rounded-xl"
        >
          {progress?.message ?? "An error occurred. Please try again."}
        </motion.p>
      )}
    </motion.div>
  );
}
