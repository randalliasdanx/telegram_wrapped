import { motion } from "framer-motion";
import { CalendarCheck, CalendarDays, Flame } from "lucide-react";
import type { WrappedData, DateRange } from "../../api/types";
import { formatNumber } from "../../lib/format";

interface Props {
  data: WrappedData;
  dateRange: DateRange;
}

const MONTH_NAMES: Record<string, string> = {
  Jan: "January", Feb: "February", Mar: "March", Apr: "April", May: "May", Jun: "June",
  Jul: "July", Aug: "August", Sep: "September", Oct: "October", Nov: "November", Dec: "December",
};

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { delay, duration: 0.5 },
});

const RING_R = 26;
const RING_C = 2 * Math.PI * RING_R;

export function RhythmSlide({ data, dateRange }: Props) {
  const months = data.monthly_activity ?? [];
  const maxMonth = Math.max(1, ...months.map((m) => m.count));
  const peakIdx = months.findIndex((m) => m.count === maxMonth);
  const peak = months[peakIdx];

  const wd = data.weekday_distribution ?? {};
  const weekdayCounts = WEEKDAYS.map((_, i) => Number(wd[i] ?? 0));
  const wdTotal = weekdayCounts.reduce((a, b) => a + b, 0);
  const wdMax = Math.max(1, ...weekdayCounts);
  const topWd = weekdayCounts.indexOf(wdMax);

  const activeDays = data.active_days ?? 0;
  const periodDays = Math.max(365, activeDays);
  const activeFrac = Math.min(1, activeDays / periodDays);

  const busiest = data.busiest_day;

  return (
    <div className="w-full h-full bg-[#f8fafc] relative overflow-y-auto overflow-x-hidden">
      <motion.div
        className="absolute top-[-10%] right-[-15%] w-80 h-80 rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(41,182,246,0.12) 0%, transparent 70%)" }}
        animate={{ x: [0, -14, 0], y: [0, 12, 0] }}
        transition={{ duration: 13, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative min-h-full max-w-xl w-full mx-auto flex flex-col justify-center px-5 py-14">
        <motion.div {...fadeUp(0)} className="text-center mb-5">
          <span className="text-[#0288D1] uppercase tracking-widest text-xs font-semibold">
            Your Year in Rhythm
          </span>
          {peak ? (
            <h2 className="font-display text-[2rem] leading-tight font-extrabold text-gray-900 mt-2">
              <span className="bg-linear-to-r from-[#29B6F6] to-[#0288D1] bg-clip-text text-transparent">
                {MONTH_NAMES[peak.month] ?? peak.month}
              </span>{" "}
              was your loudest month
            </h2>
          ) : (
            <h2 className="font-display text-3xl font-extrabold text-gray-900 mt-2">
              Your texting rhythm
            </h2>
          )}
          {peak && (
            <p className="text-gray-500 text-sm mt-1.5">
              {formatNumber(peak.count)} messages sent in {MONTH_NAMES[peak.month] ?? peak.month} {peak.year}
            </p>
          )}
        </motion.div>

        {/* Monthly bars */}
        {months.length > 0 && (
          <motion.div {...fadeUp(0.15)} className="bg-white rounded-2xl shadow-sm border border-gray-100 px-3 pt-4 pb-2.5 mb-3">
            <div className="flex items-end gap-1 h-32">
              {months.map((m, i) => {
                const isPeak = i === peakIdx;
                // Cap at 84% so the peak's count label fits above its bar.
                const h = Math.max(4, (m.count / maxMonth) * 84);
                return (
                  <div key={`${m.month}-${m.year}`} className="flex-1 h-full flex flex-col justify-end items-center relative">
                    {isPeak && (
                      <motion.span
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 1.1, duration: 0.3 }}
                        className="absolute -top-1 text-[9px] font-bold text-white bg-[#0288D1] rounded-md px-1 py-px whitespace-nowrap z-10"
                      >
                        {formatNumber(m.count)}
                      </motion.span>
                    )}
                    <motion.div
                      className="w-full rounded-t-md rounded-b-sm"
                      style={{
                        background: isPeak
                          ? "linear-gradient(180deg, #29B6F6 0%, #0288D1 100%)"
                          : "#B3E5FC",
                        boxShadow: isPeak ? "0 6px 16px rgba(2,136,209,0.35)" : undefined,
                      }}
                      initial={{ height: 0 }}
                      animate={{ height: `${h}%` }}
                      transition={{ delay: 0.3 + i * 0.05, duration: 0.6, ease: "easeOut" }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="flex gap-1 mt-1.5">
              {months.map((m, i) => (
                <span
                  key={`${m.month}-${m.year}-l`}
                  className={`flex-1 text-center text-[9px] leading-none ${
                    i === peakIdx ? "font-bold text-[#0288D1]" : "text-gray-400"
                  }`}
                >
                  {m.month.slice(0, 1)}
                </span>
              ))}
            </div>
          </motion.div>
        )}

        <div className="grid grid-cols-2 gap-3 mb-3">
          {busiest && (
            <motion.div {...fadeUp(0.45)} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-3.5 flex flex-col">
              <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center mb-2">
                <Flame className="w-4 h-4 text-orange-500" />
              </div>
              <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold">Busiest day</span>
              <span className="text-sm font-bold text-gray-900 leading-snug mt-0.5">{busiest.date}</span>
              <span className="text-xs text-gray-500 mt-0.5">
                {formatNumber(busiest.count)} messages
                {busiest.top_chat && (
                  <>
                    , mostly with <span className="font-semibold text-gray-700">{busiest.top_chat}</span>
                  </>
                )}
              </span>
            </motion.div>
          )}

          {activeDays > 0 && (
            <motion.div
              {...fadeUp(0.55)}
              className={`bg-white rounded-2xl shadow-sm border border-gray-100 p-3.5 flex flex-col ${busiest ? "" : "col-span-2"}`}
            >
              <div className="w-8 h-8 rounded-lg bg-sky-50 flex items-center justify-center mb-2">
                <CalendarCheck className="w-4 h-4 text-[#0288D1]" />
              </div>
              <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold">Active days</span>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="flex items-baseline gap-1 min-w-0">
                  <span className="text-2xl font-display font-extrabold text-gray-900 leading-none">{activeDays}</span>
                  <span className="text-xs text-gray-400">/ {periodDays}</span>
                </div>
                <svg width="34" height="34" viewBox="0 0 60 60" className="shrink-0 -rotate-90 ml-auto">
                  <circle cx="30" cy="30" r={RING_R} fill="none" stroke="#E1F5FE" strokeWidth="8" />
                  <motion.circle
                    cx="30" cy="30" r={RING_R} fill="none" stroke="#0288D1" strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={RING_C}
                    initial={{ strokeDashoffset: RING_C }}
                    animate={{ strokeDashoffset: RING_C * (1 - activeFrac) }}
                    transition={{ delay: 0.7, duration: 1.2, ease: "easeOut" }}
                  />
                </svg>
              </div>
              <span className="text-xs text-gray-500 mt-1 leading-snug">
                You texted on {Math.round(activeFrac * 100)}% of days
              </span>
            </motion.div>
          )}
        </div>

        {wdTotal > 0 && (
          <motion.div {...fadeUp(0.65)} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-3.5">
            <div className="flex items-center gap-2 mb-2.5">
              <CalendarDays className="w-4 h-4 text-[#0288D1]" />
              <span className="text-sm text-gray-700">
                <span className="font-bold text-gray-900">{WEEKDAYS[topWd]}s</span> are your day
              </span>
            </div>
            <div className="flex items-end gap-1.5 h-12">
              {weekdayCounts.map((c, i) => (
                <motion.div
                  key={i}
                  className="flex-1 rounded-md"
                  style={{ background: i === topWd ? "linear-gradient(180deg, #29B6F6 0%, #0288D1 100%)" : "#B3E5FC" }}
                  initial={{ height: 0 }}
                  animate={{ height: `${Math.max(6, (c / wdMax) * 100)}%` }}
                  transition={{ delay: 0.85 + i * 0.05, duration: 0.5, ease: "easeOut" }}
                />
              ))}
            </div>
            <div className="flex gap-1.5 mt-1.5">
              {WEEKDAYS.map((d, i) => (
                <span
                  key={d}
                  className={`flex-1 text-center text-[10px] leading-none ${i === topWd ? "font-bold text-[#0288D1]" : "text-gray-400"}`}
                >
                  {d.slice(0, 2)}
                </span>
              ))}
            </div>
          </motion.div>
        )}

        <motion.p
          {...fadeUp(1)}
          className="mt-5 text-center text-xs uppercase tracking-widest text-gray-300 font-semibold"
        >
          {dateRange.start} – {dateRange.end}
        </motion.p>
      </div>
    </div>
  );
}
