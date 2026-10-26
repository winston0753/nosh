/**
 * Auth mode, chosen at build time from EXPO_PUBLIC_* variables.
 *
 * - `supabase`: both EXPO_PUBLIC_SUPABASE_URL and
 *   EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY are set.  The API must run with
 *   AUTH_LOCAL_DEV=false and the same SUPABASE_URL.
 * - `local-dev`: neither is set.  The bearer token is a UUID, matching the
 *   API's AUTH_LOCAL_DEV=true adapter.
 *
 * Only the project URL and the client-safe publishable key ever reach the app.
 */

export type AuthMode = 'supabase' | 'local-dev';

export interface SupabaseConfig {
  url: string;
  publishableKey: string;
}

export function readSupabaseConfig(
  env: { EXPO_PUBLIC_SUPABASE_URL?: string; EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY?: string },
): SupabaseConfig | null {
  const url = env.EXPO_PUBLIC_SUPABASE_URL?.trim() ?? '';
  const publishableKey = env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ?? '';
  if (!url && !publishableKey) return null;
  if (!url || !publishableKey) {
    throw new Error(
      'Set both EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY, or neither.',
    );
  }
  if (!url.startsWith('https://')) {
    throw new Error('EXPO_PUBLIC_SUPABASE_URL must be the https:// project API URL.');
  }
  return { url, publishableKey };
}

// Expo inlines EXPO_PUBLIC_* only for literal `process.env.NAME` references.
export const supabaseConfig = readSupabaseConfig({
  EXPO_PUBLIC_SUPABASE_URL: process.env.EXPO_PUBLIC_SUPABASE_URL,
  EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY: process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
});

export const authMode: AuthMode = supabaseConfig ? 'supabase' : 'local-dev';
