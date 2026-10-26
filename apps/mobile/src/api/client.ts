/**
 * Typed API client wrapping fetch against the Nosh FastAPI backend.
 *
 * Auth: in local dev, the auth token is the user's UUID string.
 * In production, it is the current Supabase access token, read from the
 * token provider on every request so refreshed tokens are always used.
 */

import type {
  Context,
  ContextCreate,
  OnboardingPlace,
  PlaceState,
  PlaceStateValue,
  Progress,
  ResponseAction,
  ResponseResult,
  Session,
  Visit,
  VisitCreate,
} from './types';

// EXPO_PUBLIC_API_URL is inlined by Expo's Metro bundler at build time.
// globals.d.ts declares the minimal process.env type.
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export type TokenProvider = () => Promise<string | null>;

export class NoshClient {
  private getToken: TokenProvider;

  constructor(token: string | TokenProvider) {
    this.getToken = typeof token === 'string' ? () => Promise.resolve(token) : token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const token = await this.getToken();
    if (!token) {
      throw Object.assign(new Error('Not signed in'), { code: 'unauthenticated', status: 401 });
    }
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options.headers ?? {}),
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ code: 'unknown', message: res.statusText }));
      throw Object.assign(new Error(err.message ?? res.statusText), {
        code: err.code,
        status: res.status,
      });
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  // ---- Account ----

  /**
   * Delete all Nosh product data for the current user.
   * Does NOT delete the Supabase Auth identity.
   */
  deleteMyProductData(): Promise<void> {
    return this.request('/v1/me/product-data', { method: 'DELETE' });
  }

  // ---- Contexts ----

  listContexts(): Promise<Context[]> {
    return this.request('/v1/contexts');
  }

  createContext(body: ContextCreate): Promise<Context> {
    return this.request('/v1/contexts', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // ---- Onboarding ----

  getOnboardingPlaces(contextId: string, limit = 30): Promise<OnboardingPlace[]> {
    return this.request(`/v1/contexts/${contextId}/onboarding-places?limit=${limit}`);
  }

  /**
   * Onboarding classification (Been / Not been / Not interested).  Records
   * source='onboarding'; Been permanently marks the place as visited before
   * Nosh so it never counts toward the North Star.
   */
  classifyOnboardingPlace(
    contextId: string,
    placeId: string,
    state: PlaceStateValue,
  ): Promise<PlaceState> {
    return this.request(`/v1/contexts/${contextId}/onboarding-places/${placeId}/state`, {
      method: 'PUT',
      body: JSON.stringify({ state }),
    });
  }

  /** Manual place-state edit (settings).  Never marks a place as pre-Nosh. */
  setPlaceState(placeId: string, state: PlaceStateValue): Promise<PlaceState> {
    return this.request(`/v1/places/${placeId}/state`, {
      method: 'PUT',
      body: JSON.stringify({ state }),
    });
  }

  // ---- Sessions ----

  createOrGetSession(contextId: string, mealWindowKey: string): Promise<Session> {
    return this.request('/v1/suggestion-sessions', {
      method: 'POST',
      body: JSON.stringify({
        dining_context_id: contextId,
        meal_window_key: mealWindowKey,
      }),
    });
  }

  getSession(sessionId: string): Promise<Session> {
    return this.request(`/v1/suggestion-sessions/${sessionId}`);
  }

  respondToProposal(
    proposalId: string,
    response: ResponseAction,
    clientEventId: string,
  ): Promise<ResponseResult> {
    return this.request(`/v1/proposals/${proposalId}/responses`, {
      method: 'POST',
      body: JSON.stringify({ response, client_event_id: clientEventId }),
    });
  }

  // ---- Visits ----

  createVisit(body: VisitCreate): Promise<Visit> {
    return this.request('/v1/visits', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  updateVisit(
    visitId: string,
    body: { rating?: 'positive' | 'negative'; visited_at?: string },
  ): Promise<Visit> {
    return this.request(`/v1/visits/${visitId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }

  listVisits(limit = 20): Promise<Visit[]> {
    return this.request(`/v1/visits?limit=${limit}`);
  }

  getProgress(): Promise<Progress[]> {
    return this.request('/v1/progress');
  }
}
