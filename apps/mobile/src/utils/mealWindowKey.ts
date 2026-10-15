/**
 * Deterministic meal-window key derivation.
 *
 * Key format: YYYY-MM-DD#meal_type
 *   - YYYY-MM-DD is the calendar date in the context's IANA time zone
 *   - meal_type is the context's configured meal type
 *
 * mealWindowKey() returns null when:
 *   - today is not in active_days
 *   - the current local time is outside the configured window
 *   - the time zone is invalid/unrecognised
 *
 * active_days convention (matches the server schema comment):
 *   0 = Monday, 1 = Tuesday, … 6 = Sunday
 * This is Python's datetime.weekday() convention, NOT JavaScript's
 * Date.getDay() (which is 0=Sunday).  Use localWeekdayInZone() which
 * converts for you.
 *
 * Overnight windows (local_window_end <= local_window_start in total
 * minutes) are rejected — return null.  The server validates this on
 * context creation.
 */

import type { Context } from '../api/types';

// ---------------------------------------------------------------------------
// Low-level locale-agnostic helpers
// ---------------------------------------------------------------------------

/**
 * Return the calendar date string (YYYY-MM-DD) for `now` in `timeZone`.
 * Returns null when `timeZone` is not a recognised IANA zone.
 */
export function localDateInZone(now: Date, timeZone: string): string | null {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(now);
    const year = parts.find((p) => p.type === 'year')?.value ?? '';
    const month = parts.find((p) => p.type === 'month')?.value ?? '';
    const day = parts.find((p) => p.type === 'day')?.value ?? '';
    if (!year || !month || !day) return null;
    return `${year}-${month}-${day}`;
  } catch {
    return null;
  }
}

/**
 * Return the local hour (0–23) and minute (0–59) for `now` in `timeZone`.
 * Returns null when `timeZone` is not recognised.
 */
export function localTimeInZone(now: Date, timeZone: string): { hour: number; minute: number } | null {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone,
      hour: 'numeric',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(now);
    const rawH = parseInt(parts.find((p) => p.type === 'hour')?.value ?? '-1', 10);
    const rawM = parseInt(parts.find((p) => p.type === 'minute')?.value ?? '-1', 10);
    if (rawH < 0 || rawM < 0) return null;
    // Intl with hour12:false on some platforms returns 24 for midnight; normalise.
    return { hour: rawH === 24 ? 0 : rawH, minute: rawM };
  } catch {
    return null;
  }
}

/**
 * Return the API weekday (0=Mon … 6=Sun) for `now` in `timeZone`.
 * Returns null when `timeZone` is not recognised.
 *
 * JavaScript Date.getDay() returns 0=Sunday, so we convert:
 *   API weekday = (JS weekday + 6) % 7
 */
export function localWeekdayInZone(now: Date, timeZone: string): number | null {
  try {
    // Use a locale-neutral narrow weekday abbreviation (Mon/Tue/…/Sun).
    // We create a temporary date formatter with a known Sunday (1970-01-04) to
    // build an index, then compare against today.
    const fmt = new Intl.DateTimeFormat('en-US', { timeZone, weekday: 'short' });
    // Build canonical map: abbreviated name → JS weekday index.
    const SUNDAY_EPOCH = new Date('1970-01-04T12:00:00Z'); // confirmed Sunday
    const dayNames: string[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(SUNDAY_EPOCH.getTime() + i * 86_400_000);
      dayNames.push(fmt.format(d).toLowerCase().slice(0, 3));
    }
    // dayNames[0] = 'sun', dayNames[1] = 'mon', …, dayNames[6] = 'sat'
    const todayName = fmt.format(now).toLowerCase().slice(0, 3);
    const jsDow = dayNames.indexOf(todayName); // 0=Sun … 6=Sat
    if (jsDow < 0) return null;
    return (jsDow + 6) % 7; // 0=Mon … 6=Sun
  } catch {
    return null;
  }
}

/** Parse "HH:MM" into total minutes from midnight.  Returns null on bad input. */
export function parseWindowMinutes(hhmm: string): number | null {
  const match = /^(\d{1,2}):(\d{2})$/.exec(hhmm);
  if (!match) return null;
  const h = parseInt(match[1], 10);
  const m = parseInt(match[2], 10);
  if (h > 23 || m > 59) return null;
  return h * 60 + m;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

type ContextWindow = Pick<
  Context,
  'meal_type' | 'local_window_start' | 'local_window_end' | 'time_zone' | 'active_days'
>;

/**
 * Determine whether a meal window is active at `now` for the given context.
 *
 * Returns the meal_type string when:
 *   - `timeZone` is a valid IANA zone,
 *   - today's API weekday is in `active_days`,
 *   - `now` falls in [startMinutes, endMinutes), and
 *   - the window is not overnight (end > start in minutes).
 *
 * Returns null in all other cases.
 */
export function activeMealType(context: ContextWindow, now: Date): string | null {
  const zone = context.time_zone;

  const startMin = parseWindowMinutes(context.local_window_start);
  const endMin = parseWindowMinutes(context.local_window_end);
  if (startMin === null || endMin === null) return null;

  // Reject overnight windows (server-side validation should prevent these).
  if (endMin <= startMin) return null;

  const weekday = localWeekdayInZone(now, zone);
  if (weekday === null) return null;
  if (!context.active_days.includes(weekday)) return null;

  const time = localTimeInZone(now, zone);
  if (time === null) return null;
  const nowMin = time.hour * 60 + time.minute;

  if (nowMin >= startMin && nowMin < endMin) return context.meal_type;
  return null;
}

/**
 * Build the meal-window key for the given context and timestamp.
 *
 * Returns null when no window is currently active (outside hours, wrong day,
 * or invalid time zone).  Callers must not create a suggestion session when
 * this returns null.
 *
 * @param context The active dining context.
 * @param now     The current instant.  Defaults to `new Date()` in production;
 *                pass explicitly for deterministic testing.
 */
export function mealWindowKey(context: ContextWindow, now: Date = new Date()): string | null {
  const meal = activeMealType(context, now);
  if (meal === null) return null;

  const date = localDateInZone(now, context.time_zone);
  if (date === null) return null;

  return `${date}#${meal}`;
}
