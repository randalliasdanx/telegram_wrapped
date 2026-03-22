import { motion } from "framer-motion";
import { Calendar, CheckCheck, MessageCircle } from "lucide-react";
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

// Subtle floating particles for dark background
const PARTICLES = [
  { top: "12%", left: "8%", size: 4, delay: 0.4, duration: 6.0 },
  { top: "25%", right: "10%", size: 3, delay: 1.0, duration: 5.5 },
  { top: "60%", left: "5%", size: 5, delay: 0.7, duration: 6.5 },
  { top: "75%", right: "7%", size: 3, delay: 0.2, duration: 5.8 },
  { top: "88%", left: "30%", size: 4, delay: 1.2, duration: 6.2 },
];

export function MostReactedSlide({ data, dateRange }: Props) {
  const msg = data.most_reacted_message;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="w-full h-full flex flex-col px-5 py-14 relative overflow-y-auto"
      style={{ background: "#0F172A" }}
    >
      {/* Ambient cyan glow top-right */}
      <motion.div
        className="absolute top-[-8%] right-[-8%] pointer-events-none rounded-full"
        style={{
          width: 260,
          height: 260,
          background: "radial-gradient(circle, rgba(34,211,238,0.08) 0%, transparent 70%)",
        }}
        animate={{ x: [0, -10, 0], y: [0, 14, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Floating particles */}
      {PARTICLES.map((p, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-cyan-400/20 pointer-events-none"
          style={{
            width: p.size,
            height: p.size,
            top: p.top,
            left: "left" in p ? p.left : undefined,
            right: "right" in p ? p.right : undefined,
          }}
          animate={{ opacity: [0, 0.5, 0.5, 0], y: [0, -20, -20, 0] }}
          transition={{ delay: p.delay, duration: p.duration, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}

      <div className="max-w-xl w-full mx-auto flex flex-col flex-1">
        <motion.div {...fadeUp(0.1)} className="flex items-center justify-between mb-6">
          <p className="text-cyan-400 text-xs font-semibold tracking-widest uppercase">
            Telegram Wrapped
          </p>
          <motion.div
            className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center"
            animate={{ boxShadow: ["0 0 0px rgba(59,130,246,0)", "0 0 14px rgba(59,130,246,0.6)", "0 0 0px rgba(59,130,246,0)"] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          >
            <MessageCircle className="w-4 h-4 text-white" />
          </motion.div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.55, type: "spring", stiffness: 140, damping: 20 }}
          className="font-display text-4xl md:text-5xl font-bold text-white mb-5"
        >
          The Crowd Went Wild
        </motion.h1>

        {msg ? (
          <>
            <motion.p {...fadeUp(0.3)} className="text-gray-400 text-sm mb-3">
              Most reacted message in{" "}
              <span className="text-white font-bold">{msg.chat}</span>
            </motion.p>

            {/* Message bubble with shimmer */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              whileHover={{ scale: 1.01 }}
              className="relative bg-[#1E293B] rounded-2xl p-4 mb-3 overflow-hidden cursor-default"
            >
              {/* Shimmer sweep */}
              <motion.div
                className="absolute inset-0 pointer-events-none"
                style={{
                  background: "linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.04) 50%, transparent 60%)",
                }}
                animate={{ x: ["-100%", "200%"] }}
                transition={{ delay: 1.0, duration: 1.8, repeat: Infinity, repeatDelay: 3.5, ease: "easeInOut" }}
              />
              {msg.reply_preview && (
                <div className="border-l-2 border-blue-400 pl-3 mb-3">
                  <p className="text-gray-400 text-xs font-semibold">{msg.sender}</p>
                  <p className="text-gray-400 text-xs truncate">{msg.reply_preview}</p>
                </div>
              )}
              <p className="text-white text-sm leading-relaxed">{msg.text}</p>
              <div className="flex items-center justify-end gap-1.5 mt-3">
                <span className="text-gray-400 text-xs">22:42</span>
                <CheckCheck className="w-4 h-4 text-blue-400" />
              </div>
            </motion.div>

            {/* Reaction emojis floating up */}
            <div className="flex flex-wrap gap-2 mb-4">
              {msg.reactions.map((r, i) => (
                <motion.span
                  key={r.emoji + i}
                  initial={{ opacity: 0, y: 24, scale: 0.6 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{
                    delay: 0.55 + i * 0.1,
                    duration: 0.5,
                    type: "spring",
                    stiffness: 200,
                    damping: 16,
                  }}
                  whileHover={{ scale: 1.15, y: -2 }}
                  className="bg-[#1E293B] rounded-full px-3 py-1 flex items-center gap-1.5 text-sm cursor-default"
                >
                  <span>{r.emoji}</span>
                  <span className="text-gray-300 text-xs font-medium">{r.count}</span>
                </motion.span>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7, duration: 0.45 }}
              className="flex gap-3"
            >
              <motion.div
                whileHover={{ scale: 1.03, y: -1 }}
                className="flex-1 bg-[#1E293B] rounded-xl p-3 flex items-center gap-2 cursor-default"
              >
                <Calendar className="w-4 h-4 text-cyan-400 shrink-0" />
                <div>
                  <p className="text-gray-500 text-xs uppercase tracking-wide font-semibold">Sent on</p>
                  <p className="text-white text-xs font-medium">{msg.date}</p>
                </div>
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.03, y: -1 }}
                className="flex-1 bg-[#1E293B] rounded-xl p-3 flex items-center gap-2 cursor-default"
              >
                <span className="text-lg leading-none">{msg.reactions[0]?.emoji ?? "🎉"}</span>
                <div>
                  <p className="text-gray-500 text-xs uppercase tracking-wide font-semibold">Top Reaction</p>
                  <p className="text-white text-xs font-medium">{msg.reactions[0]?.emoji ?? "—"}</p>
                </div>
              </motion.div>
            </motion.div>
          </>
        ) : (
          <motion.div {...fadeUp(0.3)} className="flex-1 flex flex-col items-center justify-center">
            <MessageCircle className="w-16 h-16 text-gray-600 mb-4" />
            <p className="text-gray-400 text-lg font-medium">No viral moments yet</p>
            <p className="text-gray-600 text-sm mt-1">Keep chatting — your moment is coming!</p>
          </motion.div>
        )}

        <motion.p
          {...fadeUp(0.95)}
          className="text-gray-600 text-xs text-center mt-auto pt-4 tracking-wide uppercase"
        >
          Telegram Wrapped · {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </motion.div>
  );
}
