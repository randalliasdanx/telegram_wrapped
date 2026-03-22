import { motion } from "framer-motion";
import { Send, MessageSquare, Users, Clock, Smile, Share2 } from "lucide-react";
import html2canvas from "html2canvas";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function formatHour(h: number): string {
  const suffix = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 || 12;
  return `${hour12} ${suffix}`;
}

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: 0.3 + i * 0.1, duration: 0.45, ease: "easeOut" },
  }),
};

export function SummarySlide({ data, dateRange }: Props) {
  const topChat = data.top_chats[0];
  const topEmoji = data.top_emojis[0];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-full flex items-center justify-center px-4 overflow-y-auto"
      style={{
        background: "linear-gradient(135deg, #29B6F6 0%, #0288D1 100%)",
      }}
    >
      <div id="share-card" className="max-w-xl w-full mx-auto flex flex-col py-14">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow">
              <Send className="w-5 h-5 text-[#0288D1]" />
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold text-white leading-tight">
              My Year On
              <br />
              Telegram
            </h1>
          </div>
          <div className="text-right">
            <p className="text-white/60 text-xs uppercase tracking-widest">
              Wrapped
            </p>
            <p className="text-white font-bold text-base">
              {dateRange.end}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-6">
          <motion.div custom={0} variants={cardVariants} initial="hidden" animate="show"
            className="bg-white/10 backdrop-blur rounded-2xl p-4 flex flex-col"
          >
            <MessageSquare className="w-5 h-5 text-white/50 mb-2" />
            <p className="text-xs text-white/50 uppercase tracking-widest mb-1">Total</p>
            <p className="text-2xl sm:text-3xl font-bold text-white leading-none mb-1">
              {data.grand_total.toLocaleString()}
            </p>
            <p className="text-xs text-white/70">Messages Sent</p>
          </motion.div>

          <motion.div custom={1} variants={cardVariants} initial="hidden" animate="show"
            className="bg-white/10 backdrop-blur rounded-2xl p-4 flex flex-col"
          >
            <Users className="w-5 h-5 text-white/50 mb-2" />
            <p className="text-xs text-white/50 uppercase tracking-widest mb-1">Top Chat</p>
            {topChat && (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold text-white">
                    {initials(topChat.name)}
                  </div>
                  <p className="text-sm font-bold text-white truncate">
                    {topChat.name}
                  </p>
                </div>
                <p className="text-xs text-white/70">
                  {topChat.total.toLocaleString()} msgs
                </p>
              </>
            )}
          </motion.div>

          <motion.div custom={2} variants={cardVariants} initial="hidden" animate="show"
            className="bg-white/10 backdrop-blur rounded-2xl p-4 flex flex-col"
          >
            <Clock className="w-5 h-5 text-white/50 mb-2" />
            <p className="text-xs text-white/50 uppercase tracking-widest mb-1">Peak</p>
            <p className="text-base font-bold text-white leading-snug mb-1">
              {data.peak_personality}
            </p>
            <p className="text-xs text-white/70">
              {formatHour(data.peak_hour)} – {formatHour((data.peak_hour + 1) % 24)}
            </p>
          </motion.div>

          <motion.div custom={3} variants={cardVariants} initial="hidden" animate="show"
            className="bg-white/10 backdrop-blur rounded-2xl p-4 flex flex-col items-start"
          >
            <Smile className="w-5 h-5 text-white/50 mb-2" />
            <p className="text-xs text-white/50 uppercase tracking-widest mb-1">Vibe</p>
            {topEmoji && (
              <>
                <span className="text-3xl mb-1">{topEmoji.emoji}</span>
                <p className="text-xs text-white/70">Top Emoji</p>
              </>
            )}
          </motion.div>
        </div>

        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.4 }}
          onClick={async () => {
            const el = document.getElementById("share-card");
            if (!el) return;
            const canvas = await html2canvas(el, { backgroundColor: null, scale: 2 });
            canvas.toBlob((blob) => {
              if (!blob) return;
              const file = new File([blob], "telegram-wrapped.png", { type: "image/png" });
              if (navigator.canShare?.({ files: [file] })) {
                navigator.share({ files: [file], title: "My Telegram Wrapped" });
              } else {
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "telegram-wrapped.png";
                a.click();
                URL.revokeObjectURL(url);
              }
            });
          }}
          className="w-full flex items-center justify-center gap-2 bg-white text-[#0288D1] font-bold py-4 rounded-full text-base shadow-lg hover:bg-white/90 transition-colors mb-4 cursor-pointer active:scale-[0.98]"
        >
          <Share2 className="w-5 h-5" />
          Share Your Wrapped
        </motion.button>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.0, duration: 0.4 }}
          className="flex items-center justify-between text-white/60 text-xs"
        >
          <span>{dateRange.start} – {dateRange.end}</span>
          <span>Telegram Wrapped</span>
        </motion.div>
      </div>
    </motion.div>
  );
}
