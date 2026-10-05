import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import {
  Camera, Video, Mic, Aperture, ImagePlay, Sticker, Link2, FileText, Music,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";
import { formatCompact, formatNumber } from "../../lib/format";
import { getMediaItems } from "../../lib/slideData";
import type { MediaItem } from "../../lib/slideData";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

interface MediaMeta {
  label: string;
  icon: LucideIcon;
  color: string;
  tint: string;
  headline: string;
}

const MEDIA_META: Record<MediaItem["key"], MediaMeta> = {
  photos: { label: "Photos", icon: Camera, color: "#0288D1", tint: "#E1F5FE", headline: "You speak in photos" },
  videos: { label: "Videos", icon: Video, color: "#7C3AED", tint: "#EDE9FE", headline: "Director's cut, every time" },
  voice_notes: { label: "Voice notes", icon: Mic, color: "#E11D48", tint: "#FFE4E6", headline: "Voice notes are your love language" },
  round_videos: { label: "Video circles", icon: Aperture, color: "#F59E0B", tint: "#FEF3C7", headline: "Video-circle royalty" },
  gifs: { label: "GIFs", icon: ImagePlay, color: "#059669", tint: "#D1FAE5", headline: "Certified GIF wizard" },
  stickers: { label: "Stickers", icon: Sticker, color: "#DB2777", tint: "#FCE7F3", headline: "Sticker connoisseur" },
  links: { label: "Links", icon: Link2, color: "#0EA5E9", tint: "#E0F2FE", headline: "The group chat's link dealer" },
  documents: { label: "Files", icon: FileText, color: "#475569", tint: "#F1F5F9", headline: "Basically a walking shared drive" },
  music: { label: "Music", icon: Music, color: "#8B5CF6", tint: "#F3E8FF", headline: "Resident DJ" },
};

const tileVariants: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.85 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: 0.55 + i * 0.07, type: "spring", stiffness: 220, damping: 18 },
  }),
};

export function MediaMixSlide({ data, dateRange }: Props) {
  const items = getMediaItems(data);
  if (items.length === 0) return null;

  const total = items.reduce((a, b) => a + b.count, 0);
  const [top, ...rest] = items;
  const topMeta = MEDIA_META[top.key];
  const TopIcon = topMeta.icon;

  return (
    <div className="w-full h-full bg-white relative overflow-y-auto overflow-x-hidden">
      <motion.div
        className="absolute top-[-12%] left-[-20%] w-80 h-80 rounded-full pointer-events-none"
        style={{ background: `radial-gradient(circle, ${topMeta.color}1f 0%, transparent 70%)` }}
        animate={{ x: [0, 16, 0], y: [0, 10, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative min-h-full max-w-xl w-full mx-auto flex flex-col justify-center px-5 py-14">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-5"
        >
          <span className="text-[#0288D1] uppercase tracking-widest text-xs font-semibold">Media Mix</span>
          <h2 className="font-display text-[2rem] font-extrabold text-gray-900 mt-2 leading-tight">
            {topMeta.headline}
          </h2>
          <p className="text-gray-500 text-sm mt-1.5">
            <span className="font-semibold text-gray-700">{formatNumber(total)}</span> things shared that words couldn't cover
          </p>
        </motion.div>

        {/* Proportion strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="flex h-3 rounded-full overflow-hidden bg-gray-100 mb-4"
        >
          {items.map((it, i) => (
            <motion.div
              key={it.key}
              style={{ background: MEDIA_META[it.key].color }}
              initial={{ width: 0 }}
              animate={{ width: `${(it.count / total) * 100}%` }}
              transition={{ delay: 0.3 + i * 0.06, duration: 0.6, ease: "easeOut" }}
            />
          ))}
        </motion.div>

        {/* Hero tile */}
        <motion.div
          custom={0}
          variants={tileVariants}
          initial="hidden"
          animate="show"
          className="rounded-2xl p-4 mb-3 flex items-center gap-4 relative overflow-hidden"
          style={{ background: topMeta.tint }}
        >
          <motion.div
            className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 shadow-md"
            style={{ background: topMeta.color }}
            animate={{ rotate: [0, -8, 8, 0] }}
            transition={{ delay: 1.4, duration: 0.8, repeat: Infinity, repeatDelay: 3 }}
          >
            <TopIcon className="w-7 h-7 text-white" />
          </motion.div>
          <div className="flex-1 min-w-0">
            <span className="text-[10px] uppercase tracking-widest font-bold" style={{ color: topMeta.color }}>
              #1 · {topMeta.label}
            </span>
            <p className="font-display text-3xl font-extrabold text-gray-900 leading-none mt-1">
              {formatNumber(top.count)}
            </p>
          </div>
          <div className="text-right shrink-0">
            <span className="font-display text-2xl font-extrabold" style={{ color: topMeta.color }}>
              {Math.round((top.count / total) * 100)}%
            </span>
            <span className="block text-[10px] text-gray-500">of your media</span>
          </div>
        </motion.div>

        {rest.length > 0 && (
          <div className="grid grid-cols-3 gap-2.5">
            {rest.map((it, i) => {
              const meta = MEDIA_META[it.key];
              const Icon = meta.icon;
              return (
                <motion.div
                  key={it.key}
                  custom={i + 1}
                  variants={tileVariants}
                  initial="hidden"
                  animate="show"
                  className="rounded-2xl p-3 flex flex-col items-start border border-gray-100 bg-white shadow-sm"
                >
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center mb-2"
                    style={{ background: meta.tint }}
                  >
                    <Icon className="w-4 h-4" style={{ color: meta.color }} />
                  </div>
                  <span className="font-display text-lg font-extrabold text-gray-900 leading-none">
                    {formatCompact(it.count)}
                  </span>
                  <span className="text-[11px] text-gray-500 mt-0.5 truncate w-full">{meta.label}</span>
                </motion.div>
              );
            })}
          </div>
        )}

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3 }}
          className="mt-5 text-center text-xs uppercase tracking-widest text-gray-300 font-semibold"
        >
          {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </div>
  );
}
