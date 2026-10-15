/**
 * Onboarding history screen: classify nearby places as Been, Not been, Not interested.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import React from 'react';
import {
  FlatList,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { OnboardingPlace } from '../../src/api/types';
import { useAuth } from '../../src/hooks/useAuth';

type PlaceState = 'visited' | 'not_interested' | 'unknown';

const STATE_BUTTONS: { label: string; value: PlaceState; color: string }[] = [
  { label: 'Been', value: 'visited', color: '#4CAF50' },
  { label: 'Not been', value: 'unknown', color: '#888' },
  { label: 'Not interested', value: 'not_interested', color: '#f44336' },
];

function PlaceRow({
  item,
  onState,
}: {
  item: OnboardingPlace;
  onState: (placeId: string, state: PlaceState) => void;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.placeInfo}>
        <Text style={styles.placeName}>{item.place.canonical_name}</Text>
        <Text style={styles.placeMeta}>
          {item.primary_cuisine ?? 'Restaurant'} ·{' '}
          {(item.distance_meters / 1000).toFixed(1)} km
        </Text>
      </View>
      <View style={styles.stateBtns}>
        {STATE_BUTTONS.map((btn) => (
          <TouchableOpacity
            key={btn.value}
            style={[
              styles.stateBtn,
              item.state === btn.value && { backgroundColor: btn.color },
            ]}
            onPress={() => onState(item.place.id, btn.value)}
          >
            <Text
              style={[
                styles.stateBtnText,
                item.state === btn.value && { color: '#fff' },
              ]}
            >
              {btn.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

export default function OnboardingScreen() {
  const { contextId } = useLocalSearchParams<{ contextId: string }>();
  const { client } = useAuth();
  const qc = useQueryClient();

  const { data: places, isLoading } = useQuery({
    queryKey: ['onboarding-places', contextId],
    queryFn: () => client!.getOnboardingPlaces(contextId!),
    enabled: !!client && !!contextId,
  });

  const stateMutation = useMutation({
    mutationFn: ({ placeId, state }: { placeId: string; state: PlaceState }) =>
      client!.setPlaceState(placeId, state),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding-places', contextId] });
    },
  });

  if (isLoading) {
    return (
      <SafeAreaView style={styles.center}>
        <Text>Loading places…</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={places ?? []}
        keyExtractor={(item) => item.place.id}
        renderItem={({ item }) => (
          <PlaceRow
            item={item}
            onState={(placeId, state) =>
              stateMutation.mutate({ placeId, state })
            }
          />
        )}
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.title}>Places near you</Text>
            <Text style={styles.subtitle}>
              {"Mark places you've already been so we skip them."}
            </Text>
          </View>
        }
        ListFooterComponent={
          <View style={styles.footer}>
            <TouchableOpacity
              style={styles.doneBtn}
              onPress={() => router.replace('/(app)')}
            >
              <Text style={styles.doneBtnText}>Done</Text>
            </TouchableOpacity>
          </View>
        }
        contentContainerStyle={styles.list}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  list: { padding: 16, gap: 12 },
  header: { paddingBottom: 16 },
  title: { fontSize: 24, fontWeight: '700', marginBottom: 4 },
  subtitle: { fontSize: 15, color: '#666' },
  row: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  placeInfo: { gap: 2 },
  placeName: { fontSize: 16, fontWeight: '600' },
  placeMeta: { fontSize: 13, color: '#888' },
  stateBtns: { flexDirection: 'row', gap: 8 },
  stateBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
  },
  stateBtnText: { fontSize: 12, fontWeight: '500', color: '#444' },
  footer: { paddingTop: 16, paddingBottom: 32 },
  doneBtn: {
    backgroundColor: '#111',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  doneBtnText: { color: '#fff', fontSize: 17, fontWeight: '600' },
});
