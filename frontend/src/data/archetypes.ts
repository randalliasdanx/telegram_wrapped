// Canonical archetype list sourced from backend/app/ml/models/personality_types.json
// 16 personality types across 4 binary axes: E/T, V/M, I/R, N/D

export interface Archetype {
  code: string;
  name: string;
  description: string;
  traits: string[];
}

export const ARCHETYPES: Archetype[] = [
  {
    code: "EVIN",
    name: "The Night Creator",
    description: "You flood chats with media at 2 AM and start half the conversations. Your friends wake up to a wall of stickers, photos, and voice notes.",
    traits: ["Expressive", "Verbose", "Initiator", "Night Owl"],
  },
  {
    code: "EVID",
    name: "The Social Butterfly",
    description: "You're the life of every group chat — always starting conversations, always sending something interesting.",
    traits: ["Expressive", "Verbose", "Initiator", "Day Person"],
  },
  {
    code: "EVRN",
    name: "The Late-Night Reactor",
    description: "Your friends send a message and you reply with a voice note, 3 stickers, and a paragraph — at midnight.",
    traits: ["Expressive", "Verbose", "Reactor", "Night Owl"],
  },
  {
    code: "EVRD",
    name: "The Enthusiast",
    description: "You reply to everything with maximum effort — long messages, perfect stickers, the right GIF. The group chat's biggest hype person.",
    traits: ["Expressive", "Verbose", "Reactor", "Day Person"],
  },
  {
    code: "EMIN",
    name: "The Midnight Memer",
    description: "Stickers, GIFs, and voice notes do the talking for you. Short but visually loud, especially after midnight.",
    traits: ["Expressive", "Minimal", "Initiator", "Night Owl"],
  },
  {
    code: "EMID",
    name: "The Quick Starter",
    description: "You kick off conversations with a sticker or a quick voice note. Efficient, expressive, and always available during the day.",
    traits: ["Expressive", "Minimal", "Initiator", "Day Person"],
  },
  {
    code: "EMRN",
    name: "The Sticker Ghost",
    description: "You haunt the chat at odd hours with perfectly chosen reactions — a sticker here, a GIF there. Few words, maximum impact.",
    traits: ["Expressive", "Minimal", "Reactor", "Night Owl"],
  },
  {
    code: "EMRD",
    name: "The Vibe Check",
    description: "You keep the energy up with quick reactions and well-placed media. Not many words, but every sticker lands perfectly.",
    traits: ["Expressive", "Minimal", "Reactor", "Day Person"],
  },
  {
    code: "TVIN",
    name: "The Midnight Novelist",
    description: "You write essays at 3 AM and start deep conversations when everyone else is asleep. Your messages deserve their own scroll bar.",
    traits: ["Text-Purist", "Verbose", "Initiator", "Night Owl"],
  },
  {
    code: "TVID",
    name: "The Conversationalist",
    description: "You start thoughtful conversations with long, detailed messages. No stickers needed — your words carry all the weight.",
    traits: ["Text-Purist", "Verbose", "Initiator", "Day Person"],
  },
  {
    code: "TVRN",
    name: "The Deep Replier",
    description: "When you finally reply, it's a wall of text that addresses every point. You process slowly but respond thoroughly — usually at night.",
    traits: ["Text-Purist", "Verbose", "Reactor", "Night Owl"],
  },
  {
    code: "TVRD",
    name: "The Analyst",
    description: "You respond to messages with structured, detailed replies. If texting were a job, you'd be the senior consultant.",
    traits: ["Text-Purist", "Verbose", "Reactor", "Day Person"],
  },
  {
    code: "TMIN",
    name: "The Shadow Initiator",
    description: "You start conversations with a single 'hey' at 1 AM. Minimal words, maximal mystery. No media, no fluff.",
    traits: ["Text-Purist", "Minimal", "Initiator", "Night Owl"],
  },
  {
    code: "TMID",
    name: "The Efficient Texter",
    description: "You say what needs to be said and nothing more. Every message is purposeful. You actually answer questions directly.",
    traits: ["Text-Purist", "Minimal", "Initiator", "Day Person"],
  },
  {
    code: "TMRN",
    name: "The Ghost",
    description: "You reply with 'k' at 2 AM after leaving everyone on read for hours. Minimal effort, maximum intrigue.",
    traits: ["Text-Purist", "Minimal", "Reactor", "Night Owl"],
  },
  {
    code: "TMRD",
    name: "The Minimalist",
    description: "Short replies, reasonable hours, and you let others drive the conversation. Present but efficient.",
    traits: ["Text-Purist", "Minimal", "Reactor", "Day Person"],
  },
];
