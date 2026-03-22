import { useState, useEffect, useCallback } from "react";

interface Options {
  totalSlides: number;
  autoAdvanceMs?: number;
}

export function useSlideNavigation({ totalSlides, autoAdvanceMs = 6000 }: Options) {
  const [current, setCurrent] = useState(0);
  const [paused, setPaused] = useState(false);
  const [direction, setDirection] = useState(0);

  const goNext = useCallback(() => {
    setCurrent((prev) => {
      if (prev < totalSlides - 1) {
        setDirection(1);
        return prev + 1;
      }
      return prev;
    });
  }, [totalSlides]);

  const goPrev = useCallback(() => {
    setCurrent((prev) => {
      if (prev > 0) {
        setDirection(-1);
        return prev - 1;
      }
      return prev;
    });
  }, []);

  const togglePause = useCallback(() => setPaused((p) => !p), []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") goNext();
      else if (e.key === "ArrowLeft") goPrev();
      else if (e.key === " ") {
        e.preventDefault();
        togglePause();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [goNext, goPrev, togglePause]);

  useEffect(() => {
    if (paused || !autoAdvanceMs) return;
    const timer = setInterval(goNext, autoAdvanceMs);
    return () => clearInterval(timer);
  }, [paused, autoAdvanceMs, goNext]);

  return { current, direction, paused, goNext, goPrev, togglePause, setCurrent, setDirection };
}
