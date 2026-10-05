import type { WrappedData } from "../api/types";

/**
 * Derived data + "does this slide have anything to show?" checks.
 * Older results (pre-accuracy rewrite) lack the newer fields, so slides that
 * depend on them are skipped rather than rendered empty.
 */

export const MEDIA_KEYS = [
  "photos", "videos", "voice_notes", "round_videos", "gifs",
  "stickers", "links", "documents", "music",
] as const;

export interface MediaItem {
  key: (typeof MEDIA_KEYS)[number];
  count: number;
}

/** Media the user sent (stickers included), non-zero only, biggest first. */
export function getMediaItems(data: WrappedData): MediaItem[] {
  const counts: Record<string, number> = { ...data.media_totals };
  if (data.stickers_sent) counts.stickers = data.stickers_sent;
  return MEDIA_KEYS.map((key) => ({ key, count: Number(counts[key] ?? 0) }))
    .filter((it) => it.count > 0)
    .sort((a, b) => b.count - a.count);
}

export function hasRhythm(data: WrappedData): boolean {
  return (data.monthly_activity ?? []).some((m) => m.count > 0);
}

export function hasReplySpeed(data: WrappedData): boolean {
  return !!data.reply_speed && data.reply_speed.samples > 0;
}

export function hasMediaMix(data: WrappedData): boolean {
  return getMediaItems(data).length > 0;
}
