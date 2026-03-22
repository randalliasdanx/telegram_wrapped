import { motion } from "framer-motion";
import { Clock } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { delay, duration: 0.5 },
});

function getVibeLabel(age: number): string {
  if (age <= 15) return "Gen Alpha Energy";
  if (age <= 20) return "Peak Gen Z";
  if (age <= 25) return "Young Adult Vibes";
  if (age <= 30) return "Millennial Core";
  if (age <= 40) return "Elder Millennial";
  if (age <= 50) return "Gen X Energy";
  if (age <= 60) return "Boomer-Adjacent";
  return "Distinguished Texter";
}

function getVibeEmoji(age: number): string {
  if (age <= 15) return "⚡";
  if (age <= 20) return "🔥";
  if (age <= 25) return "✨";
  if (age <= 30) return "💫";
  if (age <= 40) return "🌟";
  if (age <= 50) return "📱";
  if (age <= 60) return "📝";
  return "📖";
}

function getVibeDescription(age: number): string {
  if (age <= 15) return "Your texts are pure chaos energy — abbreviations, emoji storms, and zero punctuation. Legends only.";
  if (age <= 20) return "You text like someone who grew up with a phone in their hand. Short, fast, and dripping with personality.";
  if (age <= 25) return "A balanced blend of casual and expressive. You know when to use 'lol' and when to use actual words.";
  if (age <= 30) return "Your texting style sits right at the crossroads — casual enough to be fun, polished enough to be understood.";
  if (age <= 40) return "You remember a time before smartphones, and it shows in your thoughtful, complete sentences.";
  if (age <= 50) return "Your messages are well-composed with proper grammar. You treat texts like mini letters.";
  if (age <= 60) return "You text with intention and clarity. Every message is a small act of communication craftsmanship.";
  return "Your texts read like correspondence from a more elegant era. Proper punctuation, full words, no shortcuts.";
}

export function VibeAgeSlide({ data, dateRange }: Props) {
  const vibeAge = data.vibe_age ?? 25;
  const label = getVibeLabel(vibeAge);
  const emoji = getVibeEmoji(vibeAge);
  const description = getVibeDescription(vibeAge);

  const normalizedPosition = Math.max(0, Math.min(100, ((vibeAge - 13) / (75 - 13)) * 100));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="w-full h-full flex flex-col items-center justify-center px-5 text-center relative overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, #f97316 0%, #ef4444 40%, #ec4899 100%)",
      }}
    >
      <div className="max-w-xl w-full mx-auto flex flex-col items-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{
            type: "spring",
            stiffness: 180,
            damping: 18,
            delay: 0.2,
          }}
          className="w-16 h-16 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center mb-4"
        >
          <Clock className="w-8 h-8 text-white" />
        </motion.div>

        <motion.p
          {...fadeUp(0.3)}
          className="text-white/60 text-xs uppercase tracking-widest font-semibold mb-2"
        >
          Your Texting Vibe Age
        </motion.p>

        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6, type: "spring" }}
          className="relative mb-2"
        >
          <span className="text-8xl sm:text-9xl font-extrabold text-white">
            {vibeAge}
          </span>
        </motion.div>

        <motion.p
          {...fadeUp(0.5)}
          className="text-white/90 text-xl font-bold mb-1"
        >
          {emoji} {label}
        </motion.p>

        <motion.p
          {...fadeUp(0.65)}
          className="text-white/70 text-sm leading-relaxed max-w-sm mb-6"
        >
          {description}
        </motion.p>

        <motion.div
          {...fadeUp(0.8)}
          className="w-full max-w-xs mb-6"
        >
          <div className="flex justify-between text-white/40 text-xs mb-1.5">
            <span>13 ⚡</span>
            <span>📖 75</span>
          </div>
          <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden relative">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${normalizedPosition}%` }}
              transition={{ delay: 0.9, duration: 0.8, ease: "easeOut" }}
              className="h-full rounded-full"
              style={{
                background: "linear-gradient(90deg, #fbbf24, #ef4444, #a855f7)",
              }}
            />
          </div>
          <div className="flex justify-between text-white/30 text-xs mt-1">
            <span>Gen Alpha</span>
            <span>Gen Z</span>
            <span>Millennial</span>
            <span>Gen X+</span>
          </div>
        </motion.div>

        <motion.p
          {...fadeUp(1.0)}
          className="text-white/30 text-xs uppercase tracking-widest"
        >
          Telegram Wrapped · {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </motion.div>
  );
}
