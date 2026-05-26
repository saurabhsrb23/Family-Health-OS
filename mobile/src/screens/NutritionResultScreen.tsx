import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { mealsAPI, adherenceAPI } from '../services/api';
import ProgressBar from '../components/ProgressBar';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#10B981',
  primaryLight: '#D1FAE5',
  primaryDark: '#065F46',
  warning: '#F59E0B',
  danger: '#EF4444',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Route = RouteProp<RootStackParamList, 'NutritionResult'>;
type Nav = StackNavigationProp<RootStackParamList>;

const MEAL_COLORS: Record<string, string> = {
  breakfast: '#F59E0B',
  lunch: '#10B981',
  dinner: '#3B82F6',
  snack: '#8B5CF6',
};

export default function NutritionResultScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId, mealId, memberName } = route.params;

  const [status, setStatus] = useState<string>('pending');
  const [meal, setMeal] = useState<any>(null);
  const [adherence, setAdherence] = useState<any>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async (mealData: any) => {
    setMeal(mealData);
    try {
      const res = await adherenceAPI.getReport(memberId);
      setAdherence(res.data);
    } catch {
      // adherence optional
    }
  }, [memberId]);

  useEffect(() => {
    let count = 0;
    const poll = async () => {
      try {
        const res = await mealsAPI.getStatus(memberId, mealId);
        const s: string = res.data.extraction_status;
        setStatus(s);
        if (s === 'completed' || s === 'failed') {
          clearInterval(pollRef.current!);
          if (s === 'completed') {
            const mealRes = await mealsAPI.get(memberId, mealId);
            loadData(mealRes.data);
          }
        }
      } catch {
        // ignore
      }
      count++;
      if (count >= 30) clearInterval(pollRef.current!);
    };

    poll();
    pollRef.current = setInterval(poll, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [memberId, mealId, loadData]);

  // Loading state
  if (status === 'pending' || status === 'processing' || (status === 'completed' && !meal)) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.analyzingTitle}>Analyzing your meal…</Text>
        <Text style={styles.analyzingSubtitle}>
          AI is identifying foods and extracting nutrition data
        </Text>
        <View style={styles.statusPill}>
          <Text style={styles.statusPillText}>
            {status === 'pending' ? '⏳ Queued' : '🔍 Processing'}
          </Text>
        </View>
      </View>
    );
  }

  // Failed state
  if (status === 'failed' || !meal) {
    return (
      <View style={styles.centered}>
        <Text style={styles.failEmoji}>❌</Text>
        <Text style={styles.failTitle}>Analysis Failed</Text>
        <Text style={styles.failSub}>
          We couldn't extract nutrition from this image. Try a clearer, well-lit photo.
        </Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.retryBtnText}>Try Another Photo</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Backend returns flat fields on MealLogResponse (not nested extracted_nutrition)
  const calories = meal.calories ?? 0;
  const protein = meal.protein_g ?? 0;
  const carbs = meal.carbs_g ?? 0;
  const fat = meal.fat_g ?? 0;

  const mealColor = MEAL_COLORS[meal.meal_type] ?? COLORS.primary;

  // Adherence impact — backend NutritionAdherence fields
  const proteinTarget = adherence?.nutrition?.today_protein_target ?? 60;
  const proteinLogged = adherence?.nutrition?.today_protein_actual ?? protein;
  const proteinPct = Math.min(100, (proteinLogged / proteinTarget) * 100);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Success header */}
      <View style={styles.successCard}>
        <Text style={styles.successEmoji}>✅</Text>
        <Text style={styles.successTitle}>Meal Logged!</Text>
        <View style={[styles.mealBadge, { backgroundColor: mealColor + '20' }]}>
          <Text style={[styles.mealBadgeText, { color: mealColor }]}>
            {meal.meal_type?.toUpperCase() ?? 'MEAL'}
          </Text>
        </View>
        {!!meal.food_description && (
          <Text style={styles.foodsText}>{meal.food_description}</Text>
        )}
      </View>

      {/* Calorie spotlight */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Total Calories</Text>
        <Text style={styles.calorieValue}>{calories}</Text>
        <Text style={styles.calorieUnit}>kcal</Text>
      </View>

      {/* Macros */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Macronutrients</Text>
        <View style={styles.macroRow}>
          {[
            { label: 'Protein', value: protein, unit: 'g', color: '#3B82F6' },
            { label: 'Carbs', value: carbs, unit: 'g', color: COLORS.warning },
            { label: 'Fat', value: fat, unit: 'g', color: '#8B5CF6' },
          ].map(({ label, value, unit, color }) => (
            <View key={label} style={styles.macroBox}>
              <Text style={[styles.macroValue, { color }]}>{value}</Text>
              <Text style={styles.macroUnit}>{unit}</Text>
              <Text style={styles.macroLabel}>{label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Adherence impact */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Today's Progress</Text>
        <View style={styles.progressLabelRow}>
          <Text style={styles.progressLabelLeft}>Protein</Text>
          <Text style={styles.progressLabelRight}>
            {Math.round(proteinLogged)}g / {proteinTarget}g target
          </Text>
        </View>
        <ProgressBar
          value={proteinPct}
          color={proteinPct >= 80 ? COLORS.primary : proteinPct >= 50 ? COLORS.warning : COLORS.danger}
          showLabel={false}
        />
        <View style={[
          styles.statusBadge,
          { backgroundColor: proteinPct >= 80 ? COLORS.primaryLight : proteinPct >= 50 ? '#FEF3C7' : '#FEE2E2' },
        ]}>
          <Text style={[
            styles.statusBadgeText,
            { color: proteinPct >= 80 ? COLORS.primaryDark : proteinPct >= 50 ? '#92400E' : '#991B1B' },
          ]}>
            {proteinPct >= 80 ? '✓ On Track' : proteinPct >= 50 ? '⚠ Partial' : '↓ Below Target'}
          </Text>
        </View>
      </View>

      {/* Bottom actions */}
      <TouchableOpacity
        style={styles.secondaryBtn}
        onPress={() => navigation.goBack()}
      >
        <Text style={styles.secondaryBtnText}>📷 Log Another Meal</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.primaryBtn}
        onPress={() =>
          navigation.navigate('AdherenceDashboard', {
            memberId,
            memberName,
          })
        }
      >
        <Text style={styles.primaryBtnText}>📊 View Dashboard</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.background,
    padding: 32,
  },
  analyzingTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.text,
    marginTop: 16,
    marginBottom: 6,
  },
  analyzingSubtitle: {
    fontSize: 14,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  statusPill: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  statusPillText: { fontSize: 13, fontWeight: '700', color: COLORS.primaryDark },
  failEmoji: { fontSize: 48, marginBottom: 12 },
  failTitle: { fontSize: 20, fontWeight: '800', color: COLORS.text, marginBottom: 8 },
  failSub: {
    fontSize: 14,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  retryBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingHorizontal: 32,
    paddingVertical: 13,
  },
  retryBtnText: { color: COLORS.white, fontSize: 15, fontWeight: '700' },
  successCard: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 12,
  },
  successEmoji: { fontSize: 40, marginBottom: 8 },
  successTitle: { fontSize: 22, fontWeight: '800', color: COLORS.primaryDark, marginBottom: 8 },
  mealBadge: { borderRadius: 20, paddingHorizontal: 14, paddingVertical: 4, marginBottom: 8 },
  mealBadgeText: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  foodsText: {
    fontSize: 13,
    color: COLORS.primaryDark,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  card: {
    backgroundColor: COLORS.white,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: { fontSize: 14, fontWeight: '700', color: COLORS.textSecondary, marginBottom: 12 },
  calorieValue: { fontSize: 52, fontWeight: '900', color: COLORS.primary, lineHeight: 60 },
  calorieUnit: { fontSize: 16, color: COLORS.textSecondary, marginTop: -4 },
  macroRow: { flexDirection: 'row', justifyContent: 'space-around' },
  macroBox: { alignItems: 'center' },
  macroValue: { fontSize: 28, fontWeight: '800' },
  macroUnit: { fontSize: 13, color: COLORS.textSecondary },
  macroLabel: { fontSize: 12, color: COLORS.textSecondary, marginTop: 2, fontWeight: '600' },
  progressLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  progressLabelLeft: { fontSize: 14, fontWeight: '600', color: COLORS.text },
  progressLabelRight: { fontSize: 12, color: COLORS.textSecondary },
  statusBadge: {
    alignSelf: 'flex-start',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginTop: 10,
  },
  statusBadgeText: { fontSize: 12, fontWeight: '700' },
  secondaryBtn: {
    borderWidth: 1.5,
    borderColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 10,
  },
  secondaryBtnText: { fontSize: 15, fontWeight: '700', color: COLORS.primary },
  primaryBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  primaryBtnText: { fontSize: 15, fontWeight: '700', color: COLORS.white },
});
