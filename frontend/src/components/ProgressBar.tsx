import { motion } from "framer-motion";

interface Props {
  total: number;
  current: number;
}

export function ProgressBar({ total, current }: Props) {
  return (
    <div className="flex gap-1 px-4 py-3">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className="h-[3px] flex-1 rounded-full bg-white/25 overflow-hidden"
        >
          {i <= current && (
            <motion.div
              className="h-full rounded-full bg-white"
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
