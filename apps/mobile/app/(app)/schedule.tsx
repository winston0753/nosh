/**
 * Meal-schedule survey (D020, D026): which meals Nosh helps with, when, on
 * which days, and the most the user wants to spend.  Also used to edit the
 * schedule later from Settings.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
import type { MealType, PriceCeiling } from '../../src/api/types';
import { userKey } from '../../src/auth/queryKeys';
import { useAuth } from '../../src/hooks/useAuth';
import {
  MEAL_ORDER,
  scheduleFormFrom,
  toScheduleUpdate,
  validateScheduleForm,
  type MealForm,
  type ScheduleForm,
} from '../../src/utils/scheduleForm';

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']; // 0=Mon … 6=Sun
const PRICE_OPTIONS: { label: string; value: PriceCeiling | null }[] = [
  { label: '$', value: 1 },
  { label: '$$', value: 2 },
  { label: '$$$', value: 3 },
  { label: '$$$$', value: 4 },
  { label: 'Any', value: null },
];
const MEAL_COPY: Record<MealType, { title: string; hint: string }> = {
  lunch: { title: 'Lunch', hint: 'On by default.' },
  dinner: { title: 'Dinner', hint: 'Turn on if you also want help with dinner.' },
};

export default function ScheduleScreen() {
  const { client, userId } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: userKey(userId, 'schedule'),
    queryFn: () => client!.getMealSchedule(),
    enabled: !!client,
  });

  if (isLoading) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.muted}>Loading…</Text>
      </SafeAreaView>
    );
  }
  return <ScheduleEditor initial={scheduleFormFrom(data)} isFirstRun={!data?.meals.length} />;
}

function ScheduleEditor({ initial, isFirstRun }: { initial: ScheduleForm; isFirstRun: boolean }) {
  const { client, userId } = useAuth();
  const qc = useQueryClient();
  const [form, setForm] = useState(initial);

  const updateMeal = (meal: MealType, patch: Partial<MealForm>) =>
    setForm((f) => ({ ...f, [meal]: { ...f[meal], ...patch } }));

  const save = useMutation({
    mutationFn: () =>
      client!.putMealSchedule(
        toScheduleUpdate(form, Intl.DateTimeFormat().resolvedOptions().timeZone),
      ),
    onSuccess: (schedule) => {
      qc.setQueryData(userKey(userId, 'schedule'), schedule);
      qc.invalidateQueries({ queryKey: userKey(userId, 'session') });
      router.replace('/(app)');
    },
    onError: () => Alert.alert('Could not save your schedule', 'Check your connection.'),
  });

  const onSave = () => {
    const problem = validateScheduleForm(form);
    if (problem) {
      Alert.alert('Check your schedule', problem);
      return;
    }
    save.mutate();
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          {isFirstRun && (
            <View style={styles.intro}>
              <Text style={styles.title}>When should Nosh help?</Text>
              <Text style={styles.muted}>
                Nosh suggests one nearby place during these times, wherever you are.
              </Text>
            </View>
          )}

          {MEAL_ORDER.map((meal) => (
            <MealSection
              key={meal}
              meal={meal}
              value={form[meal]}
              onChange={(patch) => updateMeal(meal, patch)}
            />
          ))}

          <TouchableOpacity
            style={[styles.btn, save.isPending && styles.btnDisabled]}
            onPress={onSave}
            disabled={save.isPending}
          >
            <Text style={styles.btnText}>{save.isPending ? 'Saving…' : 'Save'}</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function MealSection({
  meal,
  value,
  onChange,
}: {
  meal: MealType;
  value: MealForm;
  onChange: (patch: Partial<MealForm>) => void;
}) {
  const copy = MEAL_COPY[meal];
  const toggleDay = (day: number) =>
    onChange({
      days: value.days.includes(day) ? value.days.filter((d) => d !== day) : [...value.days, day],
    });

  return (
    <View style={styles.section}>
      <View style={styles.switchRow}>
        <View>
          <Text style={styles.sectionTitle}>{copy.title}</Text>
          <Text style={styles.muted}>{copy.hint}</Text>
        </View>
        <Switch
          value={value.enabled}
          onValueChange={(enabled) => onChange({ enabled })}
          accessibilityLabel={`Help with ${meal}`}
        />
      </View>

      {value.enabled && (
        <>
          <Text style={styles.label}>Days</Text>
          <View style={styles.chips}>
            {DAY_LABELS.map((label, day) => {
              const on = value.days.includes(day);
              return (
                <TouchableOpacity
                  key={day}
                  style={[styles.chip, on && styles.chipOn]}
                  onPress={() => toggleDay(day)}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: on }}
                >
                  <Text style={[styles.chipText, on && styles.chipTextOn]}>{label}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <Text style={styles.label}>Between (24-hour)</Text>
          <View style={styles.timeRow}>
            <TextInput
              style={[styles.input, styles.timeInput]}
              value={value.start}
              onChangeText={(start) => onChange({ start })}
              placeholder="11:30"
              keyboardType="numbers-and-punctuation"
              maxLength={5}
            />
            <Text style={styles.muted}>and</Text>
            <TextInput
              style={[styles.input, styles.timeInput]}
              value={value.end}
              onChangeText={(end) => onChange({ end })}
              placeholder="13:30"
              keyboardType="numbers-and-punctuation"
              maxLength={5}
            />
          </View>

          <Text style={styles.label}>Most you want to spend</Text>
          <View style={styles.chips}>
            {PRICE_OPTIONS.map((option) => {
              const on = value.priceCeiling === option.value;
              return (
                <TouchableOpacity
                  key={option.label}
                  style={[styles.chip, styles.priceChip, on && styles.chipOn]}
                  onPress={() => onChange({ priceCeiling: option.value })}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: on }}
                >
                  <Text style={[styles.chipText, on && styles.chipTextOn]}>{option.label}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: 24, gap: 16 },
  intro: { gap: 6 },
  title: { fontSize: 24, fontWeight: '700', color: '#111' },
  muted: { fontSize: 14, color: '#777' },
  section: { backgroundColor: '#fff', borderRadius: 12, padding: 16, gap: 8 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#111' },
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginTop: 8 },
  chips: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  chip: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  priceChip: { width: undefined, paddingHorizontal: 14 },
  chipOn: { backgroundColor: '#111' },
  chipText: { fontSize: 14, fontWeight: '500', color: '#444' },
  chipTextOn: { color: '#fff' },
  timeRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  timeInput: { width: 90, textAlign: 'center' },
  btn: {
    backgroundColor: '#111',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 17, fontWeight: '600' },
});
