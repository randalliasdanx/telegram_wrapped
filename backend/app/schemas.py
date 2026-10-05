from __future__ import annotations

from pydantic import BaseModel


class DateRange(BaseModel):
    start: str
    end: str


class ChatStat(BaseModel):
    name: str
    total: int  # messages exchanged in the period (both sides)
    pct: float  # share of the user's sent messages that went to this chat (0-100)
    sent: int = 0  # messages the user sent in this chat
    sent_share: float = 0.0  # user's share of this chat's messages (0-100)
    is_group: bool = False
    avatar: str | None = None  # data: URI thumbnail


class ReactionInfo(BaseModel):
    emoji: str
    count: int


class MostReactedMessage(BaseModel):
    text: str
    chat: str
    sender: str
    date: str
    reactions: list[ReactionInfo]
    reply_preview: str | None = None


class EmojiStat(BaseModel):
    emoji: str
    count: int


class WordStat(BaseModel):
    word: str
    count: int


class BigramStat(BaseModel):
    phrase: str
    count: int


class StickerStat(BaseModel):
    emoji: str
    count: int
    image: str | None = None


class TexterType(BaseModel):
    type: str
    description: str
    fun_fact: str = ""
    traits: list[str]
    code: str = ""


class MonthStat(BaseModel):
    month: str  # short month name, e.g. "Oct"
    year: int
    count: int


class BusiestDay(BaseModel):
    date: str  # e.g. "March 14, 2026"
    count: int
    top_chat: str | None = None


class ReplySpeed(BaseModel):
    median_seconds: int
    samples: int
    fastest_chat: str | None = None
    fastest_seconds: int | None = None


class Accuracy(BaseModel):
    mode: str  # "exact" (every sent message analysed) or "estimated"
    coverage_pct: float  # % of the user's sent messages analysed directly
    total_exact: bool = True  # False when the sent total had to be estimated
    messages_analyzed: int
    chats_analyzed: int
    takeout: bool
    duration_seconds: float
    api_calls: int


class WrappedData(BaseModel):
    grand_total: int
    daily_average: int
    top_chats: list[ChatStat]
    peak_hour: int
    peak_personality: str
    hourly_distribution: dict[int, int]
    total_night_messages: int
    longest_streak: int
    streak_partner: str
    conversation_starter: dict[str, int]
    most_reacted_message: MostReactedMessage | None = None
    top_emojis: list[EmojiStat]
    top_stickers: list[StickerStat] = []
    texter_type: TexterType | None = None
    top_sticker_pack: dict[str, str] | None = None
    top_words: list[WordStat]
    top_bigrams: list[BigramStat]
    media_totals: dict[str, int]
    date_range: DateRange
    vibe_age: int | None = None
    total_chats: int = 0
    active_days: int = 0
    stickers_sent: int = 0
    monthly_activity: list[MonthStat] = []
    weekday_distribution: dict[int, int] = {}  # 0 = Monday
    busiest_day: BusiestDay | None = None
    reply_speed: ReplySpeed | None = None
    accuracy: Accuracy | None = None
