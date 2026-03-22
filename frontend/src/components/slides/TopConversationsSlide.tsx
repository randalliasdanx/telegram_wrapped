import { motion } from "framer-motion";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

const AVATAR_COLORS = ["#0288D1", "#7C3AED", "#059669", "#E11D48", "#0F172A"];

function getInitials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export function TopConversationsSlide({ data, dateRange }: Props) {
  const topFive = data.top_chats.slice(0, 5);
  const maxCount = topFive[0]?.total ?? 1;

  return (
    <div className="w-full h-full bg-white flex flex-col items-center justify-center px-5">
      <div className="max-w-xl w-full mx-auto flex flex-col items-center">
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

                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                  style={{ backgroundColor: AVATAR_COLORS[i % AVATAR_COLORS.length] }}
                >
                  {getInitials(chat.name)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between mb-1">
                    <span className={`truncate ${
                      isFirst ? "text-sm font-bold text-gray-900" : "text-sm font-medium text-gray-800"
                    }`}>
                      {chat.name}
                    </span>
                    <span className="text-xs text-gray-400 ml-2 shrink-0">
                      {chat.pct}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <motion.div
                      className="h-1.5 rounded-full"
                      style={{ backgroundColor: isFirst ? "#0288D1" : "#94a3b8" }}
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ delay: 0.6 + i * 0.1, duration: 0.6, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 mt-0.5 inline-block">
                    {chat.total.toLocaleString()} messages
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.5 }}
          className="mt-6 text-xs uppercase tracking-widest text-gray-300 font-semibold"
        >
          {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </div>
  );
}
