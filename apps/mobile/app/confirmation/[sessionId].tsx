/**
 * Visit confirmation screen — shown after a Go action.
 * Deep-linked from notifications or the app after the meal window.
 *
 * Requires: sessionId (from path) + proposalId + placeName (from query params)
 * set when the user taps Go. This avoids fetching the session to find the
 * accepted proposal (session.current_proposal is null once accepted).
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import {
  Alert,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../../src/hooks/useAuth';

export default function ConfirmationScreen() {
  const { proposalId, placeId, placeName } =
    useLocalSearchParams<{
      sessionId: string;
      proposalId: string;
      placeId: string;
      placeName: string;
    }>();
  const { client } = useAuth();
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState<'yes' | 'no' | null>(null);
  const [rating, setRating] = useState<'positive' | 'negative' | null>(null);

  const displayName = placeName ?? 'this restaurant';

  const visitMutation = useMutation({
    mutationFn: (r: 'positive' | 'negative') => {
      if (!placeId) {
        throw new Error('Missing place ID for visit confirmation');
      }
      return client!.createVisit({
        place_id: placeId,
        proposal_id: proposalId ?? undefined,
        visited_at: new Date().toISOString(),
        rating: r,
        confirmation_source: 'app_confirmation',
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['visits'] });
      qc.invalidateQueries({ queryKey: ['progress'] });
      router.replace('/(app)');
    },
    onError: () => Alert.alert('Could not save visit', 'Try again.'),
  });

  if (confirming === null) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>Did you visit {displayName}?</Text>
          <TouchableOpacity style={styles.btn} onPress={() => setConfirming('yes')}>
            <Text style={styles.btnText}>Yes, I went</Text>
          </TouchableOpacity>
          <TouchableOpacity
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
  if (rating === null) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.inner}>
          <Text style={styles.title}>How was {displayName}?</Text>
          <TouchableOpacity
            style={[styles.btn, styles.positive]}
            onPress={() => {
              setRating('positive');
              visitMutation.mutate('positive');
            }}
            disabled={visitMutation.isPending}
          >
            <Text style={styles.btnText}>👍 Good</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.btn, styles.negative]}
            onPress={() => {
              setRating('negative');
              visitMutation.mutate('negative');
            }}
            disabled={visitMutation.isPending}
          >
            <Text style={styles.btnText}>👎 Not great</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <Text style={styles.title}>Thanks!</Text>
        <Text style={styles.body}>
          {rating === 'positive' ? 'Great pick 🎉' : "We'll learn from this."}
        </Text>
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
