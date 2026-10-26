// Expo's Metro bundler inlines EXPO_PUBLIC_* variables at build time.
// Declare the minimal process.env shape needed to avoid @types/node.
declare namespace NodeJS {
  interface ProcessEnv {
    readonly EXPO_PUBLIC_API_URL?: string;
    readonly EXPO_PUBLIC_SUPABASE_URL?: string;
    readonly EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY?: string;
  }
}

declare const process: {
  readonly env: NodeJS.ProcessEnv;
};
