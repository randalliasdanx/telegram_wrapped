import { motion } from "framer-motion";
import { Send } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

export function VocabularySlide({ data, dateRange }: Props) {
  const topPhrase = data.top_bigrams[0];
  const otherPhrases = data.top_bigrams.slice(1, 6);
  const topWords = data.top_words.slice(0, 5);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-full bg-linear-to-b from-cyan-400 via-blue-500 to-blue-900 flex items-center justify-center px-5 overflow-y-auto"
    >
      <div className="max-w-xl w-full mx-auto flex flex-col items-center text-center py-14">
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="text-white/60 text-xs uppercase tracking-widest mb-3"
        >
          My Top Phrases
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="font-display text-4xl sm:text-5xl font-extrabold text-white mb-8 leading-tight"
        >
          Vocabulary
          <br />
          Vibe Check
        </motion.h1>

        {topPhrase && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              delay: 0.45,
              type: "spring",
              stiffness: 200,
              damping: 20,
            }}
            className="mb-2"
          >
            <span className="text-4xl sm:text-5xl font-bold text-white leading-none">
              &ldquo;{topPhrase.phrase}&rdquo;
            </span>
          </motion.div>
        )}

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="text-cyan-300 text-sm font-semibold mb-8"
        >
          {topPhrase ? `Used ${topPhrase.count.toLocaleString()} times` : ""}
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7, duration: 0.5 }}
          className="w-full flex flex-col gap-2 mb-8"
        >
          {otherPhrases.map((p, i) => (
            <motion.div
              key={p.phrase}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.75 + i * 0.08, duration: 0.4 }}
              className="flex items-center justify-between bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <span className="text-white/40 text-xs font-bold w-5">
                  #{i + 2}
                </span>
                <span className="text-white font-semibold text-base">
                  &ldquo;{p.phrase}&rdquo;
                </span>
              </div>
              <span className="text-cyan-300 text-sm font-medium">
                {p.count.toLocaleString()}x
              </span>
            </motion.div>
          ))}
        </motion.div>

        {topWords.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1, duration: 0.5 }}
            className="w-full"
          >
            <p className="text-white/40 text-xs uppercase tracking-widest font-semibold mb-3 text-left">
              Top Single Words
            </p>
            <div className="flex flex-wrap gap-2">
              {topWords.map((w, i) => (
                <motion.span
                  key={w.word}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 1.2 + i * 0.06, duration: 0.3 }}
                  className="bg-white/10 text-white/80 text-sm font-medium px-3 py-1.5 rounded-full"
                >
                  {w.word}{" "}
                  <span className="text-white/40">{w.count.toLocaleString()}</span>
                </motion.span>
              ))}
            </div>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.4 }}
          className="w-full flex items-center justify-between text-white/40 text-xs uppercase tracking-widest mt-8"
        >
          <div className="flex items-center gap-1.5">
            <Send className="w-3 h-3" />
            <span>
              {dateRange.start} – {dateRange.end}
            </span>
          </div>
          <span>Telegram Wrapped</span>
        </motion.div>
      </div>
    </motion.div>
  );
}
