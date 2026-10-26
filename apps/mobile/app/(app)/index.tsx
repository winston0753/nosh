/**
 * Main suggestion-card screen.
 *
 * Flow:
 * 1. Load existing contexts.
 * 2. If none, prompt to create one.
 * 3. Derive the meal-window key from the active context's time zone and meal type.
 * 4. Create/get the suggestion session for that key.
 * 5. Display the current proposal with Go / Another / Not today actions.
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
import { mealWindowKey } from '../../src/utils/mealWindowKey';

export default function SuggestionScreen() {
  const { client, userId } = useAuth();
  const qc = useQueryClient();
  const [respondingAction, setRespondingAction] = useState<ResponseAction | null>(null);

  const { data: contexts, isLoading: contextsLoading } = useQuery({
    queryKey: userKey(userId, 'contexts'),
    queryFn: () => client!.listContexts(),
    enabled: !!client,
  });

  const activeContext = contexts?.find((c) => !c.disabled_at) ?? null;

  // Derive the window key from the context's configured time zone and meal type.
  // Returns null when the context's active window is not currently open.
  // Do NOT create a session when windowKey is null — that would create a
  // session for a window key like "2026-10-12#dinner" when today is inactive.
  const windowKey: string | null = activeContext ? mealWindowKey(activeContext) : null;

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: userKey(userId, 'session', activeContext?.id, windowKey),
    queryFn: () => client!.createOrGetSession(activeContext!.id, windowKey!),
    enabled: !!client && !!activeContext && windowKey !== null,
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

  if (contextsLoading || sessionLoading) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.loadingText}>Loading…</Text>
      </SafeAreaView>
    );
  }

  if (!activeContext) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.emptyTitle}>No dining context yet</Text>
        <Text style={styles.emptyBody}>Create one to get your first suggestion.</Text>
        <TouchableOpacity style={styles.btn} onPress={() => router.push('/(app)/contexts/new')}>
          <Text style={styles.btnText}>Set up a context</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // No active meal window right now: either the time is outside the configured
  // window or today is not one of the context's active days.
  if (windowKey === null) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.emptyTitle}>No active meal window</Text>
        <Text style={styles.emptyBody}>
          {activeContext.name} opens at {activeContext.local_window_start}.
        </Text>
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
          <Text style={styles.emptyBody}>Try widening your radius in Settings.</Text>
        )}
      </SafeAreaView>
    );
  }

  const proposal = session.current_proposal;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <Text style={styles.contextName}>{activeContext.name}</Text>
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
  contextName: { fontSize: 18, fontWeight: '600', color: '#111' },
  settingsLink: { fontSize: 15, color: '#888' },
  actions: { gap: 12 },
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
