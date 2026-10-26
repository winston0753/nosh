/**
 * The app's single Supabase client (null in local-dev mode).
 *
 * Sessions persist in the Keychain via chunkedSecureStorage.  Tokens refresh
 * automatically while the app is in the foreground only, as Supabase
 * recommends for React Native.
 */

import 'react-native-url-polyfill/auto';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { AppState } from 'react-native';
import { supabaseConfig } from './config';
import { chunkedSecureStorage } from './secureStorage';

function create(): SupabaseClient | null {
  if (!supabaseConfig) return null;
  const client = createClient(supabaseConfig.url, supabaseConfig.publishableKey, {
    auth: {
      storage: chunkedSecureStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  });
  AppState.addEventListener('change', (state) => {
    if (state === 'active') {
      client.auth.startAutoRefresh();
    } else {
      client.auth.stopAutoRefresh();
    }
  });
  return client;
}

export const supabase = create();
