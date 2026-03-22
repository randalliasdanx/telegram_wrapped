import { motion } from "framer-motion";
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

function FlameIcon() {
  return (
    <svg width="100" height="100" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M60 10C60 10 30 45 30 72C30 90 43.4 105 60 105C76.6 105 90 90 90 72C90 45 60 10 60 10Z"
        fill="white" fillOpacity="0.95"
      />
      <path
        d="M60 50C60 50 45 68 45 80C45 88.3 51.7 95 60 95C68.3 95 75 88.3 75 80C75 68 60 50 60 50Z"
        fill="#F59E0B" fillOpacity="0.7"
      />
    </svg>
  );
}

// Fire particle positions — rise upward from around the flame
const FIRE_PARTICLES = [
  { x: -22, delay: 0.2, duration: 2.4, size: 8 },
  { x: 0, delay: 0.5, duration: 2.1, size: 10 },
  { x: 18, delay: 0.8, duration: 2.6, size: 7 },
  { x: -10, delay: 1.1, duration: 2.3, size: 9 },
  { x: 28, delay: 0.3, duration: 2.8, size: 6 },
  { x: -30, delay: 0.7, duration: 2.0, size: 8 },
];

// Background floating spark dots
const SPARKS = [
  { top: "10%", left: "10%", delay: 0.3, duration: 5.0 },
  { top: "20%", right: "14%", delay: 0.9, duration: 4.5 },
  { top: "55%", left: "7%", delay: 0.5, duration: 5.5 },
  { top: "65%", right: "9%", delay: 1.2, duration: 4.8 },
  { top: "80%", left: "25%", delay: 0.7, duration: 5.2 },
  { top: "85%", right: "28%", delay: 0.4, duration: 4.6 },
];

export function StreakSlide({ data, dateRange }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="w-full h-full flex flex-col items-center justify-center px-5 text-center relative overflow-hidden"
      style={{
        background: "linear-gradient(180deg, #FBBF24 0%, #F59E0B 50%, #EA580C 100%)",
      }}
    >
      {/* Background spark particles */}
      {SPARKS.map((s, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-white/25 pointer-events-none"
          style={{
            width: 5,
            height: 5,
            top: s.top,
            left: "left" in s ? s.left : undefined,
            right: "right" in s ? s.right : undefined,
          }}
          animate={{
            opacity: [0, 0.7, 0.7, 0],
            y: [0, -30, -30, 0],
            scale: [0.5, 1.2, 1.2, 0.5],
          }}
          transition={{
            delay: s.delay,
            duration: s.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}

      {/* Warm radial glow behind flame */}
      <motion.div
        className="absolute pointer-events-none"
        style={{
          width: 260,
          height: 260,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 65%)",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -80%)",
        }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="max-w-xl w-full mx-auto flex flex-col items-center">
        <motion.div {...fadeUp(0.15)} className="mb-1">
          <p className="text-white/70 text-xs font-semibold tracking-widest uppercase">
            Telegram Wrapped
          </p>
          <p className="text-white/70 text-xs mt-0.5">
            {dateRange.start} – {dateRange.end}
          </p>
        </motion.div>

        <motion.span
          {...fadeUp(0.3)}
          className="inline-block bg-white/20 backdrop-blur-sm text-white text-sm font-semibold px-5 py-1.5 rounded-full mb-5"
        >
          Consistency is Key
        </motion.span>

        {/* Flame + fire particles */}
        <div className="relative mb-2" style={{ height: 120 }}>
          <motion.div
            initial={{ scale: 0, rotate: -30 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 160, damping: 16, delay: 0.4 }}
            className="relative"
          >
            <FlameIcon />
            <motion.span
              {...fadeUp(0.6)}
              className="absolute -top-2 -right-14 bg-white/90 text-orange-600 text-xs font-bold px-3 py-1 rounded-full shadow"
            >
              ON FIRE!
            </motion.span>
          </motion.div>

          {/* Fire particle emitters rising from flame top */}
          {FIRE_PARTICLES.map((fp, i) => (
            <motion.div
              key={i}
              className="absolute pointer-events-none rounded-full"
              style={{
                width: fp.size,
                height: fp.size,
                background: "rgba(255,255,255,0.6)",
                bottom: 70,
                left: "50%",
                marginLeft: fp.x,
              }}
              animate={{
                y: [0, -50, -90],
                opacity: [0, 0.8, 0],
                scale: [0.5, 1, 0.3],
              }}
              transition={{
                delay: fp.delay,
                duration: fp.duration,
                repeat: Infinity,
                ease: "easeOut",
              }}
            />
          ))}
        </div>

        {/* Streak number with bounce */}
        <motion.p
          initial={{ opacity: 0, scale: 0.4, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{
            delay: 0.55,
            duration: 0.7,
            type: "spring",
            stiffness: 220,
            damping: 14,
          }}
          className="font-display text-8xl sm:text-9xl font-extrabold text-white leading-none mb-1"
        >
          {data.longest_streak}
        </motion.p>

        <motion.p {...fadeUp(0.65)} className="text-white text-xl sm:text-2xl font-bold mb-4">
          Days in a row!
        </motion.p>

        <motion.p
          {...fadeUp(0.75)}
          className="text-white/80 text-sm sm:text-base max-w-xs leading-relaxed"
        >
          You and <span className="font-bold">{data.streak_partner}</span> have
          kept the conversation burning.
        </motion.p>
      </div>
    </motion.div>
  );
}
