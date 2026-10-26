/**
 * Meal-schedule survey state (D020, D026): defaults, validation that mirrors
 * the API's rules, and conversion to the PUT /v1/me/meal-schedule body.
 *
 * Defaults: weekday lunch on, dinner off (opt-in).
 */

import type {
  MealPlanInput,
  MealSchedule,
  MealScheduleUpdate,
  MealType,
  PriceCeiling,
} from '../api/types';
import { parseWindowMinutes } from './mealWindowKey';

export interface MealForm {
  enabled: boolean;
  start: string; // HH:MM
  end: string; // HH:MM
  days: number[]; // 0=Mon … 6=Sun
  priceCeiling: PriceCeiling | null; // null = no limit
}

export type ScheduleForm = Record<MealType, MealForm>;

export const MEAL_ORDER: readonly MealType[] = ['lunch', 'dinner'];
export const WEEKDAYS = [0, 1, 2, 3, 4];

export function defaultScheduleForm(): ScheduleForm {
  return {
    lunch: { enabled: true, start: '11:30', end: '13:30', days: [...WEEKDAYS], priceCeiling: 2 },
    dinner: { enabled: false, start: '17:30', end: '20:30', days: [...WEEKDAYS], priceCeiling: 3 },
  };
}

/** Prefill from the stored schedule; meals not stored keep their defaults. */
export function scheduleFormFrom(schedule: MealSchedule | undefined): ScheduleForm {
  const form = defaultScheduleForm();
  for (const meal of schedule?.meals ?? []) {
    form[meal.meal_type] = {
      enabled: meal.enabled,
      start: meal.local_window_start,
      end: meal.local_window_end,
      days: [...meal.active_days].sort((a, b) => a - b),
      priceCeiling: meal.price_ceiling,
    };
  }
  return form;
}

const STRICT_HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;

/** Return a user-facing problem with the form, or null when it can be saved. */
export function validateScheduleForm(form: ScheduleForm): string | null {
  if (!MEAL_ORDER.some((m) => form[m].enabled)) {
    return 'Turn on lunch or dinner.';
  }
  for (const m of MEAL_ORDER) {
    const meal = form[m];
    const label = m === 'lunch' ? 'Lunch' : 'Dinner';
    if (!STRICT_HHMM.test(meal.start) || !STRICT_HHMM.test(meal.end)) {
      return `${label} times must look like 12:30 (24-hour).`;
    }
    if (parseWindowMinutes(meal.end)! <= parseWindowMinutes(meal.start)!) {
      return `${label} must end after it starts.`;
    }
    if (meal.enabled && meal.days.length === 0) {
      return `Pick at least one day for ${m}.`;
    }
  }
  const { lunch, dinner } = form;
  if (lunch.enabled && dinner.enabled && lunch.days.some((d) => dinner.days.includes(d))) {
    const overlap =
      parseWindowMinutes(lunch.start)! < parseWindowMinutes(dinner.end)! &&
      parseWindowMinutes(dinner.start)! < parseWindowMinutes(lunch.end)!;
    if (overlap) return 'Lunch and dinner times overlap.';
  }
  return null;
}

/**
 * Build the full-replacement body.  Both meals are always sent so a turned-off
 * meal keeps its times for next time; the API needs a non-empty day list even
 * for a disabled meal, so it falls back to weekdays.
 */
export function toScheduleUpdate(form: ScheduleForm, timeZone: string): MealScheduleUpdate {
  const meals: MealPlanInput[] = MEAL_ORDER.map((m) => ({
    meal_type: m,
    enabled: form[m].enabled,
    local_window_start: form[m].start,
    local_window_end: form[m].end,
    active_days: form[m].days.length > 0 ? [...form[m].days].sort((a, b) => a - b) : WEEKDAYS,
    price_ceiling: form[m].priceCeiling,
  }));
  return { time_zone: timeZone, meals };
}
