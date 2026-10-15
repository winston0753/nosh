import { useQuery } from '@tanstack/react-query';
import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../src/hooks/useAuth';
import type { Progress } from '../../src/api/types';

function MonthRow({ progress }: { progress: Progress }) {
  const [year, month] = progress.month.split('-');
  const monthName = new Date(parseInt(year), parseInt(month) - 1).toLocaleString('default', {
    month: 'long',
  });
  return (
    <View style={styles.row}>
      <Text style={styles.month}>{monthName} {year}</Text>
      <View style={styles.stats}>
        <View style={styles.stat}>
          <Text style={styles.statNumber}>{progress.confirmed_positive_new_count}</Text>
          <Text style={styles.statLabel}>New ✓ good</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statNumber}>{progress.total_confirmed_count}</Text>
          <Text style={styles.statLabel}>Total visits</Text>
        </View>
      </View>
    </View>
  );
}

export default function ProgressScreen() {
  const { client } = useAuth();

  const { data: progress, isLoading } = useQuery({
    queryKey: ['progress'],
    queryFn: () => client!.getProgress(),
    enabled: !!client,
  });

  if (isLoading) {
    return (
      <SafeAreaView style={styles.center}>
        <Text>Loading progress…</Text>
      </SafeAreaView>
    );
  }

  const totalNew = progress?.reduce((s, p) => s + p.confirmed_positive_new_count, 0) ?? 0;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.hero}>
          <Text style={styles.heroNumber}>{totalNew}</Text>
          <Text style={styles.heroLabel}>Confirmed positive new restaurants</Text>
        </View>
        {(progress ?? []).map((p) => (
          <MonthRow key={p.month} progress={p} />
        ))}
        {(progress ?? []).length === 0 && (
          <Text style={styles.empty}>Complete your first visit to see progress here.</Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: 24, gap: 16 },
  hero: { alignItems: 'center', paddingVertical: 24 },
  heroNumber: { fontSize: 64, fontWeight: '800', color: '#111' },
  heroLabel: { fontSize: 16, color: '#666', textAlign: 'center' },
  row: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    gap: 12,
  },
  month: { fontSize: 17, fontWeight: '600' },
  stats: { flexDirection: 'row', gap: 24 },
  stat: { alignItems: 'center' },
  statNumber: { fontSize: 28, fontWeight: '700', color: '#111' },
  statLabel: { fontSize: 12, color: '#888' },
  empty: { fontSize: 16, color: '#888', textAlign: 'center', paddingVertical: 32 },
});
