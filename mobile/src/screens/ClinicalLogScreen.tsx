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
import { measurementsAPI } from '../services/api';
import { cardShadow, scrollViewStyle } from '../utils/platform';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#8B5CF6',
  primaryLight: '#EDE9FE',
  primaryDark: '#4C1D95',
  success: '#10B981',
  danger: '#EF4444',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Route = RouteProp<RootStackParamList, 'ClinicalLog'>;
type Nav = StackNavigationProp<RootStackParamList>;
type MeasurementType = 'blood_pressure' | 'weight' | 'glucose';

const MEASURE_TYPES: { key: MeasurementType; label: string; emoji: string }[] = [
  { key: 'blood_pressure', label: 'Blood Pressure', emoji: '❤️' },
  { key: 'weight', label: 'Weight', emoji: '⚖️' },
  { key: 'glucose', label: 'Glucose', emoji: '🩸' },
];

export default function ClinicalLogScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId, memberName, programId } = route.params;

  const [measureType, setMeasureType] = useState<MeasurementType>('blood_pressure');
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [weightKg, setWeightKg] = useState('');
  const [glucoseMgdl, setGlucoseMgdl] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const validate = (): string | null => {
    if (measureType === 'blood_pressure') {
      if (!systolic || !diastolic) return 'Enter both systolic and diastolic values.';
      const s = parseInt(systolic, 10);
      const d = parseInt(diastolic, 10);
      if (isNaN(s) || s < 50 || s > 250) return 'Systolic BP should be between 50–250 mmHg.';
      if (isNaN(d) || d < 30 || d > 150) return 'Diastolic BP should be between 30–150 mmHg.';
    }
    if (measureType === 'weight') {
      if (!weightKg) return 'Enter weight.';
      const w = parseFloat(weightKg);
      if (isNaN(w) || w < 1 || w > 500) return 'Enter a valid weight in kg.';
    }
    if (measureType === 'glucose') {
      if (!glucoseMgdl) return 'Enter glucose level.';
      const g = parseFloat(glucoseMgdl);
      if (isNaN(g) || g < 10 || g > 600) return 'Enter a valid glucose level (mg/dL).';
    }
    return null;
  };

  const handleSubmit = async () => {
    const err = validate();
    if (err) {
      Alert.alert('Validation Error', err);
      return;
    }

    setSubmitting(true);
    try {
      const payload: any = {
        program_id: programId,
        measurement_type: measureType,
        notes: notes.trim() || null,
        measured_at: new Date().toISOString(),
      };

      if (measureType === 'blood_pressure') {
        payload.systolic_bp = parseInt(systolic, 10);
        payload.diastolic_bp = parseInt(diastolic, 10);
      } else if (measureType === 'weight') {
        payload.weight_kg = parseFloat(weightKg);
      } else if (measureType === 'glucose') {
        payload.glucose_mgdl = parseFloat(glucoseMgdl);
      }

      await measurementsAPI.log(memberId, payload);

      const summary = measureType === 'blood_pressure'
        ? `${systolic}/${diastolic} mmHg`
        : measureType === 'weight'
        ? `${weightKg} kg`
        : `${glucoseMgdl} mg/dL`;

      Alert.alert('Measurement Saved!', `Recorded: ${summary}`, [
        {
          text: 'View Dashboard',
          onPress: () => navigation.navigate('AdherenceDashboard', { memberId, memberName }),
        },
        { text: 'Log Another', onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      Alert.alert(
        'Log Failed',
        err?.response?.data?.detail ?? 'Could not save measurement. Please try again.'
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
      {/* Measurement type selector */}
      <Text style={styles.sectionLabel}>Measurement Type</Text>
      <View style={styles.typeRow}>
        {MEASURE_TYPES.map(({ key, label, emoji }) => {
          const active = measureType === key;
          return (
            <TouchableOpacity
              key={key}
              style={[styles.typeBtn, active && styles.typeBtnActive]}
              onPress={() => setMeasureType(key)}
              disabled={submitting}
            >
              <Text style={styles.typeEmoji}>{emoji}</Text>
              <Text style={[styles.typeLabel, active && styles.typeLabelActive]}>{label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Blood Pressure fields */}
      {measureType === 'blood_pressure' && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>❤️ Blood Pressure (mmHg)</Text>
          <View style={styles.bpRow}>
            <View style={styles.bpField}>
              <Text style={styles.fieldLabel}>Systolic</Text>
              <TextInput
                style={styles.bpInput}
                value={systolic}
                onChangeText={setSystolic}
                placeholder="120"
                keyboardType="numeric"
                editable={!submitting}
                placeholderTextColor={COLORS.textSecondary}
              />
              <Text style={styles.fieldUnit}>mmHg</Text>
            </View>
            <Text style={styles.bpDivider}>/</Text>
            <View style={styles.bpField}>
              <Text style={styles.fieldLabel}>Diastolic</Text>
              <TextInput
                style={styles.bpInput}
                value={diastolic}
                onChangeText={setDiastolic}
                placeholder="80"
                keyboardType="numeric"
                editable={!submitting}
                placeholderTextColor={COLORS.textSecondary}
              />
              <Text style={styles.fieldUnit}>mmHg</Text>
            </View>
          </View>
          <View style={styles.referenceBox}>
            <Text style={styles.referenceText}>Normal: 90/60 – 120/80 mmHg</Text>
          </View>
        </View>
      )}

      {/* Weight field */}
      {measureType === 'weight' && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>⚖️ Body Weight</Text>
          <View style={styles.singleFieldRow}>
            <TextInput
              style={[styles.singleInput]}
              value={weightKg}
              onChangeText={setWeightKg}
              placeholder="70.5"
              keyboardType="numeric"
              editable={!submitting}
              placeholderTextColor={COLORS.textSecondary}
            />
            <View style={styles.unitBadge}>
              <Text style={styles.unitBadgeText}>kg</Text>
            </View>
          </View>
        </View>
      )}

      {/* Glucose field */}
      {measureType === 'glucose' && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🩸 Blood Glucose</Text>
          <View style={styles.singleFieldRow}>
            <TextInput
              style={styles.singleInput}
              value={glucoseMgdl}
              onChangeText={setGlucoseMgdl}
              placeholder="100"
              keyboardType="numeric"
              editable={!submitting}
              placeholderTextColor={COLORS.textSecondary}
            />
            <View style={styles.unitBadge}>
              <Text style={styles.unitBadgeText}>mg/dL</Text>
            </View>
          </View>
          <View style={styles.referenceBox}>
            <Text style={styles.referenceText}>Fasting normal: 70–100 mg/dL</Text>
          </View>
        </View>
      )}

      {/* Notes */}
      <Text style={[styles.sectionLabel, { marginTop: 8 }]}>Notes (optional)</Text>
      <TextInput
        style={[styles.input, styles.notesInput]}
        value={notes}
        onChangeText={setNotes}
        placeholder="Any observations or context..."
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
          <Text style={styles.submitBtnText}>🏥 Save Measurement</Text>
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
  },
  typeRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  typeBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    backgroundColor: COLORS.white,
  },
  typeBtnActive: { borderColor: COLORS.primary, backgroundColor: COLORS.primaryLight },
  typeEmoji: { fontSize: 22, marginBottom: 4 },
  typeLabel: { fontSize: 10, color: COLORS.textSecondary, fontWeight: '600', textAlign: 'center' },
  typeLabelActive: { color: COLORS.primaryDark },
  card: {
    backgroundColor: COLORS.white,
    borderRadius: 14,
    padding: 18,
    marginBottom: 16,
    ...cardShadow('sm'),
  },
  cardTitle: { fontSize: 15, fontWeight: '700', color: COLORS.text, marginBottom: 16 },
  bpRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  bpField: { flex: 1, alignItems: 'center' },
  fieldLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    fontWeight: '600',
    marginBottom: 6,
    alignSelf: 'flex-start',
  },
  bpInput: {
    width: '100%',
    backgroundColor: COLORS.background,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 28,
    fontWeight: '700',
    color: COLORS.text,
    textAlign: 'center',
  },
  fieldUnit: { fontSize: 11, color: COLORS.textSecondary, marginTop: 4 },
  bpDivider: { fontSize: 32, color: COLORS.textSecondary, fontWeight: '300', marginBottom: 16 },
  referenceBox: {
    marginTop: 14,
    backgroundColor: COLORS.primaryLight,
    borderRadius: 8,
    padding: 10,
  },
  referenceText: { fontSize: 12, color: COLORS.primaryDark, textAlign: 'center', fontWeight: '500' },
  singleFieldRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  singleInput: {
    flex: 1,
    backgroundColor: COLORS.background,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 32,
    fontWeight: '700',
    color: COLORS.text,
    textAlign: 'center',
  },
  unitBadge: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  unitBadgeText: { fontSize: 14, fontWeight: '700', color: COLORS.primaryDark },
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
  submitBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
    marginTop: 8,
  },
  submitBtnDisabled: { backgroundColor: '#C4B5FD' },
  submitBtnText: { fontSize: 16, fontWeight: '700', color: COLORS.white },
});
