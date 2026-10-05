import { useMotionValue, useSpring, useMotionValueEvent } from "framer-motion";
import { useEffect, useState } from "react";

interface Props {
  value: number;
  /** Spring duration in ms. */
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}

const defaultFormat = (n: number) => Math.round(n).toLocaleString("en-US");

/** Counts smoothly from its previous value to `value` (starts from 0 on mount). */
export function AnimatedNumber({ value, duration = 2000, format = defaultFormat, className }: Props) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { duration, bounce: 0 });
  const [text, setText] = useState(() => format(0));

  useEffect(() => {
    motionValue.set(value);
  }, [motionValue, value]);

  useMotionValueEvent(spring, "change", (v) => setText(format(v)));

  return <span className={className}>{text}</span>;
}
