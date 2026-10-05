import { motion } from "framer-motion";
import { useState } from "react";
import { Sparkles } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";
import { ARCHETYPES } from "../../data/archetypes";
import { GUESS_KEY, storageGet } from "../../lib/storage";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { delay, duration: 0.5 },
});

const AXIS_LABELS: Record<string, [string, string]> = {
  E: ["Expressive", "Uses lots of media, stickers, and emoji"],
  T: ["Text-Purist", "Lets words do the talking"],
  V: ["Verbose", "Writes detailed, lengthy messages"],
  M: ["Minimal", "Gets straight to the point"],
  I: ["Initiator", "Starts conversations"],
  R: ["Reactor", "Responds and reacts"],
  N: ["Night Owl", "Most active after midnight"],
  D: ["Day Person", "Texts during normal hours"],
};

// Floating geometric particles for the gradient bg
const BG_PARTICLES = [
  { top: "7%", left: "8%", size: 7, delay: 0.3, duration: 6.0, shape: "circle" },
  { top: "15%", right: "10%", size: 9, delay: 0.8, duration: 7.2, shape: "square" },
  { top: "40%", left: "5%", size: 6, delay: 0.5, duration: 5.5, shape: "circle" },
  { top: "55%", right: "7%", size: 8, delay: 1.1, duration: 6.8, shape: "square" },
  { top: "72%", left: "14%", size: 5, delay: 0.4, duration: 5.8, shape: "circle" },
  { top: "82%", right: "18%", size: 7, delay: 0.9, duration: 6.3, shape: "circle" },
  { top: "30%", right: "22%", size: 5, delay: 0.6, duration: 6.0, shape: "square" },
];

export function TexterTypeSlide({ data, dateRange }: Props) {
  const texter = data.texter_type;
  const typeName = texter?.type ?? "The Balanced Texter";
  const description =
    texter?.description ??
    "You're a well-rounded communicator who mixes it all.";
  const funFact = texter?.fun_fact ?? "";
  const code = texter?.code ?? "";

  const codeLetters = code.split("");

  // The archetype the user guessed on the progress screen, if any.
  const [guess] = useState(() => storageGet(GUESS_KEY));
  const guessName = guess ? ARCHETYPES.find((a) => a.code === guess)?.name : undefined;
  const nailedIt = !!code && guess === code;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="w-full h-full flex flex-col items-center justify-center px-5 text-center relative overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, #6366f1 0%, #8b5cf6 40%, #a855f7 100%)",
      }}
    >
      {/* Floating bg particles */}
      {BG_PARTICLES.map((p, i) => (
        <motion.div
          key={i}
          className="absolute pointer-events-none bg-white/15"
          style={{
            width: p.size,
            height: p.size,
            top: p.top,
            left: "left" in p ? p.left : undefined,
            right: "right" in p ? p.right : undefined,
            borderRadius: p.shape === "circle" ? "50%" : "3px",
          }}
          animate={{
            opacity: [0, 0.6, 0.6, 0],
            y: [0, -24, -24, 0],
            rotate: p.shape === "square" ? [0, 45, 0] : [0, 0, 0],
          }}
          transition={{ delay: p.delay, duration: p.duration, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}

      {/* Ambient inner glow */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at 50% 30%, rgba(255,255,255,0.07) 0%, transparent 60%)",
        }}
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="max-w-xl w-full mx-auto flex flex-col items-center relative">
        <motion.div
          initial={{ scale: 0, rotate: -30 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{
            type: "spring",
            stiffness: 200,
            damping: 18,
            delay: 0.2,
          }}
          className="w-16 h-16 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center mb-4"
        >
          <motion.div
            animate={{ rotate: [0, 15, -15, 0] }}
            transition={{ delay: 1.0, duration: 1.5, repeat: Infinity, repeatDelay: 4 }}
          >
            <Sparkles className="w-8 h-8 text-white" />
          </motion.div>
        </motion.div>

        <motion.p
          {...fadeUp(0.3)}
          className="text-white/60 text-xs uppercase tracking-widest font-semibold mb-2"
        >
          Your Texting Personality
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, scale: 0.85, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.6, type: "spring", stiffness: 160, damping: 16 }}
          className="font-display text-3xl sm:text-4xl font-extrabold text-white mb-2 leading-tight"
        >
          {typeName}
        </motion.h1>

        {/* Personality code — letters pop in one by one */}
        {code && (
          <div className="flex gap-1.5 mb-4">
            {codeLetters.map((letter, i) => (
              <motion.span
                key={letter + i}
                initial={{ opacity: 0, scale: 0.3, y: -12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{
                  delay: 0.48 + i * 0.12,
                  type: "spring",
                  stiffness: 280,
                  damping: 16,
                }}
                className="text-white/60 text-sm font-mono tracking-[0.2em]"
              >
                {letter}
              </motion.span>
            ))}
          </div>
        )}

        <motion.p
          {...fadeUp(0.55)}
          className="text-white/80 text-sm sm:text-base leading-relaxed max-w-sm mb-5"
        >
          {description}
        </motion.p>

        {guessName && code && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 1.35, type: "spring", stiffness: 260, damping: 16 }}
            className={`-mt-2 mb-4 inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-semibold ${
              nailedIt ? "bg-white text-[#7C3AED]" : "bg-white/15 text-white/85"
            }`}
          >
            {nailedIt ? "🎯 You called it! You guessed this one." : `You guessed ${guessName} — close, but no 😉`}
          </motion.div>
        )}

        {/* Trait badge rows sliding in from alternating directions */}
        {code && (
          <div className="w-full max-w-xs space-y-2 mb-5">
            {codeLetters.map((letter, i) => {
              const axisInfo = AXIS_LABELS[letter];
              if (!axisInfo) return null;
              const fromLeft = i % 2 === 0;
              return (
                <motion.div
                  key={letter + i}
                  initial={{ opacity: 0, x: fromLeft ? -36 : 36 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    delay: 0.75 + i * 0.11,
                    duration: 0.45,
                    type: "spring",
                    stiffness: 180,
                    damping: 20,
                  }}
                  whileHover={{ scale: 1.03, x: fromLeft ? 4 : -4 }}
                  className="flex items-center gap-3 bg-white/10 backdrop-blur-sm rounded-xl px-4 py-2.5 cursor-default"
                >
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{
                      delay: 0.9 + i * 0.11,
                      type: "spring",
                      stiffness: 300,
                      damping: 14,
                    }}
                    className="text-white font-bold text-lg font-mono w-6 text-center shrink-0"
                  >
                    {letter}
                  </motion.span>
                  <div className="text-left">
                    <p className="text-white text-sm font-semibold leading-tight">
                      {axisInfo[0]}
                    </p>
                    <p className="text-white/50 text-xs leading-tight">
                      {axisInfo[1]}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {funFact && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1, duration: 0.5 }}
            className="bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3 max-w-sm mb-5"
          >
            <p className="text-white/70 text-xs italic leading-relaxed">
              {funFact}
            </p>
          </motion.div>
        )}

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.25, duration: 0.5 }}
          className="text-white/30 text-xs uppercase tracking-widest"
        >
          Telegram Wrapped · {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </motion.div>
  );
}
