/**
 * Unit tests for mealWindowKey utility.
 * Run: npm test -- --runInBand
 *
 * Covers:
 *  - date derivation using context time zone, not device time zone
 *  - both sides of the midnight UTC boundary
 *  - DST spring-forward and fall-back
 *  - minute precision inside the window
 *  - active_days gating (0=Mon…6=Sun API convention)
 *  - exact window open/close times
 *  - brunch meal type
 *  - invalid IANA time zone returns null
 *  - overnight window (end <= start) returns null
 *  - mealWindowKey returns null outside active window
 */

import {
  activeMealType,
  localDateInZone,
  localTimeInZone,
  localWeekdayInZone,
  mealWindowKey,
  parseWindowMinutes,
} from './mealWindowKey';
import type { Context } from '../api/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ctx(overrides: Partial<Context> = {}): Pick<
  Context,
  'meal_type' | 'local_window_start' | 'local_window_end' | 'time_zone' | 'active_days'
> {
  return {
    meal_type: 'dinner',
    local_window_start: '18:00',
    local_window_end: '21:00',
    time_zone: 'America/Los_Angeles',
    active_days: [0, 1, 2, 3, 4, 5, 6], // every day
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// parseWindowMinutes
// ---------------------------------------------------------------------------

describe('parseWindowMinutes', () => {
  test('18:00 → 1080', () => expect(parseWindowMinutes('18:00')).toBe(1080));
  test('00:00 → 0', () => expect(parseWindowMinutes('00:00')).toBe(0));
  test('23:59 → 1439', () => expect(parseWindowMinutes('23:59')).toBe(1439));
  test('bad input returns null', () => expect(parseWindowMinutes('25:00')).toBeNull());
  test('missing colon returns null', () => expect(parseWindowMinutes('1800')).toBeNull());
});

// ---------------------------------------------------------------------------
// localDateInZone
// ---------------------------------------------------------------------------

describe('localDateInZone', () => {
  test('returns null for an invalid time zone', () => {
    const now = new Date('2026-10-12T14:00:00.000Z');
    expect(localDateInZone(now, 'Not/ATimeZone')).toBeNull();
  });

  test('returns correct UTC date for UTC zone', () => {
    const now = new Date('2026-10-12T14:00:00.000Z');
    expect(localDateInZone(now, 'UTC')).toBe('2026-10-12');
  });

  // Boundary: one second before LA midnight
  test('2026-10-13T06:59:59Z is still Oct 12 in LA (UTC-7)', () => {
    const now = new Date('2026-10-13T06:59:59.999Z');
    // In PDT (UTC-7): 2026-10-12T23:59:59.999 local
    expect(localDateInZone(now, 'America/Los_Angeles')).toBe('2026-10-12');
  });

  // Boundary: exactly at LA midnight
  test('2026-10-13T07:00:00Z is Oct 13 in LA (UTC-7)', () => {
    const now = new Date('2026-10-13T07:00:00.000Z');
    // In PDT (UTC-7): 2026-10-13T00:00:00 local
    expect(localDateInZone(now, 'America/Los_Angeles')).toBe('2026-10-13');
  });

  // One second after LA midnight
  test('2026-10-13T07:00:01Z is Oct 13 in LA (UTC-7)', () => {
    const now = new Date('2026-10-13T07:00:01.000Z');
    expect(localDateInZone(now, 'America/Los_Angeles')).toBe('2026-10-13');
  });

  test('device TZ (Tokyo) differs from context TZ (LA)', () => {
    // 2026-10-12T23:00:00Z = Oct 13 08:00 JST, but still Oct 12 16:00 PDT
    const now = new Date('2026-10-12T23:00:00.000Z');
    expect(localDateInZone(now, 'America/Los_Angeles')).toBe('2026-10-12');
    expect(localDateInZone(now, 'Asia/Tokyo')).toBe('2026-10-13');
  });

  // DST spring-forward: America/New_York 2026-03-08 02:00 → 03:00
  test('DST spring-forward day: 2026-03-08T07:30Z is still Mar 8 in New York', () => {
    // 07:30Z = 02:30 EST → clock jumped to 03:30 EDT; local date is still Mar 8
    const now = new Date('2026-03-08T07:30:00.000Z');
    expect(localDateInZone(now, 'America/New_York')).toBe('2026-03-08');
  });

  // DST fall-back: America/New_York 2026-11-01 02:00 → 01:00
  test('DST fall-back day: 2025-11-02T06:30Z is Nov 2 in New York', () => {
    // 06:30Z = 01:30 EST (after fall-back); date is still Nov 2
    const now = new Date('2025-11-02T06:30:00.000Z');
    expect(localDateInZone(now, 'America/New_York')).toBe('2025-11-02');
  });
});

// ---------------------------------------------------------------------------
// localTimeInZone
// ---------------------------------------------------------------------------

describe('localTimeInZone', () => {
  test('returns null for an invalid time zone', () => {
    const now = new Date('2026-10-12T14:00:00.000Z');
    expect(localTimeInZone(now, 'Bad/Zone')).toBeNull();
  });

  test('2026-10-12T22:00Z = 15:00 PDT', () => {
    const result = localTimeInZone(new Date('2026-10-12T22:00:00.000Z'), 'America/Los_Angeles');
    expect(result).toEqual({ hour: 15, minute: 0 });
  });

  test('minute precision: 18:30 local', () => {
    // 2026-10-13T01:30:00Z = 18:30 PDT (UTC-7)
    const result = localTimeInZone(new Date('2026-10-13T01:30:00.000Z'), 'America/Los_Angeles');
    expect(result).toEqual({ hour: 18, minute: 30 });
  });
});

// ---------------------------------------------------------------------------
// localWeekdayInZone
// ---------------------------------------------------------------------------

describe('localWeekdayInZone', () => {
  test('returns null for an invalid time zone', () => {
    expect(localWeekdayInZone(new Date(), 'Not/Valid')).toBeNull();
  });

  // 2026-10-12 is a Monday UTC; verify API weekday = 0
  test('2026-10-12 UTC is Monday = API weekday 0', () => {
    // 2026-10-12T12:00Z = still Monday 05:00 PDT
    const now = new Date('2026-10-12T12:00:00.000Z');
    expect(localWeekdayInZone(now, 'America/Los_Angeles')).toBe(0); // Monday
  });

  // Sunday
  test('2026-10-11 UTC is Sunday = API weekday 6', () => {
    const now = new Date('2026-10-11T12:00:00.000Z');
    expect(localWeekdayInZone(now, 'UTC')).toBe(6); // Sunday
  });
});

// ---------------------------------------------------------------------------
// activeMealType
// ---------------------------------------------------------------------------

describe('activeMealType', () => {
  // 2026-10-13T01:00:00Z = Mon 18:00 PDT — exactly at window open
  test('exactly at window start (18:00 local) → inside', () => {
    const now = new Date('2026-10-13T01:00:00.000Z'); // 18:00 PDT
    expect(activeMealType(ctx(), now)).toBe('dinner');
  });

  // One minute before window start → outside
  test('one minute before window start → null', () => {
    const now = new Date('2026-10-13T00:59:00.000Z'); // 17:59 PDT
    expect(activeMealType(ctx(), now)).toBeNull();
  });

  // One minute before window end (20:59) → inside
  test('one minute before window end (20:59 local) → inside', () => {
    const now = new Date('2026-10-13T03:59:00.000Z'); // 20:59 PDT
    expect(activeMealType(ctx(), now)).toBe('dinner');
  });

  // Exactly at window end (21:00) → outside (half-open interval)
  test('exactly at window end (21:00 local) → null', () => {
    const now = new Date('2026-10-13T04:00:00.000Z'); // 21:00 PDT
    expect(activeMealType(ctx(), now)).toBeNull();
  });

  // Inactive day: context only active Mon–Fri (0–4), test on Saturday (5)
  test('inactive day returns null', () => {
    // 2026-10-10 is a Saturday
    const now = new Date('2026-10-10T22:00:00.000Z'); // Sat 15:00 PDT
    const weekendOnly = ctx({ active_days: [0, 1, 2, 3, 4] }); // Mon–Fri only
    expect(activeMealType(weekendOnly, now)).toBeNull();
  });

  // Active day — Sunday (API weekday 6)
  test('active Sunday (weekday 6) returns meal type', () => {
    // 2026-10-12T01:00Z = 2026-10-11T18:00 PDT (UTC-7) — Sunday dinner window
    const nowSun = new Date('2026-10-12T01:00:00.000Z');
    // localWeekdayInZone on 2026-10-12T01:00Z in LA → still Oct 11 (Sun) because…
    // 2026-10-12T01:00Z = 2026-10-11T18:00 PDT (UTC-7)
    const sundayCtx = ctx({ active_days: [6] }); // only Sunday
    expect(activeMealType(sundayCtx, nowSun)).toBe('dinner');
  });

  // Brunch
  test('brunch window, correct time', () => {
    const brunch = ctx({
      meal_type: 'brunch',
      local_window_start: '10:00',
      local_window_end: '13:00',
    });
    // 2026-10-12T17:00Z = 10:00 PDT Monday
    const now = new Date('2026-10-12T17:00:00.000Z');
    expect(activeMealType(brunch, now)).toBe('brunch');
  });

  // Invalid time zone
  test('invalid time zone returns null', () => {
    const now = new Date('2026-10-12T20:00:00.000Z');
    expect(activeMealType(ctx({ time_zone: 'Not/Valid' }), now)).toBeNull();
  });

  // Overnight window: end <= start in minutes → null
  test('overnight window (23:00–02:00) returns null', () => {
    const overnight = ctx({ local_window_start: '23:00', local_window_end: '02:00' });
    const now = new Date('2026-10-13T01:30:00.000Z'); // 18:30 PDT
    expect(activeMealType(overnight, now)).toBeNull();
  });

  // DST spring-forward — LA 2026-03-08 at 19:00 local
  test('DST spring-forward: dinner window still active', () => {
    // 2026-03-09T03:00Z = 2026-03-08T19:00 PDT (after spring-forward at 02:00)
    const now = new Date('2026-03-09T03:00:00.000Z');
    // 2026-03-08 is a Sunday = API weekday 6
    expect(activeMealType(ctx({ active_days: [0, 1, 2, 3, 4, 5, 6] }), now)).toBe('dinner');
  });

  // DST fall-back — LA 2026-11-01 at 19:00 local
  test('DST fall-back: dinner window still active', () => {
    // 2026-11-02T03:00Z = 2026-11-01T19:00 PST (UTC-8, after fall-back)
    const now = new Date('2026-11-02T03:00:00.000Z');
    expect(activeMealType(ctx({ active_days: [0, 1, 2, 3, 4, 5, 6] }), now)).toBe('dinner');
  });
});

// ---------------------------------------------------------------------------
// mealWindowKey
// ---------------------------------------------------------------------------

describe('mealWindowKey', () => {
  test('returns null outside active window', () => {
    // 2026-10-13T00:00Z = 17:00 PDT — before 18:00 dinner window
    const now = new Date('2026-10-13T00:00:00.000Z');
    expect(mealWindowKey(ctx(), now)).toBeNull();
  });

  test('returns YYYY-MM-DD#meal_type inside window', () => {
    // 2026-10-13T02:00Z = 19:00 PDT Monday — inside dinner window
    const now = new Date('2026-10-13T02:00:00.000Z');
    expect(mealWindowKey(ctx(), now)).toBe('2026-10-12#dinner');
  });

  test('returns null for invalid time zone', () => {
    const now = new Date('2026-10-13T02:00:00.000Z');
    expect(mealWindowKey(ctx({ time_zone: 'Bad/Zone' }), now)).toBeNull();
  });

  test('uses context time zone, not device time zone (LA vs Tokyo)', () => {
    // 2026-10-13T02:00Z = LA 19:00 Oct 12 (in window), Tokyo 11:00 Oct 13
    const now = new Date('2026-10-13T02:00:00.000Z');
    const laKey = mealWindowKey(ctx({ time_zone: 'America/Los_Angeles' }), now);
    const tokyoKey = mealWindowKey(
      ctx({ time_zone: 'Asia/Tokyo', local_window_start: '18:00', local_window_end: '21:00' }),
      now,
    );
    expect(laKey).toBe('2026-10-12#dinner'); // Oct 12 in LA
    // Tokyo 11:00 is outside dinner window → null
    expect(tokyoKey).toBeNull();
  });

  test('returns null on inactive weekday', () => {
    // 2026-10-13T02:00Z = Mon Oct 12 PDT. active_days=[1] means Tue only
    const now = new Date('2026-10-13T02:00:00.000Z');
    expect(mealWindowKey(ctx({ active_days: [1] }), now)).toBeNull();
  });

  test('brunch key format', () => {
    const brunch = ctx({
      meal_type: 'brunch',
      local_window_start: '10:00',
      local_window_end: '13:00',
      time_zone: 'UTC',
    });
    const now = new Date('2026-10-12T11:00:00.000Z'); // 11:00 UTC Monday
    expect(mealWindowKey(brunch, now)).toBe('2026-10-12#brunch');
  });
});
