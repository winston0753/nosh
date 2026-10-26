/**
 * Keychain-backed storage for the Supabase session.
 *
 * expo-secure-store warns above 2048 bytes per value, and a Supabase session
 * (access token, refresh token, user object) can exceed that.  Values are
 * split into fixed-size chunks stored under `<key>.0`, `<key>.1`, …, with the
 * chunk count under `<key>.n`, so tokens never leave the Keychain.
 */

import * as SecureStore from 'expo-secure-store';

export const CHUNK_SIZE = 1800;

function countKey(key: string): string {
  return `${key}.n`;
}

function chunkKey(key: string, index: number): string {
  return `${key}.${index}`;
}

async function readCount(key: string): Promise<number> {
  const raw = await SecureStore.getItemAsync(countKey(key));
  const count = raw === null ? 0 : Number.parseInt(raw, 10);
  return Number.isFinite(count) && count > 0 ? count : 0;
}

async function deleteChunks(key: string, from: number, to: number): Promise<void> {
  for (let i = from; i < to; i++) {
    await SecureStore.deleteItemAsync(chunkKey(key, i));
  }
}

export const chunkedSecureStorage = {
  async getItem(key: string): Promise<string | null> {
    const count = await readCount(key);
    if (count === 0) return null;
    const parts: string[] = [];
    for (let i = 0; i < count; i++) {
      const part = await SecureStore.getItemAsync(chunkKey(key, i));
      // A missing chunk means a partial write; treat the value as absent.
      if (part === null) return null;
      parts.push(part);
    }
    return parts.join('');
  },

  async setItem(key: string, value: string): Promise<void> {
    const previous = await readCount(key);
    const chunks: string[] = [];
    for (let i = 0; i < value.length; i += CHUNK_SIZE) {
      chunks.push(value.slice(i, i + CHUNK_SIZE));
    }
    if (chunks.length === 0) chunks.push('');
    for (let i = 0; i < chunks.length; i++) {
      await SecureStore.setItemAsync(chunkKey(key, i), chunks[i]);
    }
    await SecureStore.setItemAsync(countKey(key), String(chunks.length));
    await deleteChunks(key, chunks.length, previous);
  },

  async removeItem(key: string): Promise<void> {
    const count = await readCount(key);
    await SecureStore.deleteItemAsync(countKey(key));
    await deleteChunks(key, 0, count);
  },
};
