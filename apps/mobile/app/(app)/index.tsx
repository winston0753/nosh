/**
 * Main suggestion-card screen.
 *
 * Flow:
 * 1. Load the user's meal schedule.
 * 2. If it is empty, prompt for the schedule survey.
 * 3. Find the enabled meal whose window is open now and derive its key.
 * 4. Create/get the suggestion session for that key, anchored at the user's
 *    location (see PLACEHOLDER_LOCATION).
 * 5. Display the current proposal with Go / Another / Not today, plus the
 *    secondary Been here already.
 *
 * Idempotency: the client_event_id is derived from (proposal_id, action) and
 * is therefore stable across network retries for the same user action.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Linking from 'expo-linking';
import { router } from 'expo-router';
import React, { useCallback, useState } from 'react';
import {
  Alert,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { ResponseAction } from '../../src/api/types';
import ResponseButtons from '../../src/components/ResponseButtons';
import SuggestionCard from '../../src/components/SuggestionCard';
import { userKey } from '../../src/auth/queryKeys';
import { useAuth } from '../../src/hooks/useAuth';
import { openMealWindow } from '../../src/utils/mealWindowKey';

// Until the current-location step adds expo-location (Milestone 3 step 5),
// every session is anchored in San Francisco's Mission District, where the
// fixture places are.  Never log this or a real device coordinate.
const PLACEHOLDER_LOCATION = { latitude: 37.759, longitude: -122.419 };

const MEAL_NAMES = { lunch: 'Lunch', dinner: 'Dinner' } as const;

export default function SuggestionScreen() {
  const { client, userId } = useAuth();
  const qc = useQueryClient();
  const [respondingAction, setRespondingAction] = useState<ResponseAction | null>(null);

  const { data: schedule, isLoading: scheduleLoading } = useQuery({
    queryKey: userKey(userId, 'schedule'),
    queryFn: () => client!.getMealSchedule(),
    enabled: !!client,
  });

  // The enabled meal whose window is open now, with its key.  Do NOT create a
  // session when this is null — that would create a session for a window key
  // like "2026-10-12#dinner" outside the window or on an inactive day.
  const open = schedule ? openMealWindow(schedule.meals) : null;
  const windowKey = open?.key ?? null;

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: userKey(userId, 'session', windowKey),
    queryFn: () => client!.createOrGetSession(windowKey!, { location: PLACEHOLDER_LOCATION }),
    enabled: !!client && windowKey !== null,
  });

  const respondMutation = useMutation({
    mutationFn: async (action: ResponseAction) => {
      const proposal = session?.current_proposal;
      if (!proposal) return;
      // Stable idempotency key: same proposal + same action = same key, even
      // across network retries.  Never include Date.now() here.
      const clientEventId = `${proposal.id}:${action}`;
      return client!.respondToProposal(proposal.id, action, clientEventId);
    },
    onSuccess: (result, action) => {
      const proposal = session?.current_proposal;
      if (action === 'go' && proposal && session) {
        openMaps(proposal);
        // Pass accepted-proposal context to the confirmation screen.
        // We pass proposalId/placeId/placeName so the screen can confirm
        // without re-fetching the (now-closed) session.
        router.push({
          pathname: '/confirmation/[sessionId]',
          params: {
            sessionId: session.id,
            proposalId: proposal.id,
            placeId: proposal.place_id,
            placeName: proposal.place_name,
          },
        });
      }
      qc.invalidateQueries({ queryKey: userKey(userId, 'session') });
      setRespondingAction(null);
    },
    onError: () => {
      Alert.alert('Something went wrong', 'Please try again.');
      setRespondingAction(null);
    },
  });

  const openMaps = useCallback(
    (proposal: NonNullable<typeof session>['current_proposal']) => {
      if (!proposal) return;
      const query = encodeURIComponent(`${proposal.place_name} ${proposal.address ?? ''}`);
      const url = Platform.OS === 'ios' ? `maps://?q=${query}` : `geo:0,0?q=${query}`;
      Linking.openURL(url).catch(() => {
        Linking.openURL(`https://maps.apple.com/?q=${query}`);
      });
    },
    [],
  );

  const handleResponse = useCallback(
    (action: ResponseAction) => {
      setRespondingAction(action);
      respondMutation.mutate(action);
    },
    [respondMutation],
  );

  if (scheduleLoading || sessionLoading) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.loadingText}>Loading…</Text>
      </SafeAreaView>
    );
  }

  if (!schedule?.meals.length) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.emptyTitle}>When do you eat out?</Text>
        <Text style={styles.emptyBody}>Set your meal times to get your first suggestion.</Text>
        <TouchableOpacity style={styles.btn} onPress={() => router.push('/(app)/schedule')}>
          <Text style={styles.btnText}>Set meal times</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // No meal window open right now: outside every enabled window, or today is
  // not one of their active days.
  if (open === null) {
    const enabled = schedule.meals.filter((m) => m.enabled);
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.emptyTitle}>No meal window open</Text>
        {enabled.map((m) => (
          <Text key={m.meal_type} style={styles.emptyBody}>
            {MEAL_NAMES[m.meal_type]}: {m.local_window_start}–{m.local_window_end}
          </Text>
        ))}
        <TouchableOpacity onPress={() => router.push('/(app)/settings')}>
          <Text style={styles.settingsLink}>Settings</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  if (!session?.current_proposal) {
    const state = session?.state;
    const title =
      state === 'accepted'
        ? 'Enjoy your meal!'
        : state === 'exhausted'
          ? 'No more options nearby'
          : state === 'skipped'
            ? 'See you next time'
            : state === 'no_candidates'
              ? 'No restaurants found'
              : 'No suggestion right now';

    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.emptyTitle}>{title}</Text>
        {(state === 'exhausted' || state === 'no_candidates') && (
          <Text style={styles.emptyBody}>Nothing else nearby fits right now.</Text>
        )}
      </SafeAreaView>
    );
  }

  const proposal = session.current_proposal;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <Text style={styles.mealName}>{MEAL_NAMES[open.meal.meal_type]}</Text>
          <TouchableOpacity onPress={() => router.push('/(app)/settings')}>
            <Text style={styles.settingsLink}>Settings</Text>
          </TouchableOpacity>
        </View>

        <SuggestionCard proposal={proposal} sequenceNumber={proposal.sequence_number} />

        <View style={styles.actions}>
          <ResponseButtons
            onResponse={handleResponse}
            loading={respondMutation.isPending}
            disabled={!!respondingAction}
          />
          <TouchableOpacity
            onPress={() => handleResponse('been_here')}
            disabled={!!respondingAction}
            accessibilityRole="button"
            accessibilityHint="Skips this place now and in future suggestions"
          >
            <Text style={styles.beenHere}>Been here already</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.navRow}>
          <TouchableOpacity onPress={() => router.push('/(app)/history')}>
            <Text style={styles.navLink}>History</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/(app)/progress')}>
            <Text style={styles.navLink}>Progress</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 16 },
  scroll: { padding: 24, gap: 24 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  mealName: { fontSize: 18, fontWeight: '600', color: '#111' },
  settingsLink: { fontSize: 15, color: '#888' },
  actions: { gap: 12 },
  beenHere: { fontSize: 15, color: '#666', textAlign: 'center', paddingVertical: 4 },
  navRow: { flexDirection: 'row', justifyContent: 'space-around', paddingTop: 8 },
  navLink: { fontSize: 15, color: '#555' },
  loadingText: { fontSize: 16, color: '#888' },
  emptyTitle: { fontSize: 22, fontWeight: '600', textAlign: 'center' },
  emptyBody: { fontSize: 16, color: '#666', textAlign: 'center' },
  btn: {
    backgroundColor: '#111',
    borderRadius: 10,
    paddingVertical: 14,
    paddingHorizontal: 32,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
