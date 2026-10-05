export interface DateRange {
  start: string;
  end: string;
}

export interface ChatStat {
  name: string;
  /** Messages exchanged in the period (both sides). */
  total: number;
  /** Share (0-100) of the user's sent messages that went to this chat. */
  pct: number;
  /** Messages the user sent in this chat. */
  sent?: number;
  /** User's share (0-100) of this chat's messages. */
  sent_share?: number;
  is_group?: boolean;
  /** data: URI thumbnail. */
  avatar?: string | null;
}

export interface ReactionInfo {
  emoji: string;
  count: number;
}

export interface MostReactedMessage {
  text: string;
  chat: string;
  sender: string;
  date: string;
  reactions: ReactionInfo[];
  reply_preview?: string | null;
}

export interface WordStat {
  word: string;
  count: number;
}

export interface BigramStat {
  phrase: string;
  count: number;
}

export interface EmojiStat {
  emoji: string;
  count: number;
}

export interface StickerStat {
  emoji: string;
  count: number;
  image?: string | null;
}

export interface TexterType {
  type: string;
  description: string;
  fun_fact: string;
  traits: string[];
  code: string;
}

export interface MonthStat {
  /** Short month name, e.g. "Oct". */
  month: string;
  year: number;
  count: number;
}

export interface BusiestDay {
  /** e.g. "March 14, 2026". */
  date: string;
  count: number;
  top_chat?: string | null;
}

export interface ReplySpeed {
  median_seconds: number;
  samples: number;
  fastest_chat?: string | null;
  fastest_seconds?: number | null;
}

export interface Accuracy {
  /** "exact" = every sent message analysed. */
  mode: "exact" | "estimated";
  /** % of the user's sent messages analysed directly. */
  coverage_pct: number;
  messages_analyzed: number;
  chats_analyzed: number;
  takeout: boolean;
  duration_seconds: number;
  api_calls: number;
}

/** Media counts of what the user sent in the period. */
export type MediaKey =
  | "photos"
  | "videos"
  | "voice_notes"
  | "round_videos"
  | "gifs"
  | "documents"
  | "music"
  | "links";

export interface WrappedData {
  grand_total: number;
  daily_average: number;
  top_chats: ChatStat[];
  peak_hour: number;
  peak_personality: string;
  hourly_distribution: Record<number, number>;
  total_night_messages: number;
  longest_streak: number;
  streak_partner: string;
  conversation_starter: { user_pct: number; other_pct: number };
  most_reacted_message: MostReactedMessage | null;
  top_emojis: EmojiStat[];
  top_stickers: StickerStat[];
  texter_type: TexterType | null;
  top_sticker_pack: Record<string, string> | null;
  top_words: WordStat[];
  top_bigrams: BigramStat[];
  media_totals: Record<string, number>;
  date_range: DateRange;
  vibe_age: number | null;
  // ── Added in the accuracy rewrite; optional so older results still render ──
  total_chats?: number;
  /** Days with at least one sent message. */
  active_days?: number;
  stickers_sent?: number;
  /** Chronological, ~12-13 entries. */
  monthly_activity?: MonthStat[];
  /** 0 = Monday … 6 = Sunday. */
  weekday_distribution?: Record<number, number>;
  busiest_day?: BusiestDay | null;
  reply_speed?: ReplySpeed | null;
  accuracy?: Accuracy | null;
}

export type PipelinePhase =
  | "queued"
  | "init"
  | "counting"
  | "fetching"
  | "conversations"
  | "computing"
  | "done"
  | "error";

export interface SSEProgress {
  /** One of PipelinePhase; typed as string so legacy phase names still parse. */
  phase: PipelinePhase | (string & {});
  message: string;
  progress?: number;
  total?: number;
  messages_analyzed?: number;
  queue_position?: number;
  eta_seconds?: number;
}

export interface AuthResponse {
  session_id: string;
  phone_code_hash: string;
}

export interface VerifyResponse {
  success: boolean;
}
