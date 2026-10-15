import React from 'react';
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ResponseAction } from '../api/types';

interface Props {
  onResponse: (action: ResponseAction) => void;
  loading: boolean;
  disabled?: boolean;
}

export default function ResponseButtons({ onResponse, loading, disabled }: Props) {
  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={[styles.btn, styles.go]}
        onPress={() => onResponse('go')}
        disabled={loading || disabled}
        accessibilityRole="button"
        accessibilityLabel="Go — open in Maps"
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.goText}>Go</Text>
        )}
      </TouchableOpacity>

      <View style={styles.row}>
        <TouchableOpacity
          style={[styles.btn, styles.another]}
          onPress={() => onResponse('another')}
          disabled={loading || disabled}
          accessibilityRole="button"
          accessibilityLabel="Another suggestion"
        >
          <Text style={styles.secondaryText}>Another</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.btn, styles.notToday]}
          onPress={() => onResponse('not_today')}
          disabled={loading || disabled}
          accessibilityRole="button"
          accessibilityLabel="Not today"
        >
          <Text style={styles.secondaryText}>Not today</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 12,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  btn: {
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  go: {
    backgroundColor: '#111',
    flex: 1,
  },
  another: {
    flex: 1,
    backgroundColor: '#f0f0f0',
  },
  notToday: {
    flex: 1,
    backgroundColor: '#f0f0f0',
  },
  goText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  secondaryText: {
    color: '#333',
    fontSize: 16,
    fontWeight: '500',
  },
});
