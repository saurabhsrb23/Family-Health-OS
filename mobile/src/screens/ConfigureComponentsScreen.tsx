import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RouteProp } from '@react-navigation/native';
import { programsAPI } from '../services/api';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#10B981',
  primaryLight: '#D1FAE5',
  primaryDark: '#065F46',
  blue: '#3B82F6',
  purple: '#8B5CF6',
  danger: '#EF4444',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Nav = StackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'ConfigureComponents'>;

function OptionButtons({
  options,
  selected,
  onSelect,
}: {
  options: string[];
  selected: string;
  onSelect: (v: string) => void;
}) {
  return (
    <View style={styles.buttonRow}>
      {options.map((o) => (
        <TouchableOpacity
          key={o}
          style={[styles.selectBtn, selected === o && styles.selectBtnActive]}
          onPress={() => onSelect(o)}
        >
          <Text
            style={[
              styles.selectBtnText,
              selected === o && styles.selectBtnTextActive,
            ]}
          >
            {o}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

function SuffixInput({
  value,
  onChangeText,
  suffix,
  keyboardType = 'numeric',
}: {
  value: string;
  onChangeText: (v: string) => void;
  suffix: string;
  keyboardType?: 'numeric' | 'default';
}) {
  return (
    <View style={styles.suffixRow}>
      <TextInput
        style={[styles.input, styles.suffixInput]}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        placeholderTextColor={COLORS.textSecondary}
      />
      <Text style={styles.suffixLabel}>{suffix}</Text>
    </View>
  );
}

export default function ConfigureComponentsScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { memberId, memberName, programTitle, startDate } = route.params;

  // Nutrition
  const [calories, setCalories] = useState('2000');
  const [protein, setProtein] = useState('60');
  const [mealsPerDay, setMealsPerDay] = useState('3');

  // Strength
  const [sessionsPerWeek, setSessionsPerWeek] = useState('4');
  const [sessionDuration, setSessionDuration] = useState('60');

  // Clinical
  const [bpChecks, setBpChecks] = useState('2');
  const [weightChecks, setWeightChecks] = useState('3');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLaunch() {
    setLoading(true);
    setError('');
    try {
      await programsAPI.create(memberId, {
        title: programTitle,
        start_date: startDate,
        nutrition_config: {
          daily_calorie_target: parseInt(calories, 10),
          daily_protein_target_g: parseFloat(protein),
          meals_per_day: parseInt(mealsPerDay, 10),
        },
        strength_config: {
          sessions_per_week: parseInt(sessionsPerWeek, 10),
          session_duration_minutes: parseInt(sessionDuration, 10),
        },
        clinical_config: {
          bp_checks_per_week: parseInt(bpChecks, 10),
          weight_checks_per_week: parseInt(weightChecks, 10),
          checkin_frequency_days: 14,
        },
      });
      navigation.navigate('EnrollmentSuccess', { memberName, programTitle });
    } catch (e: any) {
      setError(
        e?.response?.data?.detail || 'Failed to create program. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.screenTitle}>Configure Program Components</Text>
      <Text style={styles.screenSubtitle}>{programTitle}</Text>

      {/* Nutrition Card */}
      <View style={[styles.card, styles.cardGreen]}>
        <Text style={styles.cardTitle}>🥗 Nutrition</Text>

        <Text style={styles.label}>Daily Calorie Target</Text>
        <SuffixInput value={calories} onChangeText={setCalories} suffix="kcal" />

        <Text style={styles.label}>Daily Protein Target</Text>
        <SuffixInput value={protein} onChangeText={setProtein} suffix="grams" />

        <Text style={styles.label}>Meals Per Day</Text>
        <OptionButtons
          options={['2', '3', '4']}
          selected={mealsPerDay}
          onSelect={setMealsPerDay}
        />
      </View>

      {/* Strength Card */}
      <View style={[styles.card, styles.cardBlue]}>
        <Text style={styles.cardTitle}>💪 Strength Training</Text>

        <Text style={styles.label}>Sessions Per Week</Text>
        <OptionButtons
          options={['2', '3', '4', '5']}
          selected={sessionsPerWeek}
          onSelect={setSessionsPerWeek}
        />

        <Text style={styles.label}>Session Duration</Text>
        <SuffixInput
          value={sessionDuration}
          onChangeText={setSessionDuration}
          suffix="minutes"
        />
      </View>

      {/* Clinical Card */}
      <View style={[styles.card, styles.cardPurple]}>
        <Text style={styles.cardTitle}>🏥 Clinical Monitoring</Text>

        <Text style={styles.label}>BP Checks Per Week</Text>
        <OptionButtons
          options={['1', '2', '3']}
          selected={bpChecks}
          onSelect={setBpChecks}
        />

        <Text style={styles.label}>Weight Checks Per Week</Text>
        <OptionButtons
          options={['1', '2', '3']}
          selected={weightChecks}
          onSelect={setWeightChecks}
        />
      </View>

      {/* Error */}
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {/* Launch Button */}
      <TouchableOpacity
        style={styles.launchBtn}
        onPress={handleLaunch}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color={COLORS.white} />
        ) : (
          <Text style={styles.launchBtnText}>🚀 Launch Program</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingBottom: 40 },

  screenTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.text,
    textAlign: 'center',
    marginTop: 20,
    marginHorizontal: 16,
  },
  screenSubtitle: {
    fontSize: 13,
    color: COLORS.textSecondary,
    textAlign: 'center',
    marginTop: 4,
    marginBottom: 8,
    marginHorizontal: 16,
  },

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
    borderLeftWidth: 4,
  },
  cardGreen: { borderLeftColor: COLORS.primary },
  cardBlue: { borderLeftColor: COLORS.blue },
  cardPurple: { borderLeftColor: COLORS.purple },

  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 12,
  },
  label: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginBottom: 6,
    marginTop: 12,
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
  suffixRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  suffixInput: { flex: 1 },
  suffixLabel: { fontSize: 14, color: COLORS.textSecondary, minWidth: 50 },

  buttonRow: { flexDirection: 'row', gap: 8 },
  selectBtn: {
    flex: 1,
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

  launchBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 16,
  },
  launchBtnText: { color: COLORS.white, fontSize: 17, fontWeight: '700' },
});
