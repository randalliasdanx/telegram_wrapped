import { motion } from "framer-motion";
import { X, Shield } from "lucide-react";

interface Props {
  onClose: () => void;
}

const sections = [
  {
    title: "What We Access",
    body: "When you authenticate, we temporarily connect to Telegram's API on your behalf to read the messages you sent in the last year (text, timestamps, media type, reactions), message counts per chat, and short timing samples from your top private chats. We download only small profile pictures of your top chats and thumbnails of your top stickers — never your photos, videos or documents.",
  },
  {
    title: "What We Store",
    body: "We never store your messages, contacts or media. Messages are processed in memory and discarded as soon as your Wrapped is computed. The finished Wrapped (the summary you see) is kept for up to 6 hours so you can open it again, then deleted automatically.",
  },
  {
    title: "What We Return",
    body: "Aggregated statistics — message counts, top chat names, emoji and phrase frequencies, activity patterns and similar summaries — plus the text of your single most-reacted message. Nothing else from your chats is sent to your browser.",
  },
  {
    title: "Third-Party Sharing",
    body: "We do not share any data with third parties. Your Telegram credentials are used solely to authenticate with Telegram's official API and are never logged or stored.",
  },
  {
    title: "Session Lifecycle",
    body: "Your login is held only in encrypted form and never written to disk. As soon as your Wrapped is ready we log out of Telegram, so the session disappears from your Active Sessions. If processing never completes, the login is revoked automatically within 30 minutes.",
  },
  {
    title: "Your Rights",
    body: "You can also end the session yourself at any time from Telegram → Settings → Devices. Nothing about you persists after your Wrapped expires, and you decide whether to share your generated summary.",
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
