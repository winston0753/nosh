/**
 * Typed API client wrapping fetch against the Nosh FastAPI backend.
 *
 * Auth: in local dev, the auth token is the user's UUID string.
 * In production, it is the current Supabase access token, read from the
 * token provider on every request so refreshed tokens are always used.
 */

import type {
  Anchor,
  AnchorKind,
  Coordinate,
  MealSchedule,
  MealScheduleUpdate,
  PlaceState,
  PlaceStateValue,
  Progress,
  ResponseAction,
  ResponseResult,
  Session,
  SessionAnchor,
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

  // ---- Meal schedule and Home/Work spots ----

  getMealSchedule(): Promise<MealSchedule> {
    return this.request('/v1/me/meal-schedule');
  }

  /** Full replacement; an identical PUT is a no-op, so retries are safe. */
  putMealSchedule(body: MealScheduleUpdate): Promise<MealSchedule> {
    return this.request('/v1/me/meal-schedule', {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  listAnchors(): Promise<Anchor[]> {
    return this.request('/v1/me/anchors');
  }

  setAnchor(kind: AnchorKind, point: Coordinate): Promise<Anchor> {
    return this.request(`/v1/me/anchors/${kind}`, {
      method: 'PUT',
      body: JSON.stringify(point),
    });
  }

  deleteAnchor(kind: AnchorKind): Promise<void> {
    return this.request(`/v1/me/anchors/${kind}`, { method: 'DELETE' });
  }

  // ---- Places ----

  /** Manual place-state edit (settings).  Never marks a place as pre-Nosh. */
  setPlaceState(placeId: string, state: PlaceStateValue): Promise<PlaceState> {
    return this.request(`/v1/places/${placeId}/state`, {
      method: 'PUT',
      body: JSON.stringify({ state }),
    });
  }

  // ---- Sessions ----

  /**
   * Open (or fetch) the session for a meal window.  The location is used once
   * to rank nearby places and is never stored by the API.
   */
  createOrGetSession(mealWindowKey: string, anchor: SessionAnchor): Promise<Session> {
    return this.request('/v1/suggestion-sessions', {
      method: 'POST',
      body: JSON.stringify({ meal_window_key: mealWindowKey, ...anchor }),
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
