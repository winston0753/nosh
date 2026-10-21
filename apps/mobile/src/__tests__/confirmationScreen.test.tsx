/**
 * Visit confirmation screen: honest save states and duplicate-safe retry.
 *
 * Covers:
 *  - pending feedback while createVisit runs; "Thanks" only after success
 *  - failure keeps the chosen rating and offers retry; no "Thanks"
 *  - retry re-sends the identical frozen request (same proposal_id and visited_at)
 *  - a retry after an ambiguous failure (server committed, response lost)
 *    returns the existing visit and never creates a duplicate
 *  - double taps while saving send one request
 *  - an incomplete link (no proposal) never writes
 */

import { notifyManager, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { Text } from 'react-native';
import { act, create, type ReactTestRenderer } from 'react-test-renderer';
import type { Visit, VisitCreate } from '../api/types';
import ConfirmationScreen from '../../app/confirmation/[sessionId]';
import { buildVisitRequest } from '../hooks/useVisitConfirmation';

const mockParams = jest.fn();
const mockClient = { createVisit: jest.fn<Promise<Visit>, [VisitCreate]>() };

jest.mock('expo-router', () => ({
  router: { replace: jest.fn(), back: jest.fn() },
  useLocalSearchParams: () => mockParams(),
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ client: mockClient }),
}));

const PARAMS = {
  sessionId: 'session-1',
  proposalId: 'proposal-1',
  placeId: 'place-1',
  placeName: 'Taqueria Uno',
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function visitFor(body: VisitCreate, id = 'visit-1'): Visit {
  return {
    id,
    place_id: body.place_id,
    place_name: PARAMS.placeName,
    proposal_id: body.proposal_id ?? null,
    visited_at: body.visited_at,
    rating: body.rating,
    confirmation_source: 'app_confirmation',
    created_at: body.visited_at,
    corrected_at: null,
  };
}

/** A fake API that, like the server, keeps one visit per (user, proposal). */
function fakeServer() {
  const visits = new Map<string, Visit>();
  return {
    visits,
    commit(body: VisitCreate): Visit {
      const key = body.proposal_id ?? `manual-${visits.size}`;
      const existing = visits.get(key);
      if (existing) return existing;
      const created = visitFor(body, `visit-${visits.size + 1}`);
      visits.set(key, created);
      return created;
    },
  };
}

// Deliver TanStack Query state changes synchronously inside act() instead of
// on a setTimeout(0) tick, so assertions see each phase deterministically.
notifyManager.setScheduler((callback) => callback());

let renderer: ReactTestRenderer;

async function render() {
  // gcTime: Infinity schedules no garbage-collection timers that would keep
  // Jest alive after the suite finishes.
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false, gcTime: Infinity },
    },
  });
  await act(async () => {
    renderer = create(
      <QueryClientProvider client={queryClient}>
        <ConfirmationScreen />
      </QueryClientProvider>,
    );
  });
}

function screenText(): string {
  return renderer.root
    .findAllByType(Text)
    .map((node) => {
      const children = node.props.children as unknown;
      return Array.isArray(children) ? children.join('') : String(children);
    })
    .join(' | ');
}

async function press(testID: string) {
  const target = renderer.root.find(
    (node) => node.props.testID === testID && typeof node.props.onPress === 'function',
  );
  await act(async () => {
    target.props.onPress?.();
  });
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

async function chooseRating(rating: 'positive' | 'negative') {
  await press('confirm-yes');
  await press(rating === 'positive' ? 'rate-positive' : 'rate-negative');
}

beforeEach(() => {
  mockParams.mockReturnValue(PARAMS);
  mockClient.createVisit.mockReset();
});

afterEach(() => {
  jest.useRealTimers();
  act(() => renderer?.unmount());
});

test('buildVisitRequest ties the visit to its proposal', () => {
  const now = new Date('2026-10-12T19:00:00Z');
  expect(buildVisitRequest('place-1', 'proposal-1', 'positive', now)).toEqual({
    place_id: 'place-1',
    proposal_id: 'proposal-1',
    visited_at: '2026-10-12T19:00:00.000Z',
    rating: 'positive',
    confirmation_source: 'app_confirmation',
  });
});

test('shows pending feedback, then Thanks only after the server succeeds', async () => {
  const pending = deferred<Visit>();
  mockClient.createVisit.mockReturnValueOnce(pending.promise);
  await render();
  await chooseRating('positive');

  expect(screenText()).toContain('Saving your visit…');
  expect(screenText()).not.toContain('Thanks!');
  expect(mockClient.createVisit).toHaveBeenCalledTimes(1);
  const body = mockClient.createVisit.mock.calls[0][0];
  expect(body).toMatchObject({ place_id: 'place-1', proposal_id: 'proposal-1', rating: 'positive' });

  await act(async () => {
    pending.resolve(visitFor(body));
  });
  expect(screenText()).toContain('Thanks!');
  expect(screenText()).toContain('Great pick');
});

test('failure keeps the rating, offers retry, and never shows Thanks', async () => {
  mockClient.createVisit.mockRejectedValueOnce(new Error('Network request failed'));
  await render();
  await chooseRating('negative');
  await flush();

  const text = screenText();
  expect(text).toContain("Couldn't save your visit");
  expect(text).toContain('Not great');
  expect(text).not.toContain('Thanks!');
  expect(renderer.root.findAll((n) => n.props.testID === 'confirm-retry').length).toBeGreaterThan(0);
});

test('retry re-sends the identical request and then succeeds', async () => {
  jest.useFakeTimers({ now: new Date('2026-10-12T19:00:00Z') });
  mockClient.createVisit
    .mockRejectedValueOnce(new Error('Network request failed'))
    .mockImplementationOnce(async (body) => visitFor(body));
  await render();
  await chooseRating('positive');
  await flush();
  expect(screenText()).toContain("Couldn't save your visit");

  // Time passes before the user retries; the request must not change.
  jest.setSystemTime(new Date('2026-10-12T19:45:00Z'));
  await press('confirm-retry');
  await flush();

  expect(mockClient.createVisit).toHaveBeenCalledTimes(2);
  const [first, second] = mockClient.createVisit.mock.calls.map((call) => call[0]);
  expect(second).toEqual(first);
  expect(second.visited_at).toBe('2026-10-12T19:00:00.000Z');
  expect(screenText()).toContain('Thanks!');
});

test('retry after an ambiguous failure is duplicate-safe', async () => {
  const server = fakeServer();
  // First attempt: the server commits but the response is lost (timeout).
  mockClient.createVisit
    .mockImplementationOnce(async (body) => {
      server.commit(body);
      throw new Error('The request timed out');
    })
    .mockImplementationOnce(async (body) => server.commit(body));
  await render();
  await chooseRating('positive');
  await flush();
  expect(screenText()).toContain("Couldn't save your visit");

  await press('confirm-retry');
  await flush();

  expect(server.visits.size).toBe(1);
  const [first, second] = mockClient.createVisit.mock.calls.map((call) => call[0]);
  expect(second).toEqual(first);
  expect(screenText()).toContain('Thanks!');
});

test('double taps while saving send a single request', async () => {
  const pending = deferred<Visit>();
  mockClient.createVisit.mockReturnValue(pending.promise);
  await render();
  await press('confirm-yes');

  const positive = renderer.root.find(
    (node) => node.props.testID === 'rate-positive' && typeof node.props.onPress === 'function',
  );
  await act(async () => {
    positive.props.onPress?.();
    positive.props.onPress?.();
  });
  expect(mockClient.createVisit).toHaveBeenCalledTimes(1);

  await act(async () => {
    pending.resolve(visitFor(mockClient.createVisit.mock.calls[0][0]));
  });
  expect(screenText()).toContain('Thanks!');
});

test('an incomplete link without a proposal never writes a visit', async () => {
  mockParams.mockReturnValue({ ...PARAMS, proposalId: undefined });
  await render();
  expect(screenText()).toContain("Can't confirm this visit");
  expect(renderer.root.findAll((n) => n.props.testID === 'rate-positive')).toHaveLength(0);
  expect(mockClient.createVisit).not.toHaveBeenCalled();
});
