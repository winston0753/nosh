/**
 * chunkedSecureStorage: values larger than one SecureStore entry round-trip,
 * shrinking a value removes stale chunks, and partial writes read as absent.
 */

import { CHUNK_SIZE, chunkedSecureStorage } from '../auth/secureStorage';

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

beforeEach(() => mockStore.clear());

const KEY = 'sb-project-auth-token';

test('missing key reads as null', async () => {
  expect(await chunkedSecureStorage.getItem(KEY)).toBeNull();
});

test('a small value round-trips in one chunk', async () => {
  await chunkedSecureStorage.setItem(KEY, '{"a":1}');
  expect(await chunkedSecureStorage.getItem(KEY)).toBe('{"a":1}');
  expect(mockStore.get(`${KEY}.n`)).toBe('1');
});

test('a value larger than one entry is split and reassembled', async () => {
  const value = 'x'.repeat(CHUNK_SIZE * 2 + 17);
  await chunkedSecureStorage.setItem(KEY, value);
  expect(mockStore.get(`${KEY}.n`)).toBe('3');
  for (let i = 0; i < 3; i++) {
    expect(mockStore.get(`${KEY}.${i}`)!.length).toBeLessThanOrEqual(CHUNK_SIZE);
  }
  expect(await chunkedSecureStorage.getItem(KEY)).toBe(value);
});

test('overwriting with a shorter value deletes stale chunks', async () => {
  await chunkedSecureStorage.setItem(KEY, 'y'.repeat(CHUNK_SIZE * 3));
  await chunkedSecureStorage.setItem(KEY, 'short');
  expect(await chunkedSecureStorage.getItem(KEY)).toBe('short');
  expect(mockStore.has(`${KEY}.1`)).toBe(false);
  expect(mockStore.has(`${KEY}.2`)).toBe(false);
});

test('removeItem deletes every chunk and the count', async () => {
  await chunkedSecureStorage.setItem(KEY, 'z'.repeat(CHUNK_SIZE + 1));
  await chunkedSecureStorage.removeItem(KEY);
  expect(mockStore.size).toBe(0);
  expect(await chunkedSecureStorage.getItem(KEY)).toBeNull();
});

test('a missing chunk (partial write) reads as null', async () => {
  await chunkedSecureStorage.setItem(KEY, 'w'.repeat(CHUNK_SIZE + 1));
  mockStore.delete(`${KEY}.1`);
  expect(await chunkedSecureStorage.getItem(KEY)).toBeNull();
});
