/**
 * Sign-in screen.
 *
 * In local development (AUTH_LOCAL_DEV=true on the API), the user enters
 * their UUID directly. This adapter is clearly isolated here so it can be
 * replaced with Supabase passwordless email auth when credentials are ready.
 */

import { router } from 'expo-router';
import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../../src/hooks/useAuth';

export default function SignInScreen() {
  const { signIn } = useAuth();
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    if (!token.trim()) {
      Alert.alert('Enter a user UUID or email');
      return;
    }
    setLoading(true);
    try {
      await signIn(token.trim());
      router.replace('/(app)');
    } catch {
      Alert.alert('Sign-in failed', 'Check your credentials and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <View style={styles.inner}>
        <Text style={styles.title}>Nosh</Text>
        <Text style={styles.subtitle}>Try more good restaurants nearby.</Text>

        <TextInput
          style={styles.input}
          placeholder="User UUID (local dev)"
          value={token}
          onChangeText={setToken}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType="go"
          onSubmitEditing={handleSignIn}
        />

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleSignIn}
          disabled={loading}
        >
          <Text style={styles.btnText}>{loading ? 'Signing in…' : 'Sign in'}</Text>
        </TouchableOpacity>

        <Text style={styles.note}>
          Local dev: enter any UUID. Production: replaced with passwordless email link.
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 16,
  },
  title: { fontSize: 48, fontWeight: '800', textAlign: 'center' },
  subtitle: { fontSize: 18, color: '#555', textAlign: 'center', marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  btn: {
    backgroundColor: '#111',
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 17, fontWeight: '600' },
  note: { fontSize: 12, color: '#aaa', textAlign: 'center' },
});
