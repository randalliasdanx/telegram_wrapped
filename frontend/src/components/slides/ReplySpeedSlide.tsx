import { motion } from "framer-motion";
import { Zap, Rabbit, Coffee, Snail, Trophy } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";
import { formatDuration, formatNumber } from "../../lib/format";
import { ChatAvatar } from "../ChatAvatar";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

interface SpeedTier {
  label: string;
  blurb: string;
  icon: LucideIcon;
  color: string;
  bg: string;
}

function getTier(seconds: number): SpeedTier {
  if (seconds < 60)
    return { label: "Lightning", blurb: "Your phone basically never leaves your hand.", icon: Zap, color: "#F59E0B", bg: "#FEF3C7" };
  if (seconds < 600)
    return { label: "Quick on the draw", blurb: "Nobody waits long for a reply from you.", icon: Rabbit, color: "#0288D1", bg: "#E1F5FE" };
  if (seconds < 3600)
    return { label: "Takes your time", blurb: "You reply when you've got something to say.", icon: Coffee, color: "#7C3AED", bg: "#EDE9FE" };
  return { label: "Fashionably late", blurb: "Worth the wait — or so you tell everyone.", icon: Snail, color: "#E11D48", bg: "#FFE4E6" };
}

/** Map a reply time onto the gauge: 1 s → 1 (fast, right), 1 day → 0 (slow, left). Log scale. */
function gaugePosition(seconds: number): number {
  const t = Math.log10(Math.max(1, seconds)) / Math.log10(86400);
  return 1 - Math.min(1, Math.max(0, t));
}

const GAUGE_R = 100;
const GAUGE_LEN = Math.PI * GAUGE_R;

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { delay, duration: 0.5 },
});

export function ReplySpeedSlide({ data, dateRange }: Props) {
  const rs = data.reply_speed;
  if (!rs) return null;

  const tier = getTier(rs.median_seconds);
  const Icon = tier.icon;
  const pos = gaugePosition(rs.median_seconds);
  const needleDeg = -90 + 180 * pos;
  const fastestAvatar = data.top_chats.find((c) => c.name === rs.fastest_chat)?.avatar;

  return (
    <div
      className="w-full h-full relative overflow-y-auto overflow-x-hidden"
      style={{ background: "linear-gradient(180deg, #E1F5FE 0%, #F5FBFF 45%, #FFFFFF 100%)" }}
    >
      {/* Speed lines */}
      {[9, 14, 19].map((top, i) => (
        <motion.div
          key={top}
          className="absolute h-[2px] rounded-full bg-[#29B6F6]/25 pointer-events-none"
          style={{ top: `${top}%`, width: 60 + i * 20 }}
          initial={{ x: "110vw" }}
          animate={{ x: "-40vw" }}
          transition={{ duration: 2.2 + i * 0.4, repeat: Infinity, delay: i * 0.6, ease: "linear" }}
        />
      ))}

      <div className="relative min-h-full max-w-xl w-full mx-auto flex flex-col items-center justify-center px-5 py-14 text-center">
        <motion.span {...fadeUp(0)} className="text-[#0288D1] uppercase tracking-widest text-xs font-semibold">
          Reply Speed
        </motion.span>
        <motion.h2 {...fadeUp(0.1)} className="font-display text-3xl font-extrabold text-gray-900 mt-2 leading-tight">
          When someone texts you…
        </motion.h2>

        {/* Gauge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.25, type: "spring", stiffness: 150, damping: 16 }}
          className="relative mt-6"
          style={{ width: 240, height: 136 }}
        >
          <svg viewBox="0 0 240 136" width="240" height="136" className="overflow-visible">
            <defs>
              <linearGradient id="speedGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#B3E5FC" />
                <stop offset="60%" stopColor="#29B6F6" />
                <stop offset="100%" stopColor="#0288D1" />
              </linearGradient>
            </defs>
            <path d="M 20 120 A 100 100 0 0 1 220 120" fill="none" stroke="#E5E7EB" strokeWidth="14" strokeLinecap="round" />
            <motion.path
              d="M 20 120 A 100 100 0 0 1 220 120"
              fill="none"
              stroke="url(#speedGrad)"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={GAUGE_LEN}
              initial={{ strokeDashoffset: GAUGE_LEN }}
              animate={{ strokeDashoffset: GAUGE_LEN * (1 - pos) }}
              transition={{ delay: 0.5, duration: 1.3, ease: "easeOut" }}
            />
            {/* Needle */}
            <motion.line
              x1="120" y1="120" x2="120" y2="38"
              stroke="#0F172A" strokeWidth="4" strokeLinecap="round"
              initial={{ rotate: -90 }}
              animate={{ rotate: needleDeg }}
              transition={{ delay: 0.5, type: "spring", stiffness: 60, damping: 9 }}
              style={{ originX: 0.5, originY: 1 }}
            />
            <circle cx="120" cy="120" r="9" fill="#0F172A" />
            <circle cx="120" cy="120" r="3.5" fill="#fff" />
          </svg>
          <span className="absolute left-0 -bottom-1 text-[10px] uppercase tracking-widest text-gray-400 font-semibold">Slow</span>
          <span className="absolute right-0 -bottom-1 text-[10px] uppercase tracking-widest text-gray-400 font-semibold">Fast</span>
        </motion.div>

        <motion.p
          initial={{ opacity: 0, scale: 0.7 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.9, type: "spring", stiffness: 200, damping: 14 }}
          className="font-display text-6xl font-extrabold text-gray-900 mt-5 leading-none tracking-tight"
        >
          {formatDuration(rs.median_seconds)}
        </motion.p>
        <motion.p {...fadeUp(1)} className="text-gray-500 text-sm mt-2">
          is how long you usually take to reply
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 1.15, type: "spring", stiffness: 220, damping: 16 }}
          className="inline-flex items-center gap-2 rounded-full px-4 py-2 mt-4 font-bold text-sm"
          style={{ background: tier.bg, color: tier.color }}
        >
          <Icon className="w-4 h-4" />
          {tier.label}
        </motion.div>
        <motion.p {...fadeUp(1.25)} className="text-gray-500 text-sm mt-2 max-w-xs">
          {tier.blurb}
        </motion.p>

        {rs.fastest_chat && rs.fastest_seconds != null && (
          <motion.div
            {...fadeUp(1.4)}
            className="w-full bg-white rounded-2xl shadow-sm border border-gray-100 p-3.5 mt-6 flex items-center gap-3 text-left"
          >
            <ChatAvatar name={rs.fastest_chat} avatar={fastestAvatar} className="w-11 h-11 text-sm" />
            <div className="flex-1 min-w-0">
              <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold">
                Fastest replies go to
              </span>
              <p className="text-sm font-bold text-gray-900 truncate">{rs.fastest_chat}</p>
            </div>
            <div className="text-right shrink-0">
              <span className="flex items-center gap-1 justify-end text-[#0288D1] font-display font-extrabold text-lg leading-none">
                <Trophy className="w-4 h-4" />
                {formatDuration(rs.fastest_seconds)}
              </span>
              <span className="text-[10px] text-gray-400">typical reply</span>
            </div>
          </motion.div>
        )}

        <motion.p {...fadeUp(1.6)} className="mt-5 text-[11px] text-gray-400">
          Based on {formatNumber(rs.samples)} replies in 1:1 chats · {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </div>
  );
}
