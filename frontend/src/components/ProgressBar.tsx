import { motion } from "framer-motion";

interface Props {
  total: number;
  current: number;
  /** "light" slides get blue segments; "dark"/colourful slides get white ones. */
  tone?: "light" | "dark";
  className?: string;
}

export function ProgressBar({ total, current, tone = "dark", className = "" }: Props) {
  const track = tone === "light" ? "bg-[#0288D1]/15" : "bg-white/25";
  const fill = tone === "light" ? "bg-[#0288D1]" : "bg-white";
  return (
    <div className={`flex gap-1 px-4 py-3 ${className}`}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-[3px] flex-1 rounded-full overflow-hidden transition-colors duration-300 ${track}`}
        >
          {i <= current && (
            <motion.div
              className={`h-full rounded-full transition-colors duration-300 ${fill}`}
              initial={{ width: i < current ? "100%" : "0%" }}
              animate={{ width: i <= current ? "100%" : "0%" }}
              transition={
                i === current
                  ? { duration: 6, ease: "linear" }
                  : { duration: 0 }
              }
            />
          )}
        </div>
      ))}
    </div>
  );
}
