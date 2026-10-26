/**
 * Sign-in screen.
 *
 * Supabase mode: passwordless email.  The user enters an email address,
 * receives a one-time code, and enters it here.  A code (rather than a magic
 * link) works even when the email is opened on another device.
 *
 * Local-dev mode (no Supabase configuration; API AUTH_LOCAL_DEV=true): the
 * user enters a UUID that becomes their bearer token.
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

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CODE_PATTERN = /^\d{6,10}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function errorStatus(error: unknown): number | undefined {
  return typeof error === 'object' && error !== null && 'status' in error
    ? (error as { status?: number }).status
    : undefined;
}

/** Explains a failed send-code request; supabase-js reports network failures as status 0. */
function sendCodeErrorMessage(error: unknown): string {
  const status = errorStatus(error);
  const detail = error instanceof Error && error.message ? ` (${error.message})` : '';
  if (status === 429) return 'Too many requests. Wait a minute and try again.';
  if (!status) return `Could not reach the sign-in service${detail}. Check your connection.`;
  return `The sign-in service could not send the email${detail}. Try again shortly.`;
}

export default function SignInScreen() {
  const { mode } = useAuth();
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <View style={styles.inner}>
        <Text style={styles.title}>Nosh</Text>
        <Text style={styles.subtitle}>Try more good restaurants nearby.</Text>
        {mode === 'supabase' ? <EmailCodeSignIn /> : <LocalDevSignIn />}
      </View>
    </KeyboardAvoidingView>
  );
}

function EmailCodeSignIn() {
  const { requestEmailCode, verifyEmailCode } = useAuth();
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);

  const sendCode = async () => {
    if (!EMAIL_PATTERN.test(email.trim())) {
      Alert.alert('Enter a valid email address');
      return;
    }
    setBusy(true);
    try {
      await requestEmailCode(email);
      setCode('');
      setStep('code');
    } catch (error) {
      Alert.alert('Could not send a code', sendCodeErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    if (!CODE_PATTERN.test(code.trim())) {
      Alert.alert('Enter the code from the email');
      return;
    }
    setBusy(true);
    try {
      await verifyEmailCode(email, code);
      router.replace('/(app)');
    } catch {
      Alert.alert('That code did not work', 'Check the code or request a new one.');
    } finally {
      setBusy(false);
    }
  };

  if (step === 'email') {
    return (
      <>
        <TextInput
          style={styles.input}
          placeholder="you@example.com"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          returnKeyType="send"
          onSubmitEditing={sendCode}
        />
        <TouchableOpacity
          style={[styles.btn, busy && styles.btnDisabled]}
          onPress={sendCode}
          disabled={busy}
        >
          <Text style={styles.btnText}>{busy ? 'Sending…' : 'Email me a sign-in code'}</Text>
        </TouchableOpacity>
        <Text style={styles.note}>No password needed.</Text>
      </>
    );
  }

  return (
    <>
      <Text style={styles.note}>Enter the code we emailed you.</Text>
      <TextInput
        style={styles.input}
        placeholder="Sign-in code"
        value={code}
        onChangeText={setCode}
        keyboardType="number-pad"
        textContentType="oneTimeCode"
        autoComplete="one-time-code"
        maxLength={10}
        returnKeyType="go"
        onSubmitEditing={verify}
      />
      <TouchableOpacity
        style={[styles.btn, busy && styles.btnDisabled]}
        onPress={verify}
        disabled={busy}
      >
        <Text style={styles.btnText}>{busy ? 'Signing in…' : 'Sign in'}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={sendCode} disabled={busy}>
        <Text style={styles.link}>Send a new code</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => setStep('email')} disabled={busy}>
        <Text style={styles.link}>Use a different email</Text>
      </TouchableOpacity>
    </>
  );
}

function LocalDevSignIn() {
  const { signInLocal } = useAuth();
  const [userId, setUserId] = useState('');
  const [busy, setBusy] = useState(false);

  const signIn = async () => {
    if (!UUID_PATTERN.test(userId.trim())) {
      Alert.alert('Enter a user UUID');
      return;
    }
    setBusy(true);
    try {
      await signInLocal(userId);
      router.replace('/(app)');
    } catch {
      Alert.alert('Sign-in failed', 'Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <TextInput
        style={styles.input}
        placeholder="User UUID (local dev)"
        value={userId}
        onChangeText={setUserId}
        autoCapitalize="none"
        autoCorrect={false}
        returnKeyType="go"
        onSubmitEditing={signIn}
      />
      <TouchableOpacity
        style={[styles.btn, busy && styles.btnDisabled]}
        onPress={signIn}
        disabled={busy}
      >
        <Text style={styles.btnText}>{busy ? 'Signing in…' : 'Sign in'}</Text>
      </TouchableOpacity>
      <Text style={styles.note}>
        Local dev: Supabase is not configured, so any UUID signs in (the API must run with
        AUTH_LOCAL_DEV=true).
      </Text>
    </>
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
  note: { fontSize: 13, color: '#888', textAlign: 'center' },
  link: { fontSize: 15, color: '#555', textAlign: 'center', textDecorationLine: 'underline' },
});
