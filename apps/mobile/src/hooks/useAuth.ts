/**
 * Auth hook.  The session lives in <AuthProvider> (src/auth/AuthProvider.tsx);
 * this module keeps the import path screens already use.
 */

export { useAuth } from '../auth/AuthProvider';
export type { AuthContextValue, AuthStatus } from '../auth/AuthProvider';
