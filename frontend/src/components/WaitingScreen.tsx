import { motion } from "framer-motion";
import { useState, useMemo } from "react";
import { ARCHETYPES } from "../data/archetypes";

interface Props {
  phone: string;
  sessionId: string;
}

const BOT_USERNAME = import.meta.env.VITE_BOT_USERNAME ?? "TelegramWrappedBot";

function maskPhone(phone: string): string {
  const cleaned = phone.replace(/\s/g, "");
  if (cleaned.length <= 5) return cleaned;
  const prefix = cleaned.slice(0, 4);   // e.g. "+659"
  const suffix = cleaned.slice(-2);     // last 2 digits
  const dots = "•".repeat(Math.max(0, cleaned.length - 6));
  return `${prefix}${dots}${suffix}`;
}

// Telegram send arrow as an SVG path (the chevron ">" shape)
function TelegramArrow({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 56 48" fill="none" className={className}>
      <path
        d="M4 24L52 4L36 24L52 44L4 24Z"
        fill="#2AABEE"
      />
    </svg>
  );
}

export function WaitingScreen({ phone, sessionId }: Props) {
  const botDeepLink = `https://t.me/${BOT_USERNAME}?start=${sessionId}`;

  // Pick spotlight archetype (random on mount)
  const spotlight = useMemo(
    () => ARCHETYPES[Math.floor(Math.random() * ARCHETYPES.length)],
    [],
  );

  // Self-prediction pills — pick 4 random archetypes for the right card
  const predictionOptions = useMemo(() => {
    const shuffled = [...ARCHETYPES].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 4);
  }, []);

  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div
      className="h-full w-full overflow-y-auto"
      style={{ background: "linear-gradient(160deg, #d6edf8 0%, #eaf5fb 35%, #f7fcfe 60%, #ffffff 100%)" }}
    >
      {/* Main content area */}
      <div className="flex flex-col items-center px-5 pt-12 pb-0 max-w-3xl mx-auto">

        {/* Send arrow icon */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-7"
        >
          <TelegramArrow className="w-14 h-12" />
        </motion.div>

        {/* Phone number pill */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="flex items-center gap-2 bg-white/70 border border-gray-200 rounded-full px-4 py-1.5 mb-6 shadow-sm"
        >
          <span className="w-2 h-2 rounded-full bg-[#2AABEE] shrink-0" />
          <span className="text-gray-700 text-sm font-mono tracking-wider">{maskPhone(phone)}</span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="text-gray-900 font-black text-5xl md:text-6xl text-center leading-[1.05] mb-5 max-w-lg"
        >
          Your Wrapped is being cooked 🍳
        </motion.h1>

        {/* Subtext */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
          className="text-gray-500 text-base text-center max-w-sm mb-8 leading-relaxed"
        >
          We're digging through your messages to build your story. A Telegram bot will ping you directly when it's ready, so you can close this tab and relax.
        </motion.p>

        {/* CTA button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.45, type: "spring", stiffness: 200, damping: 18 }}
          className="flex flex-col items-center gap-2.5 mb-10"
        >
          <a
            href={botDeepLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5 bg-[#2AABEE] hover:bg-[#229ED9] text-white font-semibold text-base px-8 py-3.5 rounded-full shadow-md active:scale-95 transition-all"
          >
            <TelegramArrow className="w-4 h-3.5" />
            Start the bot now
          </a>
          <p className="text-gray-400 text-[11px] uppercase tracking-widest font-medium">
            Usually ready in 5–15 minutes
          </p>
        </motion.div>

        {/* Engagement cards — 2 columns */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="w-full grid grid-cols-1 md:grid-cols-2 gap-0 rounded-2xl overflow-hidden border border-gray-200 shadow-sm bg-white mb-0"
        >
          {/* Left card — Archetype spotlight */}
          <div className="p-6 border-b md:border-b-0 md:border-r border-gray-200">
            <div className="flex items-start justify-between mb-3">
              <span className="text-xs font-bold tracking-widest text-[#2AABEE] bg-[#2AABEE]/10 px-2.5 py-1 rounded-md uppercase">
                {spotlight.name.replace("The ", "The ").toUpperCase()}
              </span>
              <span className="text-2xl opacity-50">👁️‍🗨️</span>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed mb-4">
              {spotlight.description}
            </p>
            <button
              className="text-[#2AABEE] text-xs font-semibold uppercase tracking-widest hover:underline flex items-center gap-1"
              onClick={() => {/* preview archetypes */}}
            >
              Preview archetypes →
            </button>
          </div>

          {/* Right card — self-prediction */}
          <div className="p-6 border border-dashed border-gray-200 md:border-0">
            <p className="text-gray-900 font-bold text-sm uppercase tracking-widest mb-4">
              Which archetype are you?
            </p>
            <div className="flex flex-wrap gap-2">
              {predictionOptions.map((arch) => (
                <button
                  key={arch.code}
                  onClick={() => setSelected(selected === arch.code ? null : arch.code)}
                  className={`text-xs font-semibold px-3.5 py-1.5 rounded-full border transition-all ${
                    selected === arch.code
                      ? "bg-[#2AABEE] border-[#2AABEE] text-white"
                      : "bg-white border-gray-300 text-gray-700 hover:border-[#2AABEE] hover:text-[#2AABEE]"
                  }`}
                >
                  {arch.name.toUpperCase()}
                </button>
              ))}
            </div>
            {selected && (
              <motion.p
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-gray-400 mt-3 italic"
              >
                We'll see if your Wrapped agrees ✨
              </motion.p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <div className="mt-auto bg-gray-900 text-white/60 py-4 px-6 flex items-center justify-between text-[11px] uppercase tracking-widest font-medium mt-12">
        <span>
          <span className="text-white font-bold">Telegram Wrapped</span>
          &nbsp;2024
        </span>
        <div className="hidden md:flex items-center gap-4">
          <a href="#" className="hover:text-white transition-colors">Twitter</a>
          <span>·</span>
          <a href="#" className="hover:text-white transition-colors">Telegram</a>
          <span>·</span>
          <a href="#" className="hover:text-white transition-colors">Support</a>
        </div>
        <span>© 2024 Telegram Wrapped</span>
      </div>
    </div>
  );
}
