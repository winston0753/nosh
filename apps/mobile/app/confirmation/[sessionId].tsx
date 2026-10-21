/**
 * Visit confirmation screen — shown after a Go action.
 * Deep-linked from notifications or the app after the meal window.
 *
 * Requires: sessionId (from path) + proposalId + placeId + placeName (from
 * query params) set when the user taps Go. This avoids fetching the session to
 * find the accepted proposal (session.current_proposal is null once accepted).
 *
 * Save states: choosing → saving → saved ("Thanks") or failed (retry).  "Thanks"
 * appears only after the server confirms the visit; a retry re-sends the same
 * frozen request, so it can never create a duplicate visit.
 */

import { useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NoshClient } from '../../src/api/client';
import { useAuth } from '../../src/hooks/useAuth';
import { useVisitConfirmation } from '../../src/hooks/useVisitConfirmation';

export default function ConfirmationScreen() {
  const { proposalId, placeId, placeName } = useLocalSearchParams<{
    sessionId: string;
    proposalId: string;
    placeId: string;
    placeName: string;
  }>();
  const { client } = useAuth();
  const displayName = placeName ?? 'this restaurant';

  // Without a proposal there is no idempotency identity for the visit, so a
  // retry could duplicate it.  Refuse rather than write unsafely.
  if (!proposalId || !placeId) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>Can&apos;t confirm this visit</Text>
          <Text style={styles.body}>This confirmation link is incomplete.</Text>
          <TouchableOpacity style={styles.btn} onPress={() => router.replace('/(app)')}>
            <Text style={styles.btnText}>Back to suggestions</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (!client) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <ActivityIndicator />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <ConfirmationFlow
      client={client}
      proposalId={proposalId}
      placeId={placeId}
      displayName={displayName}
    />
  );
}

function ConfirmationFlow({
  client,
  proposalId,
  placeId,
  displayName,
}: {
  client: NoshClient;
  proposalId: string;
  placeId: string;
  displayName: string;
}) {
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState<'yes' | 'no' | null>(null);
  const { phase, rating, submit, retry } = useVisitConfirmation({
    client,
    placeId,
    proposalId,
    onSaved: () => {
      qc.invalidateQueries({ queryKey: ['visits'] });
      qc.invalidateQueries({ queryKey: ['progress'] });
    },
  });

  if (confirming === null) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>Did you visit {displayName}?</Text>
          <TouchableOpacity
            testID="confirm-yes"
            style={styles.btn}
            onPress={() => setConfirming('yes')}
          >
            <Text style={styles.btnText}>Yes, I went</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="confirm-no"
            style={[styles.btn, styles.secondary]}
            onPress={() => setConfirming('no')}
          >
            <Text style={styles.secondaryText}>No, I didn&apos;t go</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.laterText}>Remind me later</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (confirming === 'no') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>No problem!</Text>
          <Text style={styles.body}>{"We'll suggest this place again another time."}</Text>
          <TouchableOpacity style={styles.btn} onPress={() => router.replace('/(app)')}>
            <Text style={styles.btnText}>Back to suggestions</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // confirming === 'yes'
  if (phase === 'saved') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>Thanks!</Text>
          <Text style={styles.body}>
            {rating === 'positive' ? 'Great pick 🎉' : "We'll learn from this."}
          </Text>
          <TouchableOpacity
            testID="confirm-done"
            style={styles.btn}
            onPress={() => router.replace('/(app)')}
          >
            <Text style={styles.btnText}>Done</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (phase === 'saving') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <ActivityIndicator />
          <Text style={styles.body}>Saving your visit…</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (phase === 'failed') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>Couldn&apos;t save your visit</Text>
          <Text style={styles.body}>
            Check your connection and try again. Your{' '}
            {rating === 'positive' ? '👍 Good' : '👎 Not great'} rating is kept.
          </Text>
          <TouchableOpacity testID="confirm-retry" style={styles.btn} onPress={retry}>
            <Text style={styles.btnText}>Try again</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.laterText}>Remind me later</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <Text style={styles.title}>How was {displayName}?</Text>
        <TouchableOpacity
          testID="rate-positive"
          style={[styles.btn, styles.positive]}
          onPress={() => submit('positive')}
        >
          <Text style={styles.btnText}>👍 Good</Text>
        </TouchableOpacity>
        <TouchableOpacity
          testID="rate-negative"
          style={[styles.btn, styles.negative]}
          onPress={() => submit('negative')}
        >
          <Text style={styles.btnText}>👎 Not great</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  inner: { flex: 1, padding: 32, justifyContent: 'center', gap: 16 },
  title: { fontSize: 26, fontWeight: '700', textAlign: 'center', marginBottom: 8 },
  body: { fontSize: 16, color: '#666', textAlign: 'center' },
  btn: {
    backgroundColor: '#111',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  secondary: { backgroundColor: '#f0f0f0' },
  positive: { backgroundColor: '#4CAF50' },
  negative: { backgroundColor: '#f44336' },
  btnText: { color: '#fff', fontSize: 17, fontWeight: '600' },
  secondaryText: { color: '#333', fontSize: 17, fontWeight: '600' },
  laterText: { color: '#888', fontSize: 15, textAlign: 'center' },
});
