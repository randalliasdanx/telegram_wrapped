import { motion } from "framer-motion";
import { Send } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

const EMOJI_LABELS: Record<string, string> = {
  "😂": "TIMES LAUGHED",
  "❤️": "TIMES LOVED",
  "😭": "TIMES CRIED",
  "🔥": "TIMES LIT",
  "😍": "TIMES ADORED",
  "👍": "TIMES APPROVED",
  "🙏": "TIMES GRATEFUL",
  "😊": "TIMES SMILED",
  "🥰": "TIMES CHARMED",
  "💀": "TIMES DEAD",
};

function getEmojiLabel(emoji: string): string {
  return EMOJI_LABELS[emoji] ?? "TIMES USED";
}

const cardVariants = {
  hidden: { opacity: 0, scale: 0.7, y: 24 },
  show: (i: number) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      delay: 0.45 + i * 0.1,
      duration: 0.55,
      type: "spring" as const,
      stiffness: 220,
      damping: 18,
    },
  }),
};

const emojiPop = {
  hidden: { opacity: 0, scale: 0.3, rotate: -15 },
  show: (i: number) => ({
    opacity: 1,
    scale: 1,
    rotate: 0,
    transition: {
      delay: 0.6 + i * 0.12,
      type: "spring" as const,
      stiffness: 280,
      damping: 16,
    },
  }),
};

// Confetti-like burst dots that appear at mount and float away
const CONFETTI = [
  { x: -60, y: -40, color: "#60a5fa", size: 6, delay: 0.5 },
  { x: 55, y: -50, color: "#f472b6", size: 5, delay: 0.6 },
  { x: -40, y: 50, color: "#34d399", size: 7, delay: 0.55 },
  { x: 70, y: 35, color: "#fbbf24", size: 5, delay: 0.65 },
  { x: -75, y: 20, color: "#a78bfa", size: 6, delay: 0.5 },
  { x: 80, y: -20, color: "#fb923c", size: 5, delay: 0.7 },
  { x: 10, y: -65, color: "#38bdf8", size: 6, delay: 0.58 },
  { x: -20, y: 70, color: "#f87171", size: 5, delay: 0.62 },
];

// Subtle animated background blobs
const BLOBS = [
  { top: "5%", left: "0%", color: "rgba(59,130,246,0.06)" },
  { top: "60%", right: "0%", color: "rgba(99,102,241,0.05)" },
];

export function EmojiPersonalitySlide({ data, dateRange }: Props) {
  const emojis = data.top_emojis.slice(0, 5);
  const top = emojis[0];
  const rest = emojis.slice(1);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-full bg-linear-to-br from-slate-50 to-blue-50 px-5 flex items-center justify-center overflow-y-auto relative"
    >
      {/* Ambient background blobs */}
      {BLOBS.map((b, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full pointer-events-none"
          style={{
            width: 300,
            height: 300,
            background: `radial-gradient(circle, ${b.color} 0%, transparent 70%)`,
            top: b.top,
            left: "left" in b ? b.left : undefined,
            right: "right" in b ? b.right : undefined,
          }}
          animate={{ x: [0, i % 2 === 0 ? 12 : -12, 0], y: [0, i % 2 === 0 ? 10 : -10, 0] }}
          transition={{ duration: 14 + i * 2, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}

      <div className="max-w-xl w-full mx-auto py-14 relative">
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex items-center gap-2 mb-5"
        >
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
            <Send className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-medium text-gray-400 tracking-wide">
            Telegram Wrapped
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="font-display text-4xl font-bold leading-tight mb-3"
        >
          <span className="text-black">Your </span>
          <span className="text-blue-500">Emoji </span>
          <span className="text-black">personality</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.5 }}
          className="text-gray-500 text-sm leading-relaxed mb-6"
        >
          You've expressed yourself in thousands of ways this year. Here are
          the ones that truly stuck.
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="mb-4"
        >
          <h2 className="font-display text-xl font-bold text-gray-900">
            Top Emotions
          </h2>
          <p className="text-xs text-gray-400 uppercase tracking-widest mt-1">
            {dateRange.start} – {dateRange.end}
          </p>
        </motion.div>

        <div className="grid grid-cols-2 gap-3">
          {top && (
            <motion.div
              custom={0}
              variants={cardVariants}
              initial="hidden"
              animate="show"
              whileHover={{ scale: 1.03, y: -3, boxShadow: "0 12px 32px rgba(59,130,246,0.12)" }}
              className="col-span-1 row-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-4 flex flex-col items-center justify-center text-center cursor-default relative overflow-hidden"
            >
              {/* Shimmer on the hero card */}
              <motion.div
                className="absolute inset-0 pointer-events-none"
                style={{
                  background: "linear-gradient(110deg, transparent 35%, rgba(59,130,246,0.06) 50%, transparent 65%)",
                }}
                animate={{ x: ["-100%", "200%"] }}
                transition={{ delay: 1.2, duration: 2.0, repeat: Infinity, repeatDelay: 4.0, ease: "easeInOut" }}
              />
              <span className="inline-block bg-blue-50 text-blue-600 text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full mb-2">
                #1 Most Used
              </span>

              {/* Confetti burst around the hero emoji */}
              <div className="relative inline-flex items-center justify-center mb-2">
                {CONFETTI.map((c, ci) => (
                  <motion.div
                    key={ci}
                    className="absolute rounded-full pointer-events-none"
                    style={{ width: c.size, height: c.size, background: c.color }}
                    initial={{ x: 0, y: 0, opacity: 0, scale: 0 }}
                    animate={{
                      x: [0, c.x],
                      y: [0, c.y],
                      opacity: [0, 0.9, 0],
                      scale: [0, 1.2, 0],
                    }}
                    transition={{
                      delay: c.delay,
                      duration: 0.9,
                      ease: "easeOut",
                    }}
                  />
                ))}
                <motion.span
                  custom={0}
                  variants={emojiPop}
                  initial="hidden"
                  animate="show"
                  className="text-5xl"
                >
                  {top.emoji}
                </motion.span>
              </div>

              <p className="text-xl font-bold text-gray-900">
                {top.count.toLocaleString()}
              </p>
              <p className="text-xs text-gray-400 uppercase tracking-widest mt-1">
                {getEmojiLabel(top.emoji)}
              </p>
            </motion.div>
          )}

          {rest.map((e, i) => (
            <motion.div
              key={e.emoji}
              custom={i + 1}
              variants={cardVariants}
              initial="hidden"
              animate="show"
              whileHover={{ scale: 1.05, y: -3, boxShadow: "0 8px 24px rgba(0,0,0,0.08)" }}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-3 flex flex-col items-center justify-center text-center cursor-default"
            >
              <span className="text-xs font-semibold text-gray-300 mb-1">
                #{i + 2}
              </span>
              <motion.span
                custom={i + 1}
                variants={emojiPop}
                initial="hidden"
                animate="show"
                className="text-3xl mb-1"
              >
                {e.emoji}
              </motion.span>
              <p className="text-sm font-bold text-gray-900">
                {e.count.toLocaleString()}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
