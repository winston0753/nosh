/**
 * Auth hook — keeps a local-dev adapter behind a clean interface.
 *
 * In local dev (no Supabase credentials), the "token" is just a UUID
 * stored in SecureStore. In production this swaps to Supabase session.
 */

import * as SecureStore from 'expo-secure-store';
import { useCallback, useEffect, useState } from 'react';
import { NoshClient } from '../api/client';

const DEV_TOKEN_KEY = 'nosh_dev_token';

interface AuthState {
  token: string | null;
  isLoading: boolean;
  client: NoshClient | null;
  signIn: (token: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthState {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    SecureStore.getItemAsync(DEV_TOKEN_KEY).then((stored) => {
      setToken(stored);
      setIsLoading(false);
    });
  }, []);

  const signIn = useCallback(async (newToken: string) => {
    await SecureStore.setItemAsync(DEV_TOKEN_KEY, newToken);
    setToken(newToken);
  }, []);

  const signOut = useCallback(async () => {
    await SecureStore.deleteItemAsync(DEV_TOKEN_KEY);
    setToken(null);
  }, []);

  const client = token ? new NoshClient(token) : null;

  return { token, isLoading, client, signIn, signOut };
}
