import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { Proposal } from '../api/types';

interface Props {
  proposal: Proposal;
  sequenceNumber?: number;
}

const REASON_LABELS: Record<string, string> = {
  nearby: 'Nearby',
  new_to_you: 'New to you',
  highly_rated: 'Highly rated',
  preferred_cuisine: 'Matches your taste',
  many_options_remaining: 'Lots to explore',
};

export default function SuggestionCard({ proposal, sequenceNumber }: Props) {
  const distanceKm = (proposal.distance_meters / 1000).toFixed(1);
  const reasonLabel = proposal.reason_codes
    .slice(0, 2)
    .map((r) => REASON_LABELS[r] ?? r)
    .join(' · ');

  return (
    <View style={styles.card}>
      {sequenceNumber && sequenceNumber > 1 && (
        <Text style={styles.nextLabel}>Next option</Text>
      )}
      <Text style={styles.name}>{proposal.place_name}</Text>
      <Text style={styles.meta}>
        {proposal.cuisine_name} · {distanceKm} km away
      </Text>
      {proposal.address && (
        <Text style={styles.address}>{proposal.address}</Text>
      )}
      {reasonLabel ? (
        <Text style={styles.reason}>{reasonLabel}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  nextLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  name: {
    fontSize: 28,
    fontWeight: '700',
    color: '#111',
    marginBottom: 8,
  },
  meta: {
    fontSize: 16,
    color: '#555',
    marginBottom: 4,
  },
  address: {
    fontSize: 14,
    color: '#888',
    marginBottom: 12,
  },
  reason: {
    fontSize: 14,
    color: '#4CAF50',
    fontWeight: '500',
  },
});
