import { motion } from "framer-motion";
import { Sticker } from "lucide-react";
import type { WrappedData, DateRange, StickerStat } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

function StickerImage({ sticker, size }: { sticker: StickerStat; size: string }) {
  if (sticker.image) {
    return (
      <img
        src={sticker.image}
        alt={sticker.emoji}
        className={`${size} object-contain drop-shadow-lg`}
        draggable={false}
      />
    );
  }
  return <span className={size}>{sticker.emoji}</span>;
}

// Floating geometric shapes for the colored gradient background
const SHAPES = [
  { top: "8%", left: "8%", size: 18, delay: 0.3, duration: 5.5, rotate: 0 },
  { top: "16%", right: "10%", size: 14, delay: 0.9, duration: 6.2, rotate: 45 },
  { top: "42%", left: "4%", size: 10, delay: 0.5, duration: 5.0, rotate: 30 },
  { top: "58%", right: "6%", size: 16, delay: 1.1, duration: 6.8, rotate: 15 },
  { top: "75%", left: "18%", size: 12, delay: 0.7, duration: 5.8, rotate: 60 },
  { top: "82%", right: "20%", size: 10, delay: 0.4, duration: 5.3, rotate: 45 },
  { top: "30%", right: "28%", size: 8, delay: 1.3, duration: 6.0, rotate: 20 },
];

const cardVariants = {
  hidden: { opacity: 0, y: 28, scale: 0.85 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: 0.45 + i * 0.1,
      duration: 0.6,
      type: "spring" as const,
      stiffness: 190,
      damping: 18,
    },
  }),
};

export function TopStickersSlide({ data, dateRange }: Props) {
  const stickers = data.top_stickers?.slice(0, 8) ?? [];
  const top = stickers[0];
  const rest = stickers.slice(1, 5);
  const hasStickers = stickers.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-full flex items-center justify-center px-5 overflow-y-auto relative"
      style={{
        background:
          "linear-gradient(135deg, #f97316 0%, #ef4444 50%, #ec4899 100%)",
      }}
    >
      {/* Floating geometric shapes */}
      {SHAPES.map((s, i) => (
        <motion.div
          key={i}
          className="absolute pointer-events-none border border-white/20 rounded-sm"
          style={{
            width: s.size,
            height: s.size,
            top: s.top,
            left: "left" in s ? s.left : undefined,
            right: "right" in s ? s.right : undefined,
            rotate: s.rotate,
          }}
          animate={{
            opacity: [0, 0.45, 0.45, 0],
            y: [0, -20, -20, 0],
            rotate: [s.rotate, s.rotate + 25, s.rotate],
          }}
          transition={{ delay: s.delay, duration: s.duration, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}

      <div className="max-w-xl w-full mx-auto py-14">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="flex items-center gap-2 mb-5"
        >
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
            <Sticker className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-medium text-white/70 tracking-wide">
            Telegram Wrapped
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="font-display text-4xl font-bold leading-tight mb-3 text-white"
        >
          Your Top Stickers
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.5 }}
          className="text-white/70 text-sm leading-relaxed mb-6"
        >
          {hasStickers
            ? "The stickers you couldn't stop sending."
            : "You didn't send many stickers this period — maybe next year!"}
        </motion.p>

        {hasStickers && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="mb-4"
            >
              <p className="text-xs text-white/50 uppercase tracking-widest mt-1">
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
                  whileHover={{
                    scale: 1.04,
                    rotate: 1.5,
                    y: -4,
                    boxShadow: "0 16px 40px rgba(0,0,0,0.25)",
                    transition: { type: "spring", stiffness: 300, damping: 20 },
                  }}
                  className="col-span-1 row-span-2 bg-white/15 backdrop-blur-sm rounded-2xl p-5 flex flex-col items-center justify-center text-center cursor-default relative overflow-hidden"
                >
                  {/* Shimmer on hero card */}
                  <motion.div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      background: "linear-gradient(110deg, transparent 35%, rgba(255,255,255,0.07) 50%, transparent 65%)",
                    }}
                    animate={{ x: ["-100%", "200%"] }}
                    transition={{ delay: 1.2, duration: 2.0, repeat: Infinity, repeatDelay: 4.0, ease: "easeInOut" }}
                  />
                  <span className="inline-block bg-white/20 text-white text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full mb-3">
                    #1 Most Sent
                  </span>
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.6, type: "spring", stiffness: 220, damping: 16 }}
                  >
                    <StickerImage sticker={top} size="w-24 h-24" />
                  </motion.div>
                  <p className="text-2xl font-bold text-white mt-2">
                    {top.count.toLocaleString()}
                  </p>
                  <p className="text-xs text-white/50 uppercase tracking-widest mt-1">
                    times sent
                  </p>
                </motion.div>
              )}

              {rest.map((s, i) => (
                <motion.div
                  key={s.emoji + i}
                  custom={i + 1}
                  variants={cardVariants}
                  initial="hidden"
                  animate="show"
                  whileHover={{
                    scale: 1.06,
                    rotate: i % 2 === 0 ? 2 : -2,
                    y: -3,
                    boxShadow: "0 12px 32px rgba(0,0,0,0.2)",
                    transition: { type: "spring", stiffness: 300, damping: 20 },
                  }}
                  className="bg-white/10 backdrop-blur-sm rounded-2xl p-3 flex flex-col items-center justify-center text-center cursor-default"
                >
                  <span className="text-xs font-semibold text-white/40 mb-1">
                    #{i + 2}
                  </span>
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0, rotate: -10 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    transition={{
                      delay: 0.55 + i * 0.12,
                      type: "spring",
                      stiffness: 240,
                      damping: 16,
                    }}
                  >
                    <StickerImage sticker={s} size="w-14 h-14" />
                  </motion.div>
                  <p className="text-sm font-bold text-white mt-1">
                    {s.count.toLocaleString()}
                  </p>
                </motion.div>
              ))}
            </div>
          </>
        )}

        {!hasStickers && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <Sticker className="w-20 h-20 text-white/30 mb-4" />
            <p className="text-white/50 text-lg font-medium">
              No sticker data yet
            </p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
