/**
 * Visit confirmation with honest, retry-safe state.
 *
 * - The request body is built once, on the first rating tap, and frozen.  Every
 *   retry re-sends exactly that body, so the server's idempotency identity
 *   (user + proposal_id) and the recorded visited_at never change.  A retry
 *   after an ambiguous failure (e.g. a timeout after the server committed)
 *   returns the existing visit instead of creating a duplicate.
 * - Success is reported only from the server's response; the displayed rating
 *   is the one the server stored.
 */

import { useMutation } from '@tanstack/react-query';
import { useCallback, useRef } from 'react';
import type { NoshClient } from '../api/client';
import type { Visit, VisitCreate } from '../api/types';

export type VisitRating = 'positive' | 'negative';

export type ConfirmationPhase = 'choosing' | 'saving' | 'failed' | 'saved';

export function buildVisitRequest(
  placeId: string,
  proposalId: string,
  rating: VisitRating,
  now: Date,
): VisitCreate {
  return {
    place_id: placeId,
    proposal_id: proposalId,
    visited_at: now.toISOString(),
    rating,
    confirmation_source: 'app_confirmation',
  };
}

interface Options {
  client: Pick<NoshClient, 'createVisit'>;
  placeId: string;
  proposalId: string;
  onSaved?: (visit: Visit) => void;
  now?: () => Date;
}

export interface VisitConfirmation {
  phase: ConfirmationPhase;
  /** The rating the user chose (pending or failed) or the server stored (saved). */
  rating: VisitRating | null;
  visit: Visit | undefined;
  submit: (rating: VisitRating) => void;
  retry: () => void;
}

export function useVisitConfirmation({
  client,
  placeId,
  proposalId,
  onSaved,
  now = () => new Date(),
}: Options): VisitConfirmation {
  const requestRef = useRef<VisitCreate | null>(null);
  const inFlightRef = useRef(false);

  const mutation = useMutation({
    mutationFn: (request: VisitCreate) => client.createVisit(request),
    // Retries are explicit (the retry button) so the UI always reflects them.
    retry: false,
    onSuccess: (visit) => onSaved?.(visit),
    onSettled: () => {
      inFlightRef.current = false;
    },
  });

  const send = useCallback(
    (request: VisitCreate) => {
      // Ignore taps while a request is outstanding (double taps arrive before
      // the re-render that disables the buttons).
      if (inFlightRef.current) return;
      inFlightRef.current = true;
      mutation.mutate(request);
    },
    [mutation],
  );

  const submit = useCallback(
    (rating: VisitRating) => {
      if (requestRef.current === null) {
        requestRef.current = buildVisitRequest(placeId, proposalId, rating, now());
      }
      send(requestRef.current);
    },
    [now, placeId, proposalId, send],
  );

  const retry = useCallback(() => {
    if (requestRef.current !== null) send(requestRef.current);
  }, [send]);

  const phase: ConfirmationPhase = mutation.isSuccess
    ? 'saved'
    : mutation.isPending
      ? 'saving'
      : mutation.isError
        ? 'failed'
        : 'choosing';

  const storedRating = mutation.data?.rating ?? null;
  const rating = storedRating ?? requestRef.current?.rating ?? null;

  return { phase, rating, visit: mutation.data, submit, retry };
}
