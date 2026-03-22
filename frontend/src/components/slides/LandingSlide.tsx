import { motion } from "framer-motion";
import { Send } from "lucide-react";

interface Props {
  onStart?: () => void;
}

export function LandingSlide({ onStart }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="min-h-screen flex flex-col items-center justify-center px-6 text-center"
      style={{
        background: "linear-gradient(135deg, #29B6F6 0%, #0288D1 100%)",
      }}
    >
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.2 }}
        className="w-24 h-24 rounded-full bg-white flex items-center justify-center mb-8 shadow-lg"
      >
        <Send className="w-10 h-10 text-[#0288D1]" />
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
        className="font-display text-4xl md:text-5xl font-bold text-white mb-4"
      >
        Your 2024 Telegram Wrapped
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        className="text-white/70 text-base md:text-lg max-w-md mb-10 leading-relaxed"
      >
        Discover the stories behind your chats, the stickers you loved, and the
        channels that kept you informed.
      </motion.p>

      <motion.button
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8, duration: 0.5 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onStart}
        className="bg-white text-[#0288D1] font-semibold text-lg px-10 py-3 rounded-full shadow-lg hover:shadow-xl transition-shadow cursor-pointer"
      >
        Start →
      </motion.button>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.5 }}
        className="absolute bottom-8 flex gap-6"
      >
        <a href="#" className="text-white/50 text-sm hover:text-white/80 transition-colors">
          Privacy Policy
        </a>
        <a href="#" className="text-white/50 text-sm hover:text-white/80 transition-colors">
          About
        </a>
      </motion.div>
    </motion.div>
  );
}
