import { router } from 'expo-router';
import React from 'react';
import {
  Alert,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../../src/hooks/useAuth';

export default function SettingsScreen() {
  const { signOut, client } = useAuth();

  const handleSignOut = () => {
    Alert.alert('Sign out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out',
        style: 'destructive',
        onPress: async () => {
          await signOut();
          router.replace('/(auth)/sign-in');
        },
      },
    ]);
  };

  const handleDeleteData = () => {
    Alert.alert(
      'Delete Nosh data',
      'This removes your meal schedule, saved spots, place history, and visit records ' +
        'from Nosh. ' +
        'Your account sign-in is not affected. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete my data',
          style: 'destructive',
          onPress: async () => {
            try {
              await client?.deleteMyProductData();
              await signOut();
              router.replace('/(auth)/sign-in');
            } catch {
              Alert.alert('Error', 'Could not delete data. Please try again.');
            }
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.sectionTitle}>Meals</Text>
        <TouchableOpacity style={styles.row} onPress={() => router.push('/(app)/schedule')}>
          <Text style={styles.rowText}>Meal times and budget</Text>
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.row}>
          <Text style={styles.note}>
            Nosh stores your meal schedule, place history, and visit confirmations. Your current
            location is used only to find nearby places and is never stored or logged.
          </Text>
        </View>

        <TouchableOpacity style={[styles.row, styles.danger]} onPress={handleSignOut}>
          <Text style={styles.dangerText}>Sign out</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.row, styles.danger]} onPress={handleDeleteData}>
          <Text style={styles.dangerText}>Delete my Nosh data</Text>
          <Text style={styles.dangerNote}>
            Removes Nosh data only. Your sign-in account is not deleted.
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  scroll: { padding: 24, gap: 8 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#888',
    marginTop: 16,
    marginBottom: 4,
  },
  row: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  rowText: { fontSize: 16, color: '#111' },
  note: { fontSize: 14, color: '#666', lineHeight: 20 },
  danger: { marginTop: 8 },
  dangerText: { fontSize: 16, color: '#f44336', fontWeight: '500' },
  dangerNote: { fontSize: 12, color: '#888', marginTop: 4 },
});
