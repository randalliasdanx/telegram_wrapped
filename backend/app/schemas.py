from __future__ import annotations

from pydantic import BaseModel


class DateRange(BaseModel):
    start: str
    end: str


class ChatStat(BaseModel):
    name: str
    total: int
    pct: float


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
