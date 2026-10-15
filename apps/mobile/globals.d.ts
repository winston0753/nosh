// Expo's Metro bundler inlines EXPO_PUBLIC_* variables at build time.
// Declare the minimal process.env shape needed to avoid @types/node.
declare namespace NodeJS {
  interface ProcessEnv {
    readonly EXPO_PUBLIC_API_URL?: string;
  }
}

declare const process: {
  readonly env: NodeJS.ProcessEnv;
};
