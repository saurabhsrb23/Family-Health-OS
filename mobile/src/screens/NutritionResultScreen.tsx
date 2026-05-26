import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { mealsAPI } from '../services/api';
import LoadingOverlay from '../components/LoadingOverlay';
import ProgressBar from '../components/ProgressBar';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Route = RouteProp<RootStackParamList, 'NutritionResult'>;
type Nav = StackNavigationProp<RootStackParamList>;

const POLL_INTERVAL = 2500;
const MAX_POLLS = 20;

export default function NutritionResultScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { mealId, memberId } = route.params;

  const [status, setStatus] = useState<string>('pending');
  const [meal, setMeal] = useState<any>(null);
  const pollCount = useRef(0);

  const poll = useCallback(async () => {
    try {
      const res = await mealsAPI.getStatus(memberId, mealId);
      const data = res.data;
      setStatus(data.status);
      if (data.status === 'completed' || data.status === 'failed') {
        const mealRes = await mealsAPI.get(memberId, mealId);
        setMeal(mealRes.data);
      }
    } catch {
      // silently ignore poll errors
    }
  }, [mealId, memberId]);

  useEffect(() => {
    poll();
    const interval = setInterval(() => {
      pollCount.current += 1;
      if (pollCount.current >= MAX_POLLS) {
        clearInterval(interval);
        setStatus('failed');
        return;
      }
      if (status === 'completed' || status === 'failed') {
        clearInterval(interval);
        return;
      }
      poll();
    }, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [poll, status]);

  if (status === 'pending' || status === 'processing') {
    return (
      <LoadingOverlay
        message={`Analyzing your meal with AI…\n(${status === 'pending' ? 'Queued' : 'Processing'})`}
      />
    );
  }

  if (status === 'failed' || !meal) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorEmoji}>❌</Text>
        <Text style={styles.errorTitle}>Analysis Failed</Text>
        <Text style={styles.errorSub}>Could not extract nutrition from this image.</Text>
        <TouchableOpacity
          style={styles.backBtn}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backBtnText}>Try Again</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const ext = meal.extracted_nutrition ?? {};
  const calories = ext.calories ?? 0;
  const target = 500; // per-meal approx target

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Success header */}
      <View style={styles.successCard}>
        <Text style={styles.successEmoji}>✅</Text>
        <Text style={styles.successTitle}>Meal Logged!</Text>
        <Text style={styles.mealType}>{meal.meal_type?.toUpperCase()}</Text>
      </View>

      {/* Calorie spotlight */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Calories</Text>
        <Text style={styles.calorieValue}>{calories} kcal</Text>
        <ProgressBar
          value={(calories / target) * 100}
          label={`Target: ~${target} kcal/meal`}
          color={calories > target ? '#EF4444' : '#10B981'}
        />
      </View>

      {/* Macros */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Macronutrients</Text>
        {[
          { label: 'Protein', key: 'protein_g', unit: 'g', target: 30, color: '#3B82F6' },
          { label: 'Carbs', key: 'carbohydrates_g', unit: 'g', target: 60, color: '#F59E0B' },
          { label: 'Fat', key: 'fat_g', unit: 'g', target: 20, color: '#8B5CF6' },
          { label: 'Fibre', key: 'fiber_g', unit: 'g', target: 8, color: '#10B981' },
        ].map(({ label, key, unit, target: t, color }) => (
          <View key={key} style={styles.macroRow}>
            <View style={styles.macroLabel}>
              <Text style={styles.macroName}>{label}</Text>
              <Text style={[styles.macroValue, { color }]}>
                {ext[key] ?? '—'} {unit}
              </Text>
            </View>
            <ProgressBar
              value={ext[key] ? (ext[key] / t) * 100 : 0}
              showPercent={false}
              color={color}
            />
          </View>
        ))}
      </View>

      {/* AI foods identified */}
      {ext.foods_identified?.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Foods Identified</Text>
          {ext.foods_identified.map((food: string, i: number) => (
            <Text key={i} style={styles.foodItem}>• {food}</Text>
          ))}
        </View>
      )}

      <TouchableOpacity
        style={styles.doneBtn}
        onPress={() => navigation.navigate('Main')}
      >
        <Text style={styles.doneBtnText}>Done</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  content: { padding: 16, paddingBottom: 40 },
  successCard: {
    alignItems: 'center',
    backgroundColor: '#ECFDF5',
    borderRadius: 12,
    padding: 20,
    marginBottom: 12,
  },
  successEmoji: { fontSize: 40, marginBottom: 8 },
  successTitle: { fontSize: 20, fontWeight: '800', color: '#065F46' },
  mealType: { fontSize: 12, color: '#10B981', fontWeight: '700', marginTop: 4, letterSpacing: 1 },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#374151', marginBottom: 12 },
  calorieValue: { fontSize: 36, fontWeight: '800', color: '#10B981', marginBottom: 8 },
  macroRow: { marginBottom: 10 },
  macroLabel: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  macroName: { fontSize: 13, color: '#374151', fontWeight: '500' },
  macroValue: { fontSize: 13, fontWeight: '700' },
  foodItem: { fontSize: 14, color: '#4B5563', marginBottom: 4 },
  doneBtn: {
    backgroundColor: '#10B981',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  doneBtnText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  errorContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  errorEmoji: { fontSize: 48, marginBottom: 12 },
  errorTitle: { fontSize: 20, fontWeight: '800', color: '#111827', marginBottom: 8 },
  errorSub: { fontSize: 14, color: '#6B7280', textAlign: 'center', marginBottom: 24 },
  backBtn: { backgroundColor: '#10B981', borderRadius: 10, paddingHorizontal: 32, paddingVertical: 12 },
  backBtnText: { color: '#FFFFFF', fontSize: 15, fontWeight: '700' },
});
