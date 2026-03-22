import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useState } from "react";
import { MessageSquare, BarChart3 } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

function AnimatedCounter({ value }: { value: number }) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { duration: 2000, bounce: 0 });
  const display = useTransform(spring, (v) =>
    Math.round(v).toLocaleString("en-US"),
  );
  const [displayText, setDisplayText] = useState("0");

  useEffect(() => {
    motionValue.set(value);
  }, [motionValue, value]);

  useEffect(() => {
    const unsubscribe = display.on("change", (v) => setDisplayText(v));
    return unsubscribe;
  }, [display]);

  return <span>{displayText}</span>;
}

const bubblePositions = [
  { top: "7%", left: "8%", size: 22, delay: 0.1, duration: 4.2 },
  { top: "13%", right: "10%", size: 16, delay: 0.4, duration: 3.6 },
  { top: "30%", left: "4%", size: 14, delay: 0.7, duration: 5.0 },
  { top: "48%", right: "6%", size: 20, delay: 0.25, duration: 4.5 },
  { top: "65%", left: "12%", size: 13, delay: 0.9, duration: 3.8 },
  { top: "78%", right: "15%", size: 17, delay: 0.55, duration: 4.1 },
  { top: "20%", left: "22%", size: 10, delay: 1.1, duration: 5.3 },
  { top: "88%", left: "30%", size: 12, delay: 0.65, duration: 3.9 },
];

export function TotalSentSlide({ data, dateRange }: Props) {
  return (
    <div className="w-full h-full bg-[#f8fafc] relative overflow-hidden flex flex-col items-center justify-center px-5">
      {/* Ambient background blobs */}
      <motion.div
        className="absolute top-[-10%] left-[-10%] w-72 h-72 rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(2,136,209,0.08) 0%, transparent 70%)" }}
        animate={{ x: [0, 18, 0], y: [0, 12, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[-5%] right-[-5%] w-80 h-80 rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(41,182,246,0.07) 0%, transparent 70%)" }}
        animate={{ x: [0, -14, 0], y: [0, -10, 0] }}
        transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Floating message bubble particles */}
      {bubblePositions.map((pos, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{
            opacity: [0, 0.12, 0.12, 0],
            scale: [0.5, 1, 1, 0.5],
            y: [0, -18, -18, 0],
          }}
          transition={{
            delay: pos.delay,
            duration: pos.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute text-blue-400 pointer-events-none"
          style={{
            top: pos.top,
            left: "left" in pos ? pos.left : undefined,
            right: "right" in pos ? pos.right : undefined,
          }}
        >
          <MessageSquare size={pos.size} fill="currentColor" />
        </motion.div>
      ))}

      <div className="max-w-xl w-full mx-auto flex flex-col items-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span className="text-[#0288D1] uppercase tracking-widest text-xs font-semibold">
            Total Sent
          </span>
          <p className="text-gray-400 text-xs mt-1">
            {dateRange.start} – {dateRange.end}
          </p>
        </motion.div>

        {/* Pulsing ring + number */}
        <div className="relative flex items-center justify-center mt-4 mb-2">
          <motion.div
            className="absolute rounded-full border-2 border-[#29B6F6]/30 pointer-events-none"
            style={{ width: 160, height: 160 }}
            animate={{ scale: [1, 1.18, 1], opacity: [0.35, 0, 0.35] }}
            transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute rounded-full border border-[#0288D1]/15 pointer-events-none"
            style={{ width: 210, height: 210 }}
            animate={{ scale: [1, 1.12, 1], opacity: [0.2, 0, 0.2] }}
            transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.7, type: "spring", stiffness: 160, damping: 14 }}
            className="text-6xl sm:text-7xl md:text-8xl font-bold text-gray-900 font-display relative"
            style={{
              textShadow: "0 0 32px rgba(250,204,21,0.0)",
            }}
          >
            <motion.span
              animate={{
                textShadow: [
                  "0 0 0px rgba(250,204,21,0)",
                  "0 0 24px rgba(250,204,21,0.55)",
                  "0 0 8px rgba(250,204,21,0.25)",
                ],
              }}
              transition={{ delay: 2.2, duration: 0.8, ease: "easeOut" }}
            >
              <AnimatedCounter value={data.grand_total} />
            </motion.span>
          </motion.div>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="text-gray-700 text-lg md:text-xl mb-8"
        >
          messages sent. You've been busy!
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.85, duration: 0.5, type: "spring", stiffness: 120, damping: 18 }}
          whileHover={{ y: -3, boxShadow: "0 8px 32px rgba(2,136,209,0.12)" }}
          className="bg-white rounded-2xl shadow-md p-5 w-full cursor-default"
        >
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
              <BarChart3 className="w-5 h-5 text-[#0288D1]" />
            </div>
            <div>
              <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold">
                Daily Average
              </span>
              <p className="text-xl font-bold text-gray-900 mt-0.5">
                ~{data.daily_average} messages
              </p>
              <div className="flex items-center gap-1.5 mt-2">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                <span className="text-xs text-gray-500">
                  That's a lot of chatting!
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
