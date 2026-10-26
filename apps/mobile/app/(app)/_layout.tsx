import { router, Stack } from 'expo-router';
import React, { useEffect } from 'react';
import { useAuth } from '../../src/hooks/useAuth';

export default function AppLayout() {
  const { status } = useAuth();

  useEffect(() => {
    if (status === 'signed-out') {
      router.replace('/(auth)/sign-in');
    }
  }, [status]);

  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: 'Nosh' }} />
      <Stack.Screen name="history" options={{ title: 'History' }} />
      <Stack.Screen name="progress" options={{ title: 'Progress' }} />
      <Stack.Screen name="settings" options={{ title: 'Settings' }} />
      <Stack.Screen name="schedule" options={{ title: 'Meal times' }} />
    </Stack>
  );
}
