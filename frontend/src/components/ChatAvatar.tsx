import { useState } from "react";
import { initials } from "../lib/format";

const AVATAR_COLORS = ["#0288D1", "#7C3AED", "#059669", "#E11D48", "#F59E0B", "#0F172A"];

interface Props {
  name: string;
  avatar?: string | null;
  /** Fallback colour index (e.g. rank). */
  index?: number;
  className?: string;
}

/** Round chat avatar: the Telegram thumbnail when present, coloured initials otherwise. */
export function ChatAvatar({ name, avatar, index = 0, className = "w-9 h-9 text-xs" }: Props) {
  const [failed, setFailed] = useState(false);

  if (avatar && !failed) {
    return (
      <img
        src={avatar}
        alt=""
        draggable={false}
        onError={() => setFailed(true)}
        className={`${className} rounded-full object-cover shrink-0 bg-gray-100`}
      />
    );
  }

  return (
    <div
      aria-hidden
      className={`${className} rounded-full flex items-center justify-center text-white font-bold shrink-0`}
      style={{ backgroundColor: AVATAR_COLORS[index % AVATAR_COLORS.length] }}
    >
      {initials(name)}
    </div>
  );
}
