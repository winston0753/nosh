/**
 * AuthProvider: one session owner, per-user cache isolation, and both modes.
 *
 * Covers:
 *  - a stored Supabase session restores to signed-in
 *  - the API client sends the *current* access token (refreshes are picked up)
 *  - an account switch clears cached data from the previous user
 *  - sign-out ends the local session, clears the cache, and drops the client
 *  - email-code verification normalizes the email and signs in
 *  - send-code errors propagate to the screen
 *  - local-dev mode stores the UUID token and signs out cleanly
 */

import type { SupabaseClient } from '@supabase/supabase-js';
import { notifyManager, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useEffect } from 'react';
import { act, create, type ReactTestRenderer } from 'react-test-renderer';
import { NoshClient } from '../api/client';
import { AuthProvider, useAuth, type AuthContextValue } from '../auth/AuthProvider';
import { userKey } from '../auth/queryKeys';

jest.mock('../auth/supabase', () => ({ supabase: null }));

const mockStore = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async (key: string) => mockStore.get(key) ?? null),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockStore.set(key, value);
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    mockStore.delete(key);
  }),
}));

type Session = { user: { id: string }; access_token: string } | null;
type Listener = (event: string, session: Session) => void;

function fakeSupabase(initial: Session) {
  let session = initial;
  const listeners: Listener[] = [];
  const auth = {
    getSession: jest.fn(async () => ({ data: { session }, error: null })),
    onAuthStateChange: jest.fn((listener: Listener) => {
      listeners.push(listener);
      return { data: { subscription: { unsubscribe: jest.fn() } } };
    }),
    signInWithOtp: jest.fn(async (_args: unknown) => ({ data: {}, error: null as unknown })),
    verifyOtp: jest.fn(async (_args: unknown) => ({ data: { session }, error: null })),
    signOut: jest.fn(async (_args: unknown) => {
      session = null;
      return { error: null };
    }),
  };
  return {
    client: { auth } as unknown as SupabaseClient,
    auth,
    setSession(next: Session) {
      session = next;
      listeners.forEach((listener) => listener(next ? 'SIGNED_IN' : 'SIGNED_OUT', next));
    },
  };
}

const sessionFor = (id: string, token = `token-${id}`) => ({
  user: { id },
  access_token: token,
});

let latest: AuthContextValue;
function Probe({ onValue }: { onValue: (value: AuthContextValue) => void }) {
  const value = useAuth();
  useEffect(() => onValue(value));
  return null;
}

let renderer: ReactTestRenderer | undefined;

async function mount(supabase: SupabaseClient | null, queryClient = new QueryClient()) {
  await act(async () => {
    renderer = create(
      <QueryClientProvider client={queryClient}>
        <AuthProvider supabase={supabase}>
          <Probe
            onValue={(value) => {
              latest = value;
            }}
          />
        </AuthProvider>
      </QueryClientProvider>,
    );
  });
  return queryClient;
}

beforeAll(() => {
  notifyManager.setScheduler((cb) => cb());
});

beforeEach(() => {
  mockStore.clear();
  globalThis.fetch = jest.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => [],
  })) as unknown as typeof fetch;
});

afterEach(async () => {
  await act(async () => renderer?.unmount());
  renderer = undefined;
});

test('a stored Supabase session restores to signed-in', async () => {
  const fake = fakeSupabase(sessionFor('user-a'));
  await mount(fake.client);
  expect(latest.mode).toBe('supabase');
  expect(latest.status).toBe('signed-in');
  expect(latest.userId).toBe('user-a');
  expect(latest.client).toBeInstanceOf(NoshClient);
});

test('no stored session is signed-out with no API client', async () => {
  const fake = fakeSupabase(null);
  await mount(fake.client);
  expect(latest.status).toBe('signed-out');
  expect(latest.client).toBeNull();
});

test('the API client sends the current access token after a refresh', async () => {
  const fake = fakeSupabase(sessionFor('user-a', 'first'));
  await mount(fake.client);
  const client = latest.client!;
  await client.listContexts();
  // Refresh: same user, new token. The existing client must pick it up.
  await act(async () => fake.setSession(sessionFor('user-a', 'second')));
  await client.listContexts();
  const auths = (globalThis.fetch as jest.Mock).mock.calls.map(
    ([, init]) => (init as RequestInit & { headers: Record<string, string> }).headers.Authorization,
  );
  expect(auths).toEqual(['Bearer first', 'Bearer second']);
});

test('switching accounts clears the previous user’s cached data', async () => {
  const fake = fakeSupabase(sessionFor('user-a'));
  const queryClient = await mount(fake.client);
  queryClient.setQueryData(userKey('user-a', 'visits'), [{ id: 'visit-a' }]);

  await act(async () => fake.setSession(sessionFor('user-b')));

  expect(latest.userId).toBe('user-b');
  expect(queryClient.getQueryData(userKey('user-a', 'visits'))).toBeUndefined();
  expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
});

test('sign-out ends the local session, clears the cache, and drops the client', async () => {
  const fake = fakeSupabase(sessionFor('user-a'));
  const queryClient = await mount(fake.client);
  queryClient.setQueryData(userKey('user-a', 'progress'), [{ month: '2026-10' }]);

  await act(async () => latest.signOut());

  expect(fake.auth.signOut).toHaveBeenCalledWith({ scope: 'local' });
  expect(latest.status).toBe('signed-out');
  expect(latest.client).toBeNull();
  expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
});

test('verifying an email code normalizes the email and signs in', async () => {
  const fake = fakeSupabase(null);
  await mount(fake.client);
  fake.auth.verifyOtp.mockResolvedValueOnce({
    data: { session: sessionFor('user-c') },
    error: null,
  });

  await act(async () => latest.verifyEmailCode('  Person@Example.COM ', ' 123456 '));

  expect(fake.auth.verifyOtp).toHaveBeenCalledWith({
    email: 'person@example.com',
    token: '123456',
    type: 'email',
  });
  expect(latest.status).toBe('signed-in');
  expect(latest.userId).toBe('user-c');
});

test('a send-code error propagates to the caller', async () => {
  const fake = fakeSupabase(null);
  await mount(fake.client);
  const rateLimited = Object.assign(new Error('rate limited'), { status: 429 });
  fake.auth.signInWithOtp.mockResolvedValueOnce({ data: {}, error: rateLimited });

  await expect(latest.requestEmailCode('person@example.com')).rejects.toBe(rateLimited);
  expect(fake.auth.signInWithOtp).toHaveBeenCalledWith({
    email: 'person@example.com',
    options: { shouldCreateUser: true },
  });
});

test('local-dev mode stores the UUID token and signs out cleanly', async () => {
  await mount(null);
  expect(latest.mode).toBe('local-dev');
  expect(latest.status).toBe('signed-out');

  const id = '00000000-0000-0000-0000-000000000001';
  await act(async () => latest.signInLocal(` ${id} `));
  expect(latest.userId).toBe(id);
  expect(mockStore.get('nosh_dev_token')).toBe(id);

  await latest.client!.listContexts();
  const init = (globalThis.fetch as jest.Mock).mock.calls[0][1] as RequestInit & {
    headers: Record<string, string>;
  };
  expect(init.headers.Authorization).toBe(`Bearer ${id}`);

  await act(async () => latest.signOut());
  expect(latest.status).toBe('signed-out');
  expect(mockStore.has('nosh_dev_token')).toBe(false);
});

test('the API client refuses to send a request without a token', async () => {
  const client = new NoshClient(async () => null);
  await expect(client.listContexts()).rejects.toMatchObject({
    code: 'unauthenticated',
    status: 401,
  });
  expect(globalThis.fetch).not.toHaveBeenCalled();
});
