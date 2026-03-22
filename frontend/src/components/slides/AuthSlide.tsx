import { motion, AnimatePresence } from "framer-motion";
import { Send, ArrowLeft, Loader2, Shield } from "lucide-react";
import { useState, useRef, useEffect, useCallback } from "react";

interface Props {
  onAuthenticated: (sessionId: string, phone: string) => void;
  onPrivacyOpen: () => void;
}

export function AuthSlide({ onAuthenticated, onPrivacyOpen }: Props) {
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState(["", "", "", "", ""]);
  const [sessionId, setSessionId] = useState("");
  const [phoneCodeHash, setPhoneCodeHash] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const codeRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleSendCode = async () => {
    setError(null);
    setLoading(true);
    try {
      let cleaned = phone.replace(/\s+/g, "").replace(/-/g, "");
      if (/^\d{8}$/.test(cleaned)) cleaned = "+65" + cleaned;
      else if (/^65\d{8}$/.test(cleaned)) cleaned = "+" + cleaned;
      else if (!cleaned.startsWith("+")) cleaned = "+" + cleaned;
      const res = await fetch("/api/auth/send-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: cleaned }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send code");
      setSessionId(data.session_id);
      setPhoneCodeHash(data.phone_code_hash);
      setStep("code");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = useCallback(
    async (fullCode: string) => {
      setError(null);
      setLoading(true);
      try {
        let cleaned = phone.replace(/\s+/g, "").replace(/-/g, "");
        if (/^\d{8}$/.test(cleaned)) cleaned = "+65" + cleaned;
        else if (/^65\d{8}$/.test(cleaned)) cleaned = "+" + cleaned;
        else if (!cleaned.startsWith("+")) cleaned = "+" + cleaned;
        const res = await fetch("/api/auth/verify-code", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            phone: cleaned,
            code: fullCode,
            phone_code_hash: phoneCodeHash,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Verification failed");
        let cleanedPhone = phone.replace(/\s+/g, "").replace(/-/g, "");
        if (/^\d{8}$/.test(cleanedPhone)) cleanedPhone = "+65" + cleanedPhone;
        else if (/^65\d{8}$/.test(cleanedPhone)) cleanedPhone = "+" + cleanedPhone;
        else if (!cleanedPhone.startsWith("+")) cleanedPhone = "+" + cleanedPhone;
        onAuthenticated(sessionId, cleanedPhone);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong");
        setCode(["", "", "", "", ""]);
        codeRefs.current[0]?.focus();
      } finally {
        setLoading(false);
      }
    },
    [phone, sessionId, phoneCodeHash, onAuthenticated],
  );

  const handleCodeChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const digit = value.slice(-1);
    const next = [...code];
    next[index] = digit;
    setCode(next);

    if (digit && index < 4) {
      codeRefs.current[index + 1]?.focus();
    }

    if (digit && index === 4) {
      const fullCode = next.join("");
      if (fullCode.length === 5) {
        handleVerifyCode(fullCode);
      }
    }
  };

  const handleCodeKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      codeRefs.current[index - 1]?.focus();
    }
  };

  const handleCodePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 5);
    if (!pasted) return;
    const next = [...code];
    for (let i = 0; i < pasted.length && i < 5; i++) {
      next[i] = pasted[i];
    }
    setCode(next);
    if (pasted.length === 5) {
      handleVerifyCode(pasted);
    } else {
      codeRefs.current[Math.min(pasted.length, 4)]?.focus();
    }
  };

  useEffect(() => {
    if (step === "code") {
      codeRefs.current[0]?.focus();
    }
  }, [step]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="relative h-full w-full flex flex-col items-center justify-center px-6 text-center select-none"
      style={{
        background: "linear-gradient(135deg, #29B6F6 0%, #0288D1 100%)",
      }}
    >
      <AnimatePresence mode="wait">
        {step === "phone" ? (
          <motion.div
            key="phone"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-md flex flex-col items-center"
          >
            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.2 }}
              className="w-20 h-20 rounded-full bg-white flex items-center justify-center mb-6 shadow-lg"
            >
              <Send className="w-8 h-8 text-[#0288D1]" />
            </motion.div>

            <h1 className="font-display text-3xl md:text-4xl font-bold text-white mb-2">
              Your 2026
            </h1>
            <h1 className="font-display text-3xl md:text-4xl font-bold text-white mb-3">
              Telegram Wrapped
            </h1>
            <p className="text-white/70 text-sm md:text-base mb-8 max-w-xs leading-relaxed">
              Enter your phone number to discover the stories behind your chats.
            </p>

            <div className="w-full mb-4">
              <input
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendCode()}
                placeholder="e.g. 91234567 or +6591234567"
                className="w-full h-14 bg-white/15 backdrop-blur-sm text-white text-lg text-center font-medium rounded-2xl border-2 border-white/30 placeholder:text-white/40 outline-none focus:border-white/60 transition-colors"
              />
            </div>

            <button
              onClick={handleSendCode}
              disabled={loading || phone.replace(/[\s\-+]/g, "").length < 8}
              className="w-full h-14 bg-white text-[#0288D1] font-bold text-lg rounded-2xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer active:scale-[0.98]"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                "Get Started"
              )}
            </button>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 text-red-200 text-sm bg-red-500/20 backdrop-blur-sm px-4 py-2 rounded-xl"
              >
                {error}
              </motion.p>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="code"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-md flex flex-col items-center"
          >
            <button
              onClick={() => { setStep("phone"); setError(null); }}
              className="self-start mb-6 md:mb-0 md:absolute md:top-8 md:left-8 text-white/70 hover:text-white flex items-center gap-2 transition-colors"
            >
              <ArrowLeft className="w-4 h-4 md:w-6 md:h-6" />
              <span className="text-sm md:text-base md:font-medium">Back</span>
            </button>

            <div className="w-16 h-16 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center mb-6">
              <Send className="w-7 h-7 text-white" />
            </div>

            <h2 className="font-display text-2xl font-bold text-white mb-2">
              Enter Verification Code
            </h2>
            <p className="text-white/70 text-sm mb-8">
              We sent a code to your Telegram app
            </p>

            <div className="flex gap-3 mb-6" onPaste={handleCodePaste}>
              {code.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => { codeRefs.current[i] = el; }}
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleCodeChange(i, e.target.value)}
                  onKeyDown={(e) => handleCodeKeyDown(i, e)}
                  className="w-12 h-14 md:w-14 md:h-16 bg-white/15 backdrop-blur-sm text-white text-2xl font-bold text-center rounded-xl border-2 border-white/30 outline-none focus:border-white/60 transition-colors"
                />
              ))}
            </div>

            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 text-white/80 mb-4"
              >
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Verifying...</span>
              </motion.div>
            )}

            {error && (
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-2 text-red-200 text-sm bg-red-500/20 backdrop-blur-sm px-4 py-2 rounded-xl"
              >
                {error}
              </motion.p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.5 }}
        className="absolute bottom-8 flex items-center gap-4"
      >
        <button
          onClick={onPrivacyOpen}
          className="text-white/50 text-xs hover:text-white/80 transition-colors flex items-center gap-1"
        >
          <Shield className="w-3 h-3" />
          Privacy Policy
        </button>
        <span className="text-white/30 text-xs">|</span>
        <span className="text-white/50 text-xs">
          Your data is never stored
        </span>
      </motion.div>
    </motion.div>
  );
}
