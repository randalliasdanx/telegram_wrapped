import { motion } from "framer-motion";
import { Users } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";
import { ChatAvatar } from "../ChatAvatar";
import { formatNumber } from "../../lib/format";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

export function TopConversationsSlide({ data, dateRange }: Props) {
  const topFive = data.top_chats.slice(0, 5);
  const maxCount = Math.max(1, ...topFive.map((c) => c.total));
  // Newer results tell us how much of each chat was *you*; older ones don't.
  const hasSplit = topFive.some((c) => c.sent_share != null && c.sent != null);

  return (
    <div className="w-full h-full bg-white overflow-y-auto overflow-x-hidden">
      <div className="min-h-full max-w-xl w-full mx-auto flex flex-col items-center justify-center px-5 py-14">
        <motion.span
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-[#0288D1] uppercase tracking-widest text-xs font-semibold mb-5"
        >
          Telegram Wrapped
        </motion.span>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.5 }}
          className="text-center mb-2"
        >
          <h2 className="font-display text-4xl font-bold text-gray-900">
            Your Top
          </h2>
          <h2 className="font-display text-4xl font-bold text-[#0288D1]">
            Conversations
          </h2>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-gray-500 text-sm mb-6"
        >
          The people you couldn't stop messaging.
        </motion.p>

        <div className="w-full flex flex-col gap-2.5">
          {topFive.map((chat, i) => {
            const isFirst = i === 0;
            const barWidth = (chat.total / maxCount) * 100;
            const youShare = Math.min(100, Math.max(0, chat.sent_share ?? 0));

            return (
              <motion.div
                key={chat.name + i}
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + i * 0.1, duration: 0.4 }}
                className={`flex items-center gap-3 p-3 rounded-xl ${
                  isFirst ? "bg-blue-50 border-l-4 border-[#0288D1]" : "bg-gray-50"
                }`}
              >
                <span className={`text-sm font-bold w-5 text-center shrink-0 ${
                  isFirst ? "text-[#0288D1]" : "text-gray-400"
                }`}>
                  {i + 1}
                </span>

                <ChatAvatar name={chat.name} avatar={chat.avatar} index={i} className="w-10 h-10 text-xs" />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className={`truncate ${
                        isFirst ? "text-sm font-bold text-gray-900" : "text-sm font-medium text-gray-800"
                      }`}>
                        {chat.name}
                      </span>
                      {chat.is_group && (
                        <span className="shrink-0 inline-flex items-center gap-0.5 text-[9px] font-bold uppercase tracking-wider text-[#0288D1] bg-[#0288D1]/10 rounded px-1.5 py-0.5">
                          <Users className="w-2.5 h-2.5" />
                          Group
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400 shrink-0">
                      {Math.round(chat.pct)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                    <motion.div
                      className="h-1.5 rounded-full flex overflow-hidden"
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ delay: 0.6 + i * 0.1, duration: 0.6, ease: "easeOut" }}
                    >
                      {hasSplit ? (
                        <>
                          <div className="h-full" style={{ width: `${youShare}%`, backgroundColor: isFirst ? "#0288D1" : "#64748b" }} />
                          <div className="h-full flex-1" style={{ backgroundColor: isFirst ? "#81D4FA" : "#cbd5e1" }} />
                        </>
                      ) : (
                        <div className="h-full w-full" style={{ backgroundColor: isFirst ? "#0288D1" : "#94a3b8" }} />
                      )}
                    </motion.div>
                  </div>
                  <span className="text-xs text-gray-400 mt-0.5 inline-block">
                    {formatNumber(chat.total)} messages
                    {chat.sent_share != null && hasSplit && (
                      <> · <span className={isFirst ? "text-[#0288D1] font-semibold" : "text-gray-500 font-medium"}>you sent {Math.round(chat.sent_share)}%</span></>
                    )}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>

        {hasSplit && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.1, duration: 0.5 }}
            className="w-full flex items-center justify-between mt-3 text-[11px] text-gray-400"
          >
            <span>% = share of everything you sent</span>
            <span className="flex items-center gap-2.5">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#0288D1]" />you</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#81D4FA]" />them</span>
            </span>
          </motion.div>
        )}

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.5 }}
          className="mt-5 text-xs uppercase tracking-widest text-gray-300 font-semibold"
        >
          {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </div>
  );
}
