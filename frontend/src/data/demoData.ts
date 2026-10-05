import type { WrappedData } from "../api/types";

/**
 * A realistic, fully-populated WrappedData used by `/?demo=1` so the deck can be
 * previewed without a Telegram login. Loaded via dynamic import, so it never
 * ships in the main bundle.
 */

/** Simple illustrated avatar as an SVG data URI (stands in for a Telegram thumbnail). */
function svgAvatar(from: string, to: string, glyph: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${from}"/><stop offset="1" stop-color="${to}"/></linearGradient></defs>
<rect width="80" height="80" fill="url(#g)"/>
<text x="40" y="54" font-size="40" text-anchor="middle" font-family="Apple Color Emoji,Segoe UI Emoji,Noto Color Emoji,sans-serif">${glyph}</text>
</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

const HOURLY = [
  1420, 980, 610, 330, 140, 90, 160, 420, 980, 1510, 1880, 2050,
  2310, 2240, 2010, 1980, 2120, 2380, 2690, 3010, 3420, 3860, 4170, 3480,
];

export const DEMO_DATA: WrappedData = {
  grand_total: 48213,
  daily_average: 132,
  total_chats: 87,
  active_days: 341,
  stickers_sent: 1874,
  date_range: { start: "Oct 2025", end: "Oct 2026" },

  top_chats: [
    { name: "Maya Chen", total: 18240, pct: 19.3, sent: 9310, sent_share: 51.0, is_group: false, avatar: svgAvatar("#FDE68A", "#F59E0B", "🌻") },
    { name: "Weekend Crew 🏕️", total: 31580, pct: 12.9, sent: 6210, sent_share: 19.7, is_group: true, avatar: svgAvatar("#A7F3D0", "#059669", "🏕️") },
    { name: "Mum", total: 9870, pct: 9.1, sent: 4402, sent_share: 44.6, is_group: false, avatar: null },
    { name: "Leo Martins", total: 7644, pct: 8.3, sent: 3980, sent_share: 52.1, is_group: false, avatar: svgAvatar("#BFDBFE", "#2563EB", "🎸") },
    { name: "Design Team", total: 12005, pct: 5.2, sent: 2511, sent_share: 20.9, is_group: true, avatar: null },
  ],

  peak_hour: 22,
  peak_personality: "Night Owl",
  hourly_distribution: Object.fromEntries(HOURLY.map((c, h) => [h, c])),
  total_night_messages: 9412,

  longest_streak: 47,
  streak_partner: "Maya Chen",
  conversation_starter: { user_pct: 58, other_pct: 42 },

  most_reacted_message: {
    text: "I just replied-all to the entire building group chat with my grocery list. It had 'emotional support cheese' on it 😭",
    chat: "Weekend Crew 🏕️",
    sender: "You",
    date: "March 14",
    reactions: [
      { emoji: "😂", count: 23 },
      { emoji: "💀", count: 11 },
      { emoji: "❤️", count: 6 },
    ],
    reply_preview: null,
  },

  top_emojis: [
    { emoji: "😂", count: 2140 },
    { emoji: "😭", count: 1312 },
    { emoji: "❤️", count: 988 },
    { emoji: "🔥", count: 640 },
    { emoji: "🙏", count: 402 },
    { emoji: "👀", count: 377 },
    { emoji: "✨", count: 290 },
    { emoji: "💀", count: 254 },
  ],
  top_stickers: [
    { emoji: "🐸", count: 312, image: null },
    { emoji: "😎", count: 201, image: null },
    { emoji: "🥹", count: 166, image: null },
    { emoji: "👍", count: 143, image: null },
    { emoji: "🐱", count: 97, image: null },
  ],
  top_sticker_pack: null,

  texter_type: {
    type: "The Night Creator",
    code: "EVIN",
    description:
      "You flood chats with media at 2 AM and start half the conversations. Your friends wake up to a wall of stickers, photos, and voice notes.",
    fun_fact: "Over 19% of everything you sent landed after 10 PM — the group chat's unofficial night shift.",
    traits: ["Expressive", "Verbose", "Initiator", "Night Owl"],
  },
  vibe_age: 24,

  top_words: [
    { word: "literally", count: 812 },
    { word: "tonight", count: 604 },
    { word: "coffee", count: 488 },
    { word: "honestly", count: 452 },
    { word: "omw", count: 397 },
    { word: "babe", count: 344 },
    { word: "deadline", count: 290 },
  ],
  top_bigrams: [
    { phrase: "on my way", count: 286 },
    { phrase: "wait what", count: 241 },
    { phrase: "send pics", count: 188 },
    { phrase: "good morning", count: 175 },
    { phrase: "no worries", count: 162 },
    { phrase: "call me later", count: 121 },
  ],

  media_totals: {
    photos: 1284,
    videos: 212,
    voice_notes: 486,
    round_videos: 64,
    gifs: 318,
    documents: 41,
    music: 12,
    links: 597,
  },

  monthly_activity: [
    { month: "Oct", year: 2025, count: 2210 },
    { month: "Nov", year: 2025, count: 3480 },
    { month: "Dec", year: 2025, count: 4620 },
    { month: "Jan", year: 2026, count: 3910 },
    { month: "Feb", year: 2026, count: 3550 },
    { month: "Mar", year: 2026, count: 5874 },
    { month: "Apr", year: 2026, count: 4210 },
    { month: "May", year: 2026, count: 3760 },
    { month: "Jun", year: 2026, count: 4105 },
    { month: "Jul", year: 2026, count: 4690 },
    { month: "Aug", year: 2026, count: 3320 },
    { month: "Sep", year: 2026, count: 3184 },
    { month: "Oct", year: 2026, count: 1300 },
  ],
  weekday_distribution: { 0: 6420, 1: 6610, 2: 6890, 3: 7012, 4: 8240, 5: 7380, 6: 5661 },
  busiest_day: { date: "March 14, 2026", count: 612, top_chat: "Weekend Crew 🏕️" },
  reply_speed: { median_seconds: 134, samples: 3812, fastest_chat: "Maya Chen", fastest_seconds: 38 },
  accuracy: {
    mode: "exact",
    coverage_pct: 100,
    messages_analyzed: 48213,
    chats_analyzed: 87,
    takeout: true,
    duration_seconds: 41.6,
    api_calls: 212,
  },
};
