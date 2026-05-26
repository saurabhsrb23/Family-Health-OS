import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { workoutsAPI } from '../services/api';
import { cardShadow, scrollViewStyle } from '../utils/platform';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#3B82F6',
  primaryLight: '#DBEAFE',
  primaryDark: '#1E3A8A',
  success: '#10B981',
  danger: '#EF4444',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Route = RouteProp<RootStackParamList, 'WorkoutLog'>;
type Nav = StackNavigationProp<RootStackParamList>;

type SessionType = 'strength' | 'cardio' | 'flexibility' | 'yoga';

const SESSION_TYPES: { key: SessionType; label: string; emoji: string }[] = [
  { key: 'strength', label: 'Strength', emoji: '💪' },
  { key: 'cardio', label: 'Cardio', emoji: '🏃' },
  { key: 'flexibility', label: 'Flexibility', emoji: '🧘' },
  { key: 'yoga', label: 'Yoga', emoji: '🕉️' },
];

const ENERGY_LABELS = ['', 'Very Low', 'Low', 'Moderate', 'High', 'Max'];

interface Exercise {
  exercise_name: string;
  sets: string;
  reps: string;
  weight_kg: string;
  duration_seconds: string;
}

function emptyExercise(): Exercise {
  return { exercise_name: '', sets: '', reps: '', weight_kg: '', duration_seconds: '' };
}

export default function WorkoutLogScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId, memberName, programId } = route.params;

  const [sessionType, setSessionType] = useState<SessionType>('strength');
  const [energyLevel, setEnergyLevel] = useState<number>(3);
  const [duration, setDuration] = useState('');
  const [notes, setNotes] = useState('');
  const [exercises, setExercises] = useState<Exercise[]>([emptyExercise()]);
  const [submitting, setSubmitting] = useState(false);

  const addExercise = () => setExercises((prev) => [...prev, emptyExercise()]);

  const removeExercise = (index: number) =>
    setExercises((prev) => prev.filter((_, i) => i !== index));

  const updateExercise = (index: number, field: keyof Exercise, value: string) =>
    setExercises((prev) =>
      prev.map((ex, i) => (i === index ? { ...ex, [field]: value } : ex))
    );

  const handleSubmit = async () => {
    const validExercises = exercises.filter((ex) => ex.exercise_name.trim());
    if (validExercises.length === 0) {
      Alert.alert('Add at least one exercise', 'Enter the exercise name to continue.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        program_id: programId,
        session_type: sessionType,
        energy_level: energyLevel,
        duration_minutes: duration ? parseInt(duration, 10) : null,
        notes: notes.trim() || null,
        logged_at: new Date().toISOString(),
        exercises: validExercises.map((ex) => ({
          exercise_name: ex.exercise_name.trim(),
          sets: ex.sets ? parseInt(ex.sets, 10) : null,
          reps: ex.reps ? parseInt(ex.reps, 10) : null,
          weight_kg: ex.weight_kg ? parseFloat(ex.weight_kg) : null,
          duration_seconds: ex.duration_seconds ? parseInt(ex.duration_seconds, 10) : null,
        })),
      };

      await workoutsAPI.log(memberId, payload);
      Alert.alert('Workout Logged!', `Great work, ${memberName}!`, [
        {
          text: 'View Dashboard',
          onPress: () => navigation.navigate('AdherenceDashboard', { memberId, memberName }),
        },
        { text: 'Log Another', onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      Alert.alert(
        'Log Failed',
        err?.response?.data?.detail ?? 'Could not save workout. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView
      style={[styles.container, scrollViewStyle]}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      {/* Session type */}
      <Text style={styles.sectionLabel}>Session Type</Text>
      <View style={styles.typeRow}>
        {SESSION_TYPES.map(({ key, label, emoji }) => {
          const active = sessionType === key;
          return (
            <TouchableOpacity
              key={key}
              style={[styles.typeBtn, active && styles.typeBtnActive]}
              onPress={() => setSessionType(key)}
              disabled={submitting}
            >
              <Text style={styles.typeEmoji}>{emoji}</Text>
              <Text style={[styles.typeLabel, active && styles.typeLabelActive]}>{label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Energy level */}
      <Text style={styles.sectionLabel}>Energy Level</Text>
      <View style={styles.energyRow}>
        {[1, 2, 3, 4, 5].map((lvl) => (
          <TouchableOpacity
            key={lvl}
            style={[styles.energyBtn, energyLevel === lvl && styles.energyBtnActive]}
            onPress={() => setEnergyLevel(lvl)}
            disabled={submitting}
          >
            <Text style={styles.energyEmoji}>
              {lvl <= energyLevel ? '⚡' : '○'}
            </Text>
          </TouchableOpacity>
        ))}
        <Text style={styles.energyLabel}>{ENERGY_LABELS[energyLevel]}</Text>
      </View>

      {/* Duration */}
      <Text style={styles.sectionLabel}>Duration (minutes)</Text>
      <TextInput
        style={styles.input}
        value={duration}
        onChangeText={setDuration}
        placeholder="e.g. 45"
        keyboardType="numeric"
        editable={!submitting}
        placeholderTextColor={COLORS.textSecondary}
      />

      {/* Exercises */}
      <View style={styles.exercisesHeader}>
        <Text style={styles.sectionLabel}>Exercises</Text>
        <TouchableOpacity onPress={addExercise} disabled={submitting} style={styles.addBtn}>
          <Text style={styles.addBtnText}>+ Add</Text>
        </TouchableOpacity>
      </View>

      {exercises.map((ex, index) => (
        <View key={index} style={styles.exerciseCard}>
          <View style={styles.exerciseCardHeader}>
            <Text style={styles.exerciseNum}>Exercise {index + 1}</Text>
            {exercises.length > 1 && (
              <TouchableOpacity onPress={() => removeExercise(index)} disabled={submitting}>
                <Text style={styles.removeText}>Remove</Text>
              </TouchableOpacity>
            )}
          </View>

          <TextInput
            style={styles.input}
            value={ex.exercise_name}
            onChangeText={(v) => updateExercise(index, 'exercise_name', v)}
            placeholder="Exercise name (e.g. Squats)"
            editable={!submitting}
            placeholderTextColor={COLORS.textSecondary}
          />

          <View style={styles.metricRow}>
            <View style={styles.metricField}>
              <Text style={styles.metricLabel}>Sets</Text>
              <TextInput
                style={styles.metricInput}
                value={ex.sets}
                onChangeText={(v) => updateExercise(index, 'sets', v)}
                placeholder="3"
                keyboardType="numeric"
                editable={!submitting}
                placeholderTextColor={COLORS.textSecondary}
              />
            </View>
            <View style={styles.metricField}>
              <Text style={styles.metricLabel}>Reps</Text>
              <TextInput
                style={styles.metricInput}
                value={ex.reps}
                onChangeText={(v) => updateExercise(index, 'reps', v)}
                placeholder="10"
                keyboardType="numeric"
                editable={!submitting}
                placeholderTextColor={COLORS.textSecondary}
              />
            </View>
            <View style={styles.metricField}>
              <Text style={styles.metricLabel}>Weight (kg)</Text>
              <TextInput
                style={styles.metricInput}
                value={ex.weight_kg}
                onChangeText={(v) => updateExercise(index, 'weight_kg', v)}
                placeholder="60"
                keyboardType="numeric"
                editable={!submitting}
                placeholderTextColor={COLORS.textSecondary}
              />
            </View>
          </View>

          {(sessionType === 'cardio' || sessionType === 'flexibility' || sessionType === 'yoga') && (
            <View style={styles.metricRow}>
              <View style={[styles.metricField, { flex: 1 }]}>
                <Text style={styles.metricLabel}>Duration (seconds)</Text>
                <TextInput
                  style={styles.metricInput}
                  value={ex.duration_seconds}
                  onChangeText={(v) => updateExercise(index, 'duration_seconds', v)}
                  placeholder="60"
                  keyboardType="numeric"
                  editable={!submitting}
                  placeholderTextColor={COLORS.textSecondary}
                />
              </View>
            </View>
          )}
        </View>
      ))}

      {/* Notes */}
      <Text style={styles.sectionLabel}>Notes (optional)</Text>
      <TextInput
        style={[styles.input, styles.notesInput]}
        value={notes}
        onChangeText={setNotes}
        placeholder="How did it go? Any observations..."
        multiline
        numberOfLines={3}
        editable={!submitting}
        placeholderTextColor={COLORS.textSecondary}
      />

      {/* Submit */}
      <TouchableOpacity
        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
        activeOpacity={0.85}
      >
        {submitting ? (
          <ActivityIndicator color={COLORS.white} />
        ) : (
          <Text style={styles.submitBtnText}>💪 Save Workout</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 10,
    marginTop: 4,
  },
  typeRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  typeBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    backgroundColor: COLORS.white,
  },
  typeBtnActive: { borderColor: COLORS.primary, backgroundColor: COLORS.primaryLight },
  typeEmoji: { fontSize: 18, marginBottom: 2 },
  typeLabel: { fontSize: 11, color: COLORS.textSecondary, fontWeight: '600' },
  typeLabelActive: { color: COLORS.primaryDark },
  energyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 20,
  },
  energyBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: COLORS.border,
    backgroundColor: COLORS.white,
  },
  energyBtnActive: { borderColor: COLORS.primary, backgroundColor: COLORS.primaryLight },
  energyEmoji: { fontSize: 16 },
  energyLabel: { fontSize: 12, color: COLORS.textSecondary, fontWeight: '600', marginLeft: 4 },
  input: {
    backgroundColor: COLORS.white,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 15,
    color: COLORS.text,
    marginBottom: 16,
    ...cardShadow('sm'),
  },
  notesInput: { height: 80, textAlignVertical: 'top', paddingTop: 11 },
  exercisesHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  addBtn: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  addBtnText: { fontSize: 13, fontWeight: '700', color: COLORS.primaryDark },
  exerciseCard: {
    backgroundColor: COLORS.white,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    ...cardShadow('sm'),
  },
  exerciseCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  exerciseNum: { fontSize: 13, fontWeight: '700', color: COLORS.primary },
  removeText: { fontSize: 12, color: COLORS.danger, fontWeight: '600' },
  metricRow: { flexDirection: 'row', gap: 10, marginBottom: 4 },
  metricField: { flex: 1 },
  metricLabel: { fontSize: 11, color: COLORS.textSecondary, fontWeight: '600', marginBottom: 4 },
  metricInput: {
    backgroundColor: COLORS.background,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    color: COLORS.text,
  },
  submitBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
    marginTop: 8,
  },
  submitBtnDisabled: { backgroundColor: '#93C5FD' },
  submitBtnText: { fontSize: 16, fontWeight: '700', color: COLORS.white },
});
