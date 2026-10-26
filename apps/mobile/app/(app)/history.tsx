import { useQuery } from '@tanstack/react-query';
import React from 'react';
import { FlatList, SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { userKey } from '../../src/auth/queryKeys';
import { useAuth } from '../../src/hooks/useAuth';
import type { Visit } from '../../src/api/types';

function VisitRow({ visit }: { visit: Visit }) {
  const date = new Date(visit.visited_at).toLocaleDateString();
  return (
    <View style={styles.row}>
      <View style={styles.rowMain}>
        <Text style={styles.placeName}>{visit.place_name}</Text>
        <Text style={styles.date}>{date}</Text>
      </View>
      {visit.rating && (
        <Text style={styles.rating}>{visit.rating === 'positive' ? '👍' : '👎'}</Text>
      )}
    </View>
  );
}

export default function HistoryScreen() {
  const { client, userId } = useAuth();

  const { data: visits, isLoading } = useQuery({
    queryKey: userKey(userId, 'visits'),
    queryFn: () => client!.listVisits(50),
    enabled: !!client,
  });

  if (isLoading) {
    return (
      <SafeAreaView style={styles.center}>
        <Text>Loading history…</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={visits ?? []}
        keyExtractor={(v) => v.id}
        renderItem={({ item }) => <VisitRow visit={item} />}
        ListEmptyComponent={
          <View style={styles.center}>
            <Text style={styles.emptyText}>No confirmed visits yet.</Text>
          </View>
        }
        contentContainerStyle={styles.list}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  list: { padding: 16, gap: 8 },
  row: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  rowMain: { gap: 4 },
  placeName: { fontSize: 16, fontWeight: '600' },
  date: { fontSize: 13, color: '#888' },
  rating: { fontSize: 22 },
  emptyText: { fontSize: 16, color: '#888' },
});
