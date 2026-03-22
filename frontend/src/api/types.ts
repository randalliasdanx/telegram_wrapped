export interface DateRange {
  start: string;
  end: string;
}

export interface ChatStat {
  name: string;
  total: number;
  pct: number;
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
  reply_preview?: string;
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
  image?: string;
}

export interface TexterType {
  type: string;
  description: string;
  fun_fact: string;
  traits: string[];
  code: string;
}

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
  top_sticker_pack: { name: string } | null;
  top_words: WordStat[];
  top_bigrams: BigramStat[];
  media_totals: Record<string, number>;
  date_range: DateRange;
  vibe_age: number | null;
}

export interface SSEProgress {
  phase: string;
  progress?: number;
  total?: number;
  message: string;
}

export interface AuthResponse {
  session_id: string;
  phone_code_hash: string;
}

export interface VerifyResponse {
  success: boolean;
}
