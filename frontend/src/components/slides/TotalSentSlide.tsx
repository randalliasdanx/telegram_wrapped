import { motion } from "framer-motion";
import { MessageSquare, BarChart3, CalendarCheck, Users, ShieldCheck, Sigma } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";
import { AnimatedNumber } from "../AnimatedNumber";
import { formatNumber } from "../../lib/format";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

function AccuracyBadge({ accuracy }: { accuracy: NonNullable<WrappedData["accuracy"]> }) {
  const exact = accuracy.mode === "exact";
  const Icon = exact ? ShieldCheck : Sigma;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: 1.7, type: "spring", stiffness: 240, damping: 18 }}
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold mb-6 border ${
        exact
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : "bg-sky-50 text-[#0288D1] border-sky-200"
      }`}
    >
      <Icon className="w-3.5 h-3.5" />
      {exact
        ? "Exact count · every message analysed"
        : `Estimated from ${Math.round(accuracy.coverage_pct)}% of messages`}
    </motion.div>
  );
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
  const activeDays = data.active_days ?? 0;
  const stats = [
    { label: "Per day", value: `~${formatNumber(data.daily_average)}`, icon: BarChart3 },
    ...(activeDays > 0 ? [{ label: "Active days", value: formatNumber(activeDays), icon: CalendarCheck }] : []),
    ...(data.total_chats ? [{ label: "Chats", value: formatNumber(data.total_chats), icon: Users }] : []),
  ];

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
              <AnimatedNumber value={data.grand_total} />
            </motion.span>
          </motion.div>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className={`text-gray-700 text-lg md:text-xl ${data.accuracy ? "mb-3" : "mb-8"}`}
        >
          messages sent. You've been busy!
        </motion.p>

        {data.accuracy && <AccuracyBadge accuracy={data.accuracy} />}

        {stats.length === 1 ? (
          // Older results: just the daily average, as a wide card.
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.85, duration: 0.5, type: "spring", stiffness: 120, damping: 18 }}
            className="bg-white rounded-2xl shadow-md p-5 w-full flex items-start gap-4"
          >
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
              <BarChart3 className="w-5 h-5 text-[#0288D1]" />
            </div>
            <div>
              <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold">Daily Average</span>
              <p className="text-xl font-bold text-gray-900 mt-0.5">~{formatNumber(data.daily_average)} messages</p>
              <div className="flex items-center gap-1.5 mt-2">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                <span className="text-xs text-gray-500">That's a lot of chatting!</span>
              </div>
            </div>
          </motion.div>
        ) : (
          <div className={`grid gap-3 w-full ${stats.length >= 3 ? "grid-cols-3" : "grid-cols-2"}`}>
            {stats.map((stat, i) => {
              const Icon = stat.icon;
              return (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.85 + i * 0.1, duration: 0.5, type: "spring", stiffness: 120, damping: 18 }}
                  whileHover={{ y: -3, boxShadow: "0 8px 32px rgba(2,136,209,0.12)" }}
                  className="bg-white rounded-2xl shadow-md p-3.5 cursor-default flex flex-col items-center text-center"
                >
                  <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center mb-2">
                    <Icon className="w-[18px] h-[18px] text-[#0288D1]" />
                  </div>
                  <p className="text-xl font-bold text-gray-900 font-display leading-none">{stat.value}</p>
                  <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold mt-1.5 leading-tight">
                    {stat.label}
                  </span>
                </motion.div>
              );
            })}
          </div>
        )}

        {activeDays > 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.3, duration: 0.5 }}
            className="text-xs text-gray-500 mt-4 flex items-center gap-1.5"
          >
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            {activeDays >= 300
              ? "You barely took a day off."
              : activeDays >= 180
                ? "Most days, you had something to say."
                : "You pick your moments."}
          </motion.p>
        )}
      </div>
    </div>
  );
}
