import { motion } from "framer-motion";
import { Moon, Zap } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

function formatHour(hour: number): string {
  const period = hour >= 12 ? "PM" : "AM";
  const h = hour % 12 || 12;
  return `${h}:00 ${period}`;
}

const CIRCLE_RADIUS = 75;
const CIRCUMFERENCE = 2 * Math.PI * CIRCLE_RADIUS;

// Starfield dots around the clock
const STAR_POSITIONS = [
  { angle: 20, dist: 100, size: 3, delay: 0.5 },
  { angle: 55, dist: 95, size: 2, delay: 0.7 },
  { angle: 100, dist: 102, size: 3.5, delay: 0.6 },
  { angle: 145, dist: 98, size: 2, delay: 0.9 },
  { angle: 200, dist: 105, size: 2.5, delay: 0.4 },
  { angle: 250, dist: 96, size: 3, delay: 1.0 },
  { angle: 300, dist: 103, size: 2, delay: 0.8 },
  { angle: 340, dist: 97, size: 3, delay: 0.55 },
];

export function PeakActivitySlide({ data, dateRange }: Props) {
  const peakFraction = data.peak_hour / 24;
  const strokeOffset = CIRCUMFERENCE * (1 - peakFraction);

  return (
    <div className="w-full h-full bg-white flex flex-col items-center justify-center px-5 relative overflow-hidden">
      {/* Ambient background blobs */}
      <motion.div
        className="absolute top-[-15%] right-[-10%] w-72 h-72 rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(34,211,238,0.07) 0%, transparent 70%)" }}
        animate={{ x: [0, -12, 0], y: [0, 15, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[-10%] left-[-5%] w-64 h-64 rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(2,136,209,0.06) 0%, transparent 70%)" }}
        animate={{ x: [0, 10, 0], y: [0, -12, 0] }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="max-w-xl w-full mx-auto flex flex-col items-center">
        <motion.span
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-[#0288D1] uppercase tracking-widest text-xs font-semibold mb-4"
        >
          My Peak Activity
        </motion.span>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="text-center mb-5"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900">
            You're a true
          </h2>
          <h2 className="text-4xl md:text-5xl font-bold bg-linear-to-r from-cyan-400 to-blue-600 bg-clip-text text-transparent font-display">
            {data.peak_personality}.
          </h2>
        </motion.div>

        {/* Clock circle with radial glow and starfield */}
        <motion.div
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4, duration: 0.6, type: "spring", stiffness: 140, damping: 16 }}
          className="relative mb-5"
          style={{ width: 200, height: 200 }}
        >
          {/* Radial glow backdrop */}
          <motion.div
            className="absolute inset-0 rounded-full pointer-events-none"
            style={{
              background: "radial-gradient(circle, rgba(34,211,238,0.13) 0%, transparent 65%)",
              top: "50%",
              left: "50%",
              transform: "translate(-50%,-50%)",
              width: 200,
              height: 200,
            }}
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Starfield */}
          {STAR_POSITIONS.map((star, i) => {
            const rad = (star.angle * Math.PI) / 180;
            const cx = 100 + star.dist * Math.cos(rad);
            const cy = 100 + star.dist * Math.sin(rad);
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: [0, 0.7, 0.4, 0.7], scale: 1 }}
                transition={{
                  delay: star.delay,
                  duration: 2.5,
                  repeat: Infinity,
                  repeatType: "reverse",
                  ease: "easeInOut",
                }}
                className="absolute rounded-full bg-cyan-400 pointer-events-none"
                style={{
                  width: star.size,
                  height: star.size,
                  left: cx - star.size / 2,
                  top: cy - star.size / 2,
                }}
              />
            );
          })}

          <svg width="200" height="200" viewBox="0 0 200 200" className="w-full h-full">
            <defs>
              <linearGradient id="arcGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#22d3ee" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <filter id="arcGlow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            {/* Track */}
            <circle cx="100" cy="100" r={CIRCLE_RADIUS} fill="none" stroke="#e5e7eb" strokeWidth={8} />
            {/* Animated arc with trailing glow */}
            <motion.circle
              cx="100" cy="100" r={CIRCLE_RADIUS} fill="none"
              stroke="url(#arcGradient)" strokeWidth={10} strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              initial={{ strokeDashoffset: CIRCUMFERENCE }}
              animate={{ strokeDashoffset: strokeOffset }}
              transition={{ delay: 0.65, duration: 1.4, ease: "easeOut" }}
              transform="rotate(-90 100 100)"
              filter="url(#arcGlow)"
              style={{ opacity: 0.95 }}
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold">
              Peak Hour
            </span>
            <motion.span
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 1.2, type: "spring", stiffness: 200, damping: 14 }}
              className="text-xl sm:text-2xl font-bold text-gray-900 mt-1"
            >
              {formatHour(data.peak_hour)}
            </motion.span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.85, duration: 0.5 }}
          className="grid grid-cols-2 gap-3 w-full mb-5"
        >
          <motion.div
            whileHover={{ y: -3, boxShadow: "0 8px 24px rgba(99,102,241,0.12)" }}
            className="bg-gray-50 rounded-2xl p-4 flex flex-col items-center text-center cursor-default"
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center mb-2">
              <Moon className="w-5 h-5 text-indigo-600" />
            </div>
            <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold">
              Most Active
            </span>
            <span className="text-sm font-semibold text-gray-900 mt-1">
              Late Night
            </span>
            <span className="text-xs text-gray-500">11 PM – 2 AM</span>
          </motion.div>

          <motion.div
            whileHover={{ y: -3, boxShadow: "0 8px 24px rgba(245,158,11,0.12)" }}
            className="bg-gray-50 rounded-2xl p-4 flex flex-col items-center text-center cursor-default"
          >
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center mb-2">
              <Zap className="w-5 h-5 text-amber-600" />
            </div>
            <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold">
              Night Messages
            </span>
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 1.0, type: "spring", stiffness: 200, damping: 14 }}
              className="text-sm font-semibold text-gray-900 mt-1"
            >
              {data.total_night_messages.toLocaleString()}
            </motion.span>
            <span className="text-xs text-gray-500">sent after sunset</span>
          </motion.div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.5 }}
          className="text-xs uppercase tracking-widest text-gray-300 font-semibold"
        >
          Telegram Wrapped · {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </div>
  );
}
