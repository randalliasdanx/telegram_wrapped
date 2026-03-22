import { motion } from "framer-motion";
import { X, Shield } from "lucide-react";

interface Props {
  onClose: () => void;
}

const sections = [
  {
    title: "What We Access",
    body: "When you authenticate, we temporarily connect to Telegram's API on your behalf to read message metadata (counts, timestamps, sender IDs) and a statistical sample of message text. We never access your media files, photos, or documents.",
  },
  {
    title: "What We Store",
    body: "Nothing. We do not store your messages, contacts, media, or any personal data on our servers. All processing happens entirely in memory and is discarded within minutes of completion.",
  },
  {
    title: "What We Return",
    body: "Only aggregated, anonymous statistics: total message counts, top chat names, emoji frequencies, hourly activity patterns, and similar summaries. No raw message content is ever sent to your browser or stored anywhere.",
  },
  {
    title: "Third-Party Sharing",
    body: "We do not share any data with third parties. Your Telegram credentials are used solely to authenticate with Telegram's official API and are never logged or stored.",
  },
  {
    title: "Session Lifecycle",
    body: "Your authenticated session is automatically destroyed within 15 minutes. Temporary session files are deleted immediately after processing completes or if an error occurs.",
  },
  {
    title: "Your Rights",
    body: "You can close the browser tab at any time to terminate processing. No data persists after your session ends. You have full control over when and whether to share your generated Wrapped summary.",
  },
  {
    title: "Open Source",
    body: "This project is open source. You are welcome to audit the code to verify these claims and understand exactly how your data is processed.",
  },
  {
    title: "Contact",
    body: "For privacy inquiries, please reach out to privacy@telegramwrapped.app.",
  },
];

export function PrivacyPolicy({ onClose }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        className="w-full max-w-lg bg-white rounded-t-3xl sm:rounded-3xl max-h-[85vh] overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-[#0288D1]" />
            <h2 className="font-display text-lg font-bold text-gray-900">
              Privacy Policy
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
          >
            <X className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 space-y-6">
          <p className="text-gray-600 text-sm leading-relaxed">
            Telegram Wrapped is designed with your privacy as the top priority.
            We follow a zero-storage architecture — your data is processed
            entirely in memory and never saved.
          </p>

          {sections.map((s, i) => (
            <div key={i}>
              <h3 className="font-semibold text-gray-900 text-sm mb-1.5">
                {i + 1}. {s.title}
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed">{s.body}</p>
            </div>
          ))}

          <p className="text-gray-400 text-xs pt-4 border-t border-gray-100">
            Last updated: March 2026
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}
