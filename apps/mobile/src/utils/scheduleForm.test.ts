/**
 * Meal-schedule survey: defaults (weekday lunch on, dinner off), validation
 * mirroring the API (strict HH:MM, end after start, days, no overlap), and
 * the full-replacement PUT body.
 */

import type { MealSchedule } from '../api/types';
import {
  defaultScheduleForm,
  scheduleFormFrom,
  toScheduleUpdate,
  validateScheduleForm,
  type ScheduleForm,
} from './scheduleForm';

function form(patch: (f: ScheduleForm) => void): ScheduleForm {
  const f = defaultScheduleForm();
  patch(f);
  return f;
}

test('defaults to weekday lunch with dinner off', () => {
  const f = defaultScheduleForm();
  expect(f.lunch).toMatchObject({ enabled: true, days: [0, 1, 2, 3, 4] });
  expect(f.dinner.enabled).toBe(false);
  expect(validateScheduleForm(f)).toBeNull();
});

test.each([
  ['no meal on', (f: ScheduleForm) => (f.lunch.enabled = false), 'Turn on lunch or dinner.'],
  ['loose time', (f: ScheduleForm) => (f.lunch.start = '9:00'), 'Lunch times must look like 12:30 (24-hour).'],
  ['impossible time', (f: ScheduleForm) => (f.dinner.end = '24:00'), 'Dinner times must look like 12:30 (24-hour).'],
  ['ends before start', (f: ScheduleForm) => (f.lunch.end = '11:00'), 'Lunch must end after it starts.'],
  ['no days', (f: ScheduleForm) => (f.lunch.days = []), 'Pick at least one day for lunch.'],
])('rejects %s', (_name, patch, message) => {
  expect(validateScheduleForm(form(patch))).toBe(message);
});

test('rejects overlapping meals that share a day, allows them on different days', () => {
  const overlapping = form((f) => {
    f.dinner.enabled = true;
    f.dinner.start = '13:00';
  });
  expect(validateScheduleForm(overlapping)).toBe('Lunch and dinner times overlap.');

  overlapping.dinner.days = [5, 6];
  expect(validateScheduleForm(overlapping)).toBeNull();
});

test('a disabled meal with no days still saves with weekday fallback', () => {
  const f = form((x) => (x.dinner.days = []));
  expect(validateScheduleForm(f)).toBeNull();
  const body = toScheduleUpdate(f, 'America/Los_Angeles');
  expect(body).toEqual({
    time_zone: 'America/Los_Angeles',
    meals: [
      {
        meal_type: 'lunch',
        enabled: true,
        local_window_start: '11:30',
        local_window_end: '13:30',
        active_days: [0, 1, 2, 3, 4],
        price_ceiling: 2,
      },
      {
        meal_type: 'dinner',
        enabled: false,
        local_window_start: '17:30',
        local_window_end: '20:30',
        active_days: [0, 1, 2, 3, 4],
        price_ceiling: 3,
      },
    ],
  });
});

test('prefills from the stored schedule and sorts days', () => {
  const stored: MealSchedule = {
    meals: [
      {
        meal_type: 'dinner',
        enabled: true,
        local_window_start: '18:00',
        local_window_end: '21:00',
        time_zone: 'America/New_York',
        active_days: [6, 4, 5],
        price_ceiling: null,
        notifications_enabled: true,
        version: 3,
        updated_at: '2026-10-20T00:00:00Z',
      },
    ],
  };
  const f = scheduleFormFrom(stored);
  expect(f.dinner).toEqual({
    enabled: true,
    start: '18:00',
    end: '21:00',
    days: [4, 5, 6],
    priceCeiling: null,
  });
  expect(f.lunch).toEqual(defaultScheduleForm().lunch);
});
