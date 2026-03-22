import { motion } from "framer-motion";
import { MessageSquare, ArrowUpRight, ArrowDownLeft } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

// Floating particle dots for the gradient background
const PARTICLES = [
  { top: "8%", left: "15%", size: 5, delay: 0.3, duration: 6.0 },
  { top: "18%", right: "12%", size: 4, delay: 0.8, duration: 7.2 },
  { top: "40%", left: "6%", size: 6, delay: 0.5, duration: 5.5 },
  { top: "55%", right: "8%", size: 3, delay: 1.1, duration: 6.8 },
  { top: "70%", left: "20%", size: 5, delay: 0.2, duration: 5.9 },
  { top: "80%", right: "22%", size: 4, delay: 0.9, duration: 7.0 },
  { top: "30%", right: "30%", size: 3, delay: 0.6, duration: 6.3 },
  { top: "90%", left: "40%", size: 4, delay: 1.3, duration: 5.7 },
];

export function ConversationStarterSlide({ data, dateRange }: Props) {
  const { user_pct, other_pct } = data.conversation_starter;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="w-full h-full flex flex-col items-center justify-center px-5 text-center relative overflow-hidden"
      style={{
        background: "linear-gradient(180deg, #1a3a5c 0%, #2980b9 55%, #5dade2 100%)",
      }}
    >
      {/* Floating particle dots */}
      {PARTICLES.map((p, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-white/20 pointer-events-none"
          style={{
            width: p.size,
            height: p.size,
            top: p.top,
            left: "left" in p ? p.left : undefined,
            right: "right" in p ? p.right : undefined,
          }}
          initial={{ opacity: 0, y: 0 }}
          animate={{
            opacity: [0, 0.6, 0.6, 0],
            y: [0, -22, -22, 0],
          }}
          transition={{
            delay: p.delay,
            duration: p.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}

      <div className="max-w-xl w-full mx-auto flex flex-col items-center">
        <motion.div
          initial={{ scale: 0, rotate: -20 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 200, damping: 18, delay: 0.2 }}
          className="mb-5"
        >
          <MessageSquare className="w-12 h-12 text-white/50" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="font-display text-4xl md:text-5xl font-bold text-white mb-2"
        >
          The Conversation Starter
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45, duration: 0.5 }}
          className="text-white/70 text-base mb-8"
        >
          Who breaks the silence?
        </motion.p>

        {/* Split percentage reveal from opposite sides */}
        <div className="flex items-center justify-center gap-8 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -48, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ delay: 0.6, duration: 0.55, type: "spring", stiffness: 150, damping: 16 }}
            className="flex flex-col items-center"
          >
            <span className="text-5xl sm:text-6xl font-bold text-white leading-none">{user_pct}%</span>
            <span className="text-white/50 text-xs mt-1 uppercase tracking-widest">You</span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            transition={{ delay: 0.75, duration: 0.4 }}
            className="w-px h-10 bg-white/20"
          />

          <motion.div
            initial={{ opacity: 0, x: 48, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ delay: 0.6, duration: 0.55, type: "spring", stiffness: 150, damping: 16 }}
            className="flex flex-col items-center"
          >
            <span className="text-5xl sm:text-6xl font-bold text-white leading-none">{other_pct}%</span>
            <span className="text-white/50 text-xs mt-1 uppercase tracking-widest">Them</span>
          </motion.div>
        </div>

        {/* Split bar visualizing the ratio */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: 0.85, duration: 0.6, ease: "easeOut" }}
          className="w-full h-2 rounded-full bg-white/10 mb-8 overflow-hidden"
          style={{ originX: 0 }}
        >
          <motion.div
            initial={{ width: "0%" }}
            animate={{ width: `${user_pct}%` }}
            transition={{ delay: 1.1, duration: 0.8, ease: "easeOut" }}
            className="h-full rounded-full bg-white/70"
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.5, type: "spring", stiffness: 130, damping: 18 }}
          className="flex items-stretch gap-3 w-full"
        >
          <motion.div
            whileHover={{ scale: 1.03, y: -2 }}
            className="flex-1 bg-white rounded-2xl p-4 flex flex-col items-center gap-2 shadow-lg cursor-default"
          >
            <ArrowUpRight className="w-6 h-6 text-[#2980b9]" />
            <span className="font-bold text-gray-900 text-base">YOU</span>
            <span className="text-gray-500 text-xs">Initiator</span>
          </motion.div>

          <motion.div
            whileHover={{ scale: 1.03, y: -2 }}
            className="flex-1 bg-white/10 rounded-2xl p-4 flex flex-col items-center gap-2 backdrop-blur-sm cursor-default"
          >
            <ArrowDownLeft className="w-6 h-6 text-white" />
            <span className="font-bold text-white text-base">THEM</span>
            <span className="text-white/70 text-xs">Replier</span>
          </motion.div>
        </motion.div>
      </div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.1, duration: 0.5 }}
        className="absolute bottom-8 text-white/40 text-xs"
      >
        Telegram Wrapped · {dateRange.start} – {dateRange.end}
      </motion.p>
    </motion.div>
  );
}
