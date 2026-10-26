/** A query key scoped to one user, so cached data never crosses accounts. */
export function userKey(userId: string | null, ...parts: readonly unknown[]): unknown[] {
  return ['user', userId, ...parts];
}
