// Hand-maintained types matching the FastAPI OpenAPI schema.
// When the API changes, update these in the same PR.

export type MealType = 'lunch' | 'dinner';

/** One meal of the schedule as sent to PUT /v1/me/meal-schedule. */
export interface MealPlanInput {
  meal_type: MealType;
  enabled: boolean;
  local_window_start: string; // HH:MM
  local_window_end: string; // HH:MM
  active_days: number[]; // 0=Mon … 6=Sun
  price_ceiling: PriceCeiling | null; // null = no limit
  notifications_enabled?: boolean;
}

/** 1 ($) to 4 ($$$$). */
export type PriceCeiling = 1 | 2 | 3 | 4;

export interface MealScheduleUpdate {
  time_zone: string; // IANA
  meals: MealPlanInput[];
}

export interface MealPlan extends Required<MealPlanInput> {
  time_zone: string;
  version: number;
  updated_at: string;
}

/** `meals` is empty until the user finishes the schedule survey. */
export interface MealSchedule {
  meals: MealPlan[];
}

export type AnchorKind = 'home' | 'work';

export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface Anchor extends Coordinate {
  kind: AnchorKind;
  updated_at: string;
}

/** Where a new session is centred: the device location or a saved spot. */
export type SessionAnchor = { location: Coordinate } | { anchor: AnchorKind };

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
  meal_window_key: string;
  anchor_source: string; // device, home, work (legacy_context for migrated sessions)
  state: 'active' | 'accepted' | 'skipped' | 'exhausted' | 'no_candidates';
  policy_version: string;
  current_proposal: Proposal | null;
  created_at: string;
}

/** Go / Another / Not today, plus the card's secondary Been here already (D025). */
export type ResponseAction = 'go' | 'another' | 'not_today' | 'been_here';

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

export type PlaceStateValue = 'visited' | 'not_interested' | 'unknown';

export interface PlaceState {
  place_id: string;
  state: PlaceStateValue;
  source: 'onboarding' | 'been_here' | 'confirmation' | 'manual' | 'import';
  was_visited_before_nosh: boolean;
}

export interface NoshApiError {
  code: string;
  message: string;
  field?: string | null;
}
