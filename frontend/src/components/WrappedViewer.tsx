import { AnimatePresence, motion } from "framer-motion";
import { useState, useRef, useMemo } from "react";
import type { ReactNode } from "react";
import { Download, X, Image, Images, FileImage } from "lucide-react";
import type { WrappedData } from "../api/types";
import { useSlideNavigation } from "../hooks/useSlideNavigation";
import { ProgressBar } from "./ProgressBar";
import { TotalSentSlide } from "./slides/TotalSentSlide";
import { PeakActivitySlide } from "./slides/PeakActivitySlide";
import { TexterTypeSlide } from "./slides/TexterTypeSlide";
import { TopConversationsSlide } from "./slides/TopConversationsSlide";
import { ConversationStarterSlide } from "./slides/ConversationStarterSlide";
import { StreakSlide } from "./slides/StreakSlide";
import { MostReactedSlide } from "./slides/MostReactedSlide";
import { EmojiPersonalitySlide } from "./slides/EmojiPersonalitySlide";
import { TopStickersSlide } from "./slides/TopStickersSlide";
import { VocabularySlide } from "./slides/VocabularySlide";
import { VibeAgeSlide } from "./slides/VibeAgeSlide";
import { SummarySlide } from "./slides/SummarySlide";
import { RhythmSlide } from "./slides/RhythmSlide";
import { ReplySpeedSlide } from "./slides/ReplySpeedSlide";
import { MediaMixSlide } from "./slides/MediaMixSlide";
import { hasMediaMix, hasReplySpeed, hasRhythm } from "../lib/slideData";

interface SlideDef {
  /** Used for download filenames. */
  name: string;
  /** Background brightness — decides the colour of the overlaid chrome. */
  tone: "light" | "dark";
  element: ReactNode;
}

/** The deck, in order. Slides whose data is missing (older results) are skipped. */
function buildSlides(data: WrappedData): SlideDef[] {
  const p = { data, dateRange: data.date_range };
  const all: (SlideDef | false)[] = [
    { name: "total-sent", tone: "light", element: <TotalSentSlide {...p} /> },
    hasRhythm(data) && { name: "year-in-rhythm", tone: "light", element: <RhythmSlide {...p} /> },
    { name: "peak-activity", tone: "light", element: <PeakActivitySlide {...p} /> },
    hasReplySpeed(data) && { name: "reply-speed", tone: "light", element: <ReplySpeedSlide {...p} /> },
    { name: "texter-type", tone: "dark", element: <TexterTypeSlide {...p} /> },
    { name: "vibe-age", tone: "dark", element: <VibeAgeSlide {...p} /> },
    { name: "top-conversations", tone: "light", element: <TopConversationsSlide {...p} /> },
    { name: "conversation-starter", tone: "dark", element: <ConversationStarterSlide {...p} /> },
    { name: "streak", tone: "dark", element: <StreakSlide {...p} /> },
    { name: "most-reacted", tone: "dark", element: <MostReactedSlide {...p} /> },
    hasMediaMix(data) && { name: "media-mix", tone: "light", element: <MediaMixSlide {...p} /> },
    { name: "emoji-personality", tone: "light", element: <EmojiPersonalitySlide {...p} /> },
    { name: "top-stickers", tone: "dark", element: <TopStickersSlide {...p} /> },
    { name: "vocabulary", tone: "dark", element: <VocabularySlide {...p} /> },
    { name: "summary", tone: "dark", element: <SummarySlide {...p} /> },
  ];
  return all.filter((s): s is SlideDef => !!s);
}

const variants = {
  enter: (dir: number) => ({ x: dir > 0 ? "100%" : "-100%", opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir > 0 ? "-100%" : "100%", opacity: 0 }),
};

interface Props {
  data: WrappedData;
}

export function WrappedViewer({ data }: Props) {
  const slides = useMemo(() => buildSlides(data), [data]);
  const TOTAL_SLIDES = slides.length;
  const SLIDE_NAMES = slides.map((s) => s.name);
  const { current, direction, goNext, goPrev, setDirection, setCurrent } =
    useSlideNavigation({ totalSlides: TOTAL_SLIDES, autoAdvanceMs: 0 });
  const tone = slides[current]?.tone ?? "dark";

  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [captureProgress, setCaptureProgress] = useState({ done: 0, total: 0 });
  const slideAreaRef = useRef<HTMLDivElement>(null);

  const captureElement = (el: HTMLElement, filename: string) =>
    new Promise<void>((resolve) => {
      // Loaded on demand — keeps ~200 kB out of the initial bundle.
      import("html2canvas")
        .then(({ default: html2canvas }) =>
          html2canvas(el, { scale: 2, useCORS: true, allowTaint: true, logging: false }),
        )
        .then((canvas) => {
          canvas.toBlob((blob) => {
            if (blob) {
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = filename;
              a.click();
              setTimeout(() => URL.revokeObjectURL(url), 2000);
            }
            resolve();
          }, "image/png");
        })
        .catch(() => resolve());
    });

  const downloadCurrentSlide = async () => {
    setShowDownloadMenu(false);
    const el = slideAreaRef.current;
    if (!el) return;
    await new Promise((r) => setTimeout(r, 80));
    await captureElement(el, `telegram-wrapped-${SLIDE_NAMES[current]}.png`);
  };

  const downloadSummaryCard = async () => {
    setShowDownloadMenu(false);
    // Navigate to the summary slide first
    setCurrent(TOTAL_SLIDES - 1);
    await new Promise((r) => setTimeout(r, 900));
    const el = document.getElementById("share-card");
    if (!el) return;
    await captureElement(el, "telegram-wrapped-summary.png");
  };

  const downloadAllSlides = async () => {
    setShowDownloadMenu(false);
    const el = slideAreaRef.current;
    if (!el) return;
    setCapturing(true);

    for (let i = 0; i < TOTAL_SLIDES; i++) {
      setCurrent(i);
      setCaptureProgress({ done: i, total: TOTAL_SLIDES });
      // Wait for slide transition + entrance animations to settle
      await new Promise((r) => setTimeout(r, 1000));
      await captureElement(el, `telegram-wrapped-${String(i + 1).padStart(2, "0")}-${SLIDE_NAMES[i]}.png`);
      await new Promise((r) => setTimeout(r, 100));
    }

    setCapturing(false);
    setCaptureProgress({ done: 0, total: 0 });
  };

  const handleDragEnd = (_: unknown, info: { offset: { x: number } }) => {
    if (capturing) return;
    if (info.offset.x < -30) goNext();
    else if (info.offset.x > 30) goPrev();
  };

  const handleTap = (e: React.MouseEvent) => {
    if (capturing || showDownloadMenu) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x > rect.width / 2) { setDirection(1); goNext(); }
    else { setDirection(-1); goPrev(); }
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-black select-none">
      {/* Progress bar */}
      <div className="absolute top-0 left-0 right-0 z-20 pt-[env(safe-area-inset-top)]">
        <ProgressBar total={TOTAL_SLIDES} current={current} tone={tone} className="pr-14" />
      </div>

      {/* Download button — top right */}
      <button
        onClick={(e) => { e.stopPropagation(); setShowDownloadMenu((v) => !v); }}
        className={`absolute top-3 right-3 z-30 w-8 h-8 flex items-center justify-center rounded-full backdrop-blur-sm transition-all ${
          tone === "light"
            ? "bg-[#0288D1]/10 text-[#0288D1] hover:bg-[#0288D1]/20"
            : "bg-black/30 text-white/70 hover:text-white hover:bg-black/50"
        }`}
        style={{ top: "calc(env(safe-area-inset-top) + 10px)" }}
      >
        {showDownloadMenu ? <X className="w-4 h-4" /> : <Download className="w-4 h-4" />}
      </button>

      {/* Download menu */}
      <AnimatePresence>
        {showDownloadMenu && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: -8 }}
            transition={{ duration: 0.18 }}
            className="absolute right-3 z-30 flex flex-col gap-1 bg-black/80 backdrop-blur-md rounded-2xl p-2 shadow-xl border border-white/10 min-w-[200px]"
            style={{ top: "calc(env(safe-area-inset-top) + 46px)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={downloadCurrentSlide}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-white/90 hover:bg-white/10 transition-colors text-sm font-medium text-left"
            >
              <Image className="w-4 h-4 text-[#29B6F6] shrink-0" />
              Download This Slide
            </button>
            <button
              onClick={downloadSummaryCard}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-white/90 hover:bg-white/10 transition-colors text-sm font-medium text-left"
            >
              <FileImage className="w-4 h-4 text-[#29B6F6] shrink-0" />
              Download Summary Card
            </button>
            <div className="h-px bg-white/10 mx-1" />
            <button
              onClick={downloadAllSlides}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-white/90 hover:bg-white/10 transition-colors text-sm font-medium text-left"
            >
              <Images className="w-4 h-4 text-[#29B6F6] shrink-0" />
              <span>
                Download All Slides
                <span className="block text-white/40 text-xs font-normal">{TOTAL_SLIDES} PNG files</span>
              </span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Capture progress overlay */}
      <AnimatePresence>
        {capturing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute bottom-16 left-1/2 -translate-x-1/2 z-30 bg-black/80 backdrop-blur-md rounded-full px-5 py-2.5 flex items-center gap-3 text-white text-sm font-medium shadow-xl border border-white/10"
          >
            <div className="w-4 h-4 border-2 border-[#29B6F6] border-t-transparent rounded-full animate-spin" />
            Capturing slide {captureProgress.done + 1} / {captureProgress.total}…
          </motion.div>
        )}
      </AnimatePresence>

      {/* Slide area */}
      <div
        ref={slideAreaRef}
        className="w-full h-full"
        style={{ touchAction: "pan-x" }}
        onClick={handleTap}
      >
        <AnimatePresence initial={false} custom={direction} mode="wait">
          <motion.div
            key={current}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.35, ease: "easeInOut" }}
            drag={capturing ? false : "x"}
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.12}
            onDragEnd={handleDragEnd}
            className="absolute inset-0"
          >
            {slides[current]?.element}
          </motion.div>
        </AnimatePresence>
      </div>

      <div
        className={`absolute bottom-4 left-0 right-0 z-20 text-center text-xs pb-[env(safe-area-inset-bottom)] pointer-events-none transition-colors duration-300 ${
          tone === "light" ? "text-gray-400/80" : "text-white/40"
        }`}
      >
        {capturing ? "" : "Tap or swipe to navigate"}
      </div>
    </div>
  );
}
