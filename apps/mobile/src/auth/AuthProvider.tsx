/**
 * The app's single owner of the signed-in session.
 *
 * Every screen reads the same state through `useAuth()`.  Whenever the
 * signed-in user changes (sign-in, sign-out, account switch) in-flight
 * queries are cancelled and the whole query cache is cleared, and query keys
 * are scoped by user ID (see `userKey` in ./queryKeys), so one account's data can never be
 * shown to another.
 *
 * Modes (see ./config): Supabase passwordless email codes, or the local-dev
 * UUID adapter that matches the API's AUTH_LOCAL_DEV=true mode.
 */

import type { SupabaseClient } from '@supabase/supabase-js';
import { useQueryClient } from '@tanstack/react-query';
import * as SecureStore from 'expo-secure-store';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { NoshClient } from '../api/client';
import type { AuthMode } from './config';
import { supabase as defaultSupabase } from './supabase';

const DEV_TOKEN_KEY = 'nosh_dev_token';

export type AuthStatus = 'loading' | 'signed-out' | 'signed-in';

export interface AuthContextValue {
  mode: AuthMode;
  status: AuthStatus;
  userId: string | null;
  client: NoshClient | null;
  /** Supabase mode: email a one-time sign-in code. */
  requestEmailCode: (email: string) => Promise<void>;
  /** Supabase mode: exchange the emailed code for a session. */
  verifyEmailCode: (email: string, code: string) => Promise<void>;
  /** Local-dev mode: sign in as the given user UUID. */
  signInLocal: (userId: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

interface Props {
  children: ReactNode;
  /** Injected in tests; defaults to the app's client (null in local-dev mode). */
  supabase?: SupabaseClient | null;
}

export function AuthProvider({ children, supabase = defaultSupabase }: Props) {
  const queryClient = useQueryClient();
  const mode: AuthMode = supabase ? 'supabase' : 'local-dev';
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [userId, setUserId] = useState<string | null>(null);

  const applyUser = useCallback((id: string | null) => {
    setUserId(id);
    setStatus(id ? 'signed-in' : 'signed-out');
  }, []);

  // Restore the stored session and follow later auth events.
  useEffect(() => {
    let active = true;
    if (supabase) {
      supabase.auth.getSession().then(({ data }) => {
        if (active) applyUser(data.session?.user.id ?? null);
      });
      const { data } = supabase.auth.onAuthStateChange((_event, session) => {
        if (active) applyUser(session?.user.id ?? null);
      });
      return () => {
        active = false;
        data.subscription.unsubscribe();
      };
    }
    SecureStore.getItemAsync(DEV_TOKEN_KEY).then((stored) => {
      if (active) applyUser(stored);
    });
    return () => {
      active = false;
    };
  }, [supabase, applyUser]);

  // Drop every cached query whenever the signed-in user changes.
  const previousUserId = useRef<string | null>(null);
  useEffect(() => {
    if (status === 'loading') return;
    if (previousUserId.current !== userId) {
      void queryClient.cancelQueries();
      queryClient.clear();
      previousUserId.current = userId;
    }
  }, [status, userId, queryClient]);

  const client = useMemo(() => {
    if (!userId) return null;
    if (supabase) {
      return new NoshClient(async () => {
        const { data } = await supabase.auth.getSession();
        return data.session?.access_token ?? null;
      });
    }
    return new NoshClient(userId);
  }, [supabase, userId]);

  const requestEmailCode = useCallback(
    async (email: string) => {
      if (!supabase) throw new Error('Email sign-in is not configured.');
      const { error } = await supabase.auth.signInWithOtp({
        email: normalizeEmail(email),
        options: { shouldCreateUser: true },
      });
      if (error) throw error;
    },
    [supabase],
  );

  const verifyEmailCode = useCallback(
    async (email: string, code: string) => {
      if (!supabase) throw new Error('Email sign-in is not configured.');
      const { data, error } = await supabase.auth.verifyOtp({
        email: normalizeEmail(email),
        token: code.trim(),
        type: 'email',
      });
      if (error) throw error;
      applyUser(data.session?.user.id ?? null);
    },
    [supabase, applyUser],
  );

  const signInLocal = useCallback(
    async (id: string) => {
      if (supabase) throw new Error('Local sign-in is disabled when Supabase is configured.');
      const trimmed = id.trim();
      await SecureStore.setItemAsync(DEV_TOKEN_KEY, trimmed);
      applyUser(trimmed);
    },
    [supabase, applyUser],
  );

  const signOut = useCallback(async () => {
    if (supabase) {
      // Local scope: end this device's session even if the network is down.
      await supabase.auth.signOut({ scope: 'local' });
    } else {
      await SecureStore.deleteItemAsync(DEV_TOKEN_KEY);
    }
    applyUser(null);
  }, [supabase, applyUser]);

  const value = useMemo<AuthContextValue>(
    () => ({
      mode,
      status,
      userId,
      client,
      requestEmailCode,
      verifyEmailCode,
      signInLocal,
      signOut,
    }),
    [mode, status, userId, client, requestEmailCode, verifyEmailCode, signInLocal, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>.');
  return value;
}
