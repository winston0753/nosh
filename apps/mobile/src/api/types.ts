// Hand-maintained types matching the FastAPI OpenAPI schema.
// When the API changes, update these in the same PR.

export interface ContextCreate {
  name: string;
  meal_type: 'lunch' | 'dinner' | 'brunch';
  longitude: number;
  latitude: number;
  radius_meters?: number;
  local_window_start: string; // HH:MM
  local_window_end: string;   // HH:MM
  time_zone: string;
  active_days?: number[];
  notifications_enabled?: boolean;
}

export interface Context {
  id: string;
  name: string;
  meal_type: 'lunch' | 'dinner' | 'brunch';
  longitude: number;
  latitude: number;
  radius_meters: number;
  local_window_start: string;
  local_window_end: string;
  time_zone: string;
  active_days: number[];
  notifications_enabled: boolean;
  version: number;
  disabled_at: string | null;
  created_at: string;
}

export interface Proposal {
  id: string;
  place_id: string;
  place_name: string;
  cuisine_name: string;
  distance_meters: number;
  address: string | null;
  reason_codes: string[];
  sequence_number: number;
  total_score: number;
  score_components: Record<string, number>;
}

export interface Session {
  id: string;
  dining_context_id: string;
  meal_window_key: string;
  state: 'active' | 'accepted' | 'skipped' | 'exhausted' | 'no_candidates';
  policy_version: string;
  current_proposal: Proposal | null;
  created_at: string;
}

export type ResponseAction = 'go' | 'another' | 'not_today';

export interface ResponseResult {
  response: ResponseAction;
  session_state: string;
  next_proposal: Proposal | null;
  no_candidates: boolean;
}

export interface VisitCreate {
  place_id: string;
  proposal_id?: string;
  visited_at: string; // ISO 8601 UTC
  rating: 'positive' | 'negative';
  confirmation_source?: 'app_confirmation' | 'manual';
}

export interface Visit {
  id: string;
  place_id: string;
  place_name: string;
  proposal_id: string | null;
  visited_at: string;
  rating: 'positive' | 'negative' | null;
  confirmation_source: string;
  created_at: string;
  corrected_at: string | null;
}

export interface Progress {
  month: string; // YYYY-MM
  confirmed_positive_new_count: number;
  total_confirmed_count: number;
}

export interface OnboardingPlace {
  place: {
    id: string;
    canonical_name: string;
    address: string | null;
    status: string;
  };
  distance_meters: number;
  primary_cuisine: string | null;
  state: 'unknown' | 'visited' | 'not_interested';
}

export type PlaceStateValue = 'visited' | 'not_interested' | 'unknown';

export interface PlaceState {
  place_id: string;
  state: PlaceStateValue;
  source: 'onboarding' | 'confirmation' | 'manual' | 'import';
  was_visited_before_nosh: boolean;
}

export interface NoshApiError {
  code: string;
  message: string;
  field?: string | null;
}
