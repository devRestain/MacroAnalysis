import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  CalendarMonthResponse,
  CalendarTodayBasis,
} from "../../entities/calendarEvent/types";
import { useLanguage } from "../i18n";
import { dayNumber, formatMonthLabel, weekdayLabels } from "../utils/calendar";

function dotTone(day: CalendarMonthResponse["days"][number]) {
  if (day.highCount > 0) return "bg-signal-red";
  if (day.mediumCount > 0) return "bg-signal-yellow";
  if (day.eventCount > 0) return "bg-text-muted";
  return "bg-transparent";
}

export function CalendarMonthGrid({
  data,
  selectedDate,
  onSelectDate,
  onShiftMonth,
  todayBasis,
  onTodayBasisChange,
  size = "compact",
  showTodayBasisToggle = true,
}: {
  data: CalendarMonthResponse;
  selectedDate?: string | null;
  onSelectDate: (date: string) => void;
  onShiftMonth: (delta: number) => void;
  todayBasis: CalendarTodayBasis;
  onTodayBasisChange: (basis: CalendarTodayBasis) => void;
  size?: "compact" | "full";
  showTodayBasisToggle?: boolean;
}) {
  const { t } = useLanguage();
  const weekdays = weekdayLabels();
  const compact = size === "compact";

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex items-center gap-1 rounded-full border border-surface-border bg-surface-hover px-1 py-1">
          <button
            onClick={() => onShiftMonth(-1)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-text-secondary transition hover:bg-white"
            aria-label={t("calendar.prevMonth")}
          >
            <ChevronLeft size={16} />
          </button>
          <div className="min-w-[120px] text-center text-sm font-bold tracking-[-0.02em] text-text-primary">
            {formatMonthLabel(data.month)}
          </div>
          <button
            onClick={() => onShiftMonth(1)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-text-secondary transition hover:bg-white"
            aria-label={t("calendar.nextMonth")}
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {showTodayBasisToggle && (
          <div className="inline-flex rounded-full border border-surface-border bg-surface-hover p-1">
            <button
              onClick={() => onTodayBasisChange("market")}
              className={`rounded-full px-3 py-1.5 text-xs font-bold ${todayBasis === "market" ? "bg-white text-text-primary shadow-sm" : "text-text-muted"}`}
            >
              {t("calendar.todayBasis.market")}
            </button>
            <button
              onClick={() => onTodayBasisChange("local")}
              className={`rounded-full px-3 py-1.5 text-xs font-bold ${todayBasis === "local" ? "bg-white text-text-primary shadow-sm" : "text-text-muted"}`}
            >
              {t("calendar.todayBasis.local")}
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-7 gap-1.5">
        {weekdays.map((weekday) => (
          <div
            key={weekday}
            className="pb-1 text-center text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted"
          >
            {weekday}
          </div>
        ))}
        {data.days.map((day) => {
          const selected = selectedDate === day.date;
          const baseClass = compact
            ? "aspect-square min-h-0 p-1.5"
            : "min-h-[110px] p-2.5";
          const compactDefaultState =
            compact && day.eventCount > 0 && !selected && !day.isToday
              ? day.inMonth
                ? "border-[#efb4b4] bg-[#fdf0f0] hover:bg-[#fbe5e5]"
                : "border-[#efb4b4] bg-[#fdf0f0] text-text-muted hover:bg-[#fbe5e5]"
              : day.inMonth
                ? "border-surface-border bg-white hover:bg-surface-hover"
                : "border-surface-border/70 bg-surface-hover/70 text-text-muted hover:bg-surface-hover";
          return (
            <button
              key={day.date}
              onClick={() => onSelectDate(day.date)}
              className={`rounded-[16px] border text-left transition ${baseClass} ${
                selected
                  ? "border-accent bg-accent/8 shadow-[0_8px_24px_-20px_rgba(36,87,214,0.5)]"
                  : compact
                    ? compactDefaultState
                    : day.inMonth
                      ? "border-surface-border bg-white hover:bg-surface-hover"
                      : "border-surface-border/70 bg-surface-hover/70 text-text-muted hover:bg-surface-hover"
              } ${day.isToday ? "ring-2 ring-accent/25" : ""}`}
            >
              <div
                className={`flex gap-2 ${compact ? "h-full flex-col items-center justify-center text-center" : "items-start justify-between"}`}
              >
                <span
                  className={`inline-flex h-7 min-w-7 items-center justify-center rounded-full px-1 text-sm font-bold ${day.isToday ? "bg-accent text-white" : selected ? "bg-white text-accent" : "text-text-primary"}`}
                >
                  {dayNumber(day.date)}
                </span>
                {compact ? (
                  <div className="h-2.5" />
                ) : (
                  <>
                    {day.eventCount >= 4 && (
                      <span className="text-[10px] font-bold text-text-muted">
                        +{day.eventCount - 3}
                      </span>
                    )}
                  </>
                )}
              </div>

              {!compact && (
                <>
                  <div className="mt-2 flex items-center gap-1">
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${dotTone(day)}`}
                    />
                    <span className="text-[10px] text-text-muted">
                      {day.eventCount > 0
                        ? `${day.eventCount} ${t("calendar.eventsUnit")}`
                        : t("calendar.noEventsShort")}
                    </span>
                  </div>

                  {day.topEvents.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {day.topEvents.slice(0, 2).map((event) => (
                        <div
                          key={event.id}
                          className="truncate text-[11px] font-medium text-text-secondary"
                        >
                          {event.shortName ?? event.displayName}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
