import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { membersAPI } from '../services/api';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#10B981',
  primaryLight: '#D1FAE5',
  primaryDark: '#065F46',
  blue: '#3B82F6',
  purple: '#8B5CF6',
  warning: '#F59E0B',
  danger: '#EF4444',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Nav = StackNavigationProp<RootStackParamList>;

const RELATIONSHIPS = ['Self', 'Spouse', 'Parent', 'Child'];
const GENDERS = ['Male', 'Female'];

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0 || parts[0] === '') return '?';
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function AddMemberScreen() {
  const navigation = useNavigation<Nav>();

  const [name, setName] = useState('');
  const [dob, setDob] = useState('');
  const [phone, setPhone] = useState('');
  const [relationship, setRelationship] = useState('');
  const [gender, setGender] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = name.trim().length > 0 && relationship.length > 0;

  async function handleContinue() {
    if (!canSubmit) return;
    setLoading(true);
    setError('');
    try {
      const res = await membersAPI.create({
        name: name.trim(),
        relationship: relationship.toLowerCase(),
        date_of_birth: dob || null,
        gender: gender ? gender.toLowerCase() : null,
        phone: phone || null,
      });
      navigation.navigate('CreateProgram', {
        memberId: res.data.id,
        memberName: name.trim(),
      });
    } catch (e: any) {
      setError(
        e?.response?.data?.detail || 'Failed to add member. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        {/* Avatar */}
        <View style={styles.avatarWrap}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{getInitials(name)}</Text>
          </View>
        </View>

        {/* Member Details */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Member Details</Text>

          <Text style={styles.label}>Full Name *</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Enter full name"
            placeholderTextColor={COLORS.textSecondary}
            autoFocus
          />

          <Text style={styles.label}>Date of Birth</Text>
          <TextInput
            style={styles.input}
            value={dob}
            onChangeText={setDob}
            placeholder="YYYY-MM-DD"
            placeholderTextColor={COLORS.textSecondary}
          />

          <Text style={styles.label}>Phone</Text>
          <TextInput
            style={styles.input}
            value={phone}
            onChangeText={setPhone}
            placeholder="Phone number"
            placeholderTextColor={COLORS.textSecondary}
            keyboardType="phone-pad"
          />
        </View>

        {/* Relationship */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Relationship *</Text>
          <View style={styles.buttonRow}>
            {RELATIONSHIPS.map((r) => (
              <TouchableOpacity
                key={r}
                style={[
                  styles.selectBtn,
                  relationship === r && styles.selectBtnActive,
                ]}
                onPress={() => setRelationship(r)}
              >
                <Text
                  style={[
                    styles.selectBtnText,
                    relationship === r && styles.selectBtnTextActive,
                  ]}
                >
                  {r}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Gender */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Gender</Text>
          <View style={styles.buttonRow}>
            {GENDERS.map((g) => (
              <TouchableOpacity
                key={g}
                style={[
                  styles.selectBtn,
                  gender === g && styles.selectBtnActive,
                ]}
                onPress={() => setGender(gender === g ? '' : g)}
              >
                <Text
                  style={[
                    styles.selectBtnText,
                    gender === g && styles.selectBtnTextActive,
                  ]}
                >
                  {g}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Error */}
        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        {/* Submit */}
        <TouchableOpacity
          style={[styles.primaryBtn, !canSubmit && styles.primaryBtnDisabled]}
          onPress={handleContinue}
          disabled={!canSubmit || loading}
        >
          {loading ? (
            <ActivityIndicator color={COLORS.white} />
          ) : (
            <Text style={styles.primaryBtnText}>Continue →</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingBottom: 40 },

  avatarWrap: { alignItems: 'center', paddingVertical: 24 },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { color: COLORS.white, fontSize: 28, fontWeight: '700' },

  card: {
    backgroundColor: COLORS.white,
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 12,
  },
  label: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginBottom: 4,
    marginTop: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: COLORS.text,
    backgroundColor: COLORS.background,
  },

  buttonRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  selectBtn: {
    flex: 1,
    minWidth: 60,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: COLORS.primary,
    alignItems: 'center',
    backgroundColor: COLORS.white,
  },
  selectBtnActive: { backgroundColor: COLORS.primary },
  selectBtnText: { fontSize: 14, fontWeight: '600', color: COLORS.primary },
  selectBtnTextActive: { color: COLORS.white },

  errorText: {
    color: COLORS.danger,
    fontSize: 13,
    textAlign: 'center',
    marginHorizontal: 16,
    marginTop: 8,
  },

  primaryBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 16,
  },
  primaryBtnDisabled: { backgroundColor: COLORS.border },
  primaryBtnText: { color: COLORS.white, fontSize: 16, fontWeight: '600' },
});
