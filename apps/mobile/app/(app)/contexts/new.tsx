/**
 * Create a new dining context.
 * Uses a fixed SF Mission location in local dev; in production would use device location.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { userKey } from '../../../src/auth/queryKeys';
import { useAuth } from '../../../src/hooks/useAuth';

const SF_MISSION = { latitude: 37.759, longitude: -122.419 };

export default function NewContextScreen() {
  const { client, userId } = useAuth();
  const qc = useQueryClient();

  const [name, setName] = useState('Home Dinner');
  const [mealType, setMealType] = useState<'lunch' | 'dinner' | 'brunch'>('dinner');
  const [windowStart, setWindowStart] = useState('18:00');
  const [windowEnd, setWindowEnd] = useState('20:00');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  const createMutation = useMutation({
    mutationFn: () =>
      client!.createContext({
        name: name.trim() || 'My Context',
        meal_type: mealType,
        longitude: SF_MISSION.longitude,
        latitude: SF_MISSION.latitude,
        radius_meters: 1600,
        local_window_start: windowStart,
        local_window_end: windowEnd,
        time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        active_days: [0, 1, 2, 3, 4, 5, 6],
        notifications_enabled: notificationsEnabled,
      }),
    onSuccess: (ctx) => {
      qc.invalidateQueries({ queryKey: userKey(userId, 'contexts') });
      router.replace({ pathname: '/(app)/onboarding', params: { contextId: ctx.id } });
    },
    onError: () => Alert.alert('Could not create context', 'Check your connection.'),
  });

  const MEAL_TYPES: (typeof mealType)[] = ['lunch', 'dinner', 'brunch'];

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.label}>Name</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Home Dinner"
          />

          <Text style={styles.label}>Meal type</Text>
          <View style={styles.segmented}>
            {MEAL_TYPES.map((m) => (
              <TouchableOpacity
                key={m}
                style={[styles.segment, mealType === m && styles.segmentActive]}
                onPress={() => setMealType(m)}
              >
                <Text style={[styles.segmentText, mealType === m && styles.segmentTextActive]}>
                  {m.charAt(0).toUpperCase() + m.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.label}>Window start (HH:MM)</Text>
          <TextInput
            style={styles.input}
            value={windowStart}
            onChangeText={setWindowStart}
            placeholder="18:00"
            keyboardType="numbers-and-punctuation"
          />

          <Text style={styles.label}>Window end (HH:MM)</Text>
          <TextInput
            style={styles.input}
            value={windowEnd}
            onChangeText={setWindowEnd}
            placeholder="20:00"
            keyboardType="numbers-and-punctuation"
          />

          <View style={styles.switchRow}>
            <Text style={styles.label}>Enable notifications</Text>
            <Switch value={notificationsEnabled} onValueChange={setNotificationsEnabled} />
          </View>

          <Text style={styles.note}>
            Location is set to Mission District, SF for local dev.
            Production will use your device location.
          </Text>

          <TouchableOpacity
            style={[styles.btn, createMutation.isPending && styles.btnDisabled]}
            onPress={() => createMutation.mutate()}
            disabled={createMutation.isPending}
          >
            <Text style={styles.btnText}>
              {createMutation.isPending ? 'Creating…' : 'Create context'}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  scroll: { padding: 24, gap: 8 },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginTop: 12 },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  segmented: { flexDirection: 'row', gap: 8, marginTop: 4 },
  segment: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
  },
  segmentActive: { backgroundColor: '#111' },
  segmentText: { fontSize: 14, fontWeight: '500', color: '#444' },
  segmentTextActive: { color: '#fff' },
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  note: { fontSize: 12, color: '#aaa', marginTop: 8 },
  btn: {
    backgroundColor: '#111',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 17, fontWeight: '600' },
});
