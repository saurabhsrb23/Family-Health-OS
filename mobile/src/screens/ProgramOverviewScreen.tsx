import React, { useCallback, useEffect, useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { programsAPI, adherenceAPI } from '../services/api';
import ProgressBar from '../components/ProgressBar';
import { LoadingOverlay } from '../components/LoadingOverlay';
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

type Route = RouteProp<RootStackParamList, 'ProgramOverview'>;
type Nav = StackNavigationProp<RootStackParamList>;

const COMPONENT_META: Record<string, { icon: string; label: string; color: string }> = {
  nutrition: { icon: '🥗', label: 'Nutrition', color: COLORS.primary },
  strength: { icon: '💪', label: 'Strength Training', color: '#3B82F6' },
  clinical: { icon: '🏥', label: 'Clinical Monitoring', color: '#8B5CF6' },
};

function adherenceColor(rate: number): string {
  if (rate >= 80) return COLORS.primary;
  if (rate >= 50) return COLORS.warning;
  return COLORS.danger;
}

function adherenceLabel(rate: number): string {
  if (rate >= 80) return 'Met';
  if (rate >= 40) return 'Partial';
  return 'Missed';
}

function phaseLabel(dayNumber: number): string {
  if (dayNumber <= 30) return 'Phase 1 — Foundation';
  if (dayNumber <= 60) return 'Phase 2 — Build';
  return 'Phase 3 — Sustain';
}

export default function ProgramOverviewScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId, memberName, programId } = route.params;

  const [program, setProgram] = useState<any>(null);
  const [adherence, setAdherence] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      let prog: any = null;
      if (programId) {
        const res = await programsAPI.get(memberId, programId);
        prog = res.data;
      } else {
        // No programId passed — fetch list and use first active
        const res = await programsAPI.list(memberId);
        const all: any[] = res.data.data ?? res.data.items ?? res.data;
        prog = all.find((p) => p.status === 'active') ?? all[0] ?? null;
      }
      setProgram(prog);

      const adhRes = await adherenceAPI.getReport(memberId);
      setAdherence(adhRes.data);
    } catch (err) {
      // silently show whatever loaded
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [memberId, programId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <LoadingOverlay visible message="Loading program…" />;

  if (!program) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyEmoji}>📋</Text>
        <Text style={styles.emptyTitle}>No active program</Text>
        <Text style={styles.emptySub}>
          {memberName} doesn't have an active care program yet.
        </Text>
      </View>
    );
  }

  const dayNumber = program.day_number ?? 1;
  const daysRemaining = program.days_remaining ?? (90 - dayNumber);
  const progress = Math.min(100, (dayNumber / 90) * 100);
  const components: any[] = program.components ?? [];

  // Map adherence rates per component type from the report
  // Backend: nutrition.today_adherence_pct, strength/clinical.week_adherence_pct
  const rateFor = (type: string): number => {
    if (!adherence) return 0;
    if (type === 'nutrition') return adherence.nutrition?.today_adherence_pct ?? 0;
    if (type === 'strength') return adherence.strength?.week_adherence_pct ?? 0;
    if (type === 'clinical') return adherence.clinical?.week_adherence_pct ?? 0;
    return 0;
  };

  return (
    <>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); fetchData(); }}
            tintColor={COLORS.primary}
          />
        }
      >
        {/* Program header */}
        <View style={styles.headerCard}>
          <View style={styles.headerTop}>
            <View style={styles.phaseBadge}>
              <Text style={styles.phaseText}>{phaseLabel(dayNumber)}</Text>
            </View>
            <View style={[
              styles.statusBadge,
              { backgroundColor: program.status === 'active' ? COLORS.primaryLight : '#FEF3C7' },
            ]}>
              <Text style={[
                styles.statusText,
                { color: program.status === 'active' ? COLORS.primaryDark : '#92400E' },
              ]}>
                {program.status ?? 'active'}
              </Text>
            </View>
          </View>
          <Text style={styles.programName}>{program.title ?? program.name}</Text>

          {/* Day progress */}
          <View style={styles.dayRow}>
            <Text style={styles.dayNumber}>Day {dayNumber}</Text>
            <Text style={styles.dayOf}>of 90</Text>
          </View>
          <ProgressBar value={progress} color={COLORS.primary} showLabel={false} />
          <Text style={styles.daysRemaining}>{daysRemaining} days remaining</Text>
        </View>

        {/* Component cards */}
        {components.map((comp: any) => {
          const meta = COMPONENT_META[comp.component_type] ?? {
            icon: '📊',
            label: comp.component_type,
            color: COLORS.primary,
          };
          const rate = rateFor(comp.component_type);
          const aColor = adherenceColor(rate);

          return (
            <View key={comp.id} style={styles.compCard}>
              <View style={styles.compHeader}>
                <Text style={styles.compIcon}>{meta.icon}</Text>
                <Text style={styles.compLabel}>{meta.label}</Text>
                <View style={[styles.adherenceBadge, { backgroundColor: aColor + '20' }]}>
                  <Text style={[styles.adherenceBadgeText, { color: aColor }]}>
                    {adherenceLabel(rate)}
                  </Text>
                </View>
              </View>
              <ProgressBar
                value={rate}
                color={meta.color}
                label="Today's adherence"
                showLabel
              />
            </View>
          );
        })}

        {/* View Dashboard */}
        <TouchableOpacity
          style={styles.dashBtn}
          onPress={() =>
            navigation.navigate('AdherenceDashboard', { memberId, memberName })
          }
        >
          <Text style={styles.dashBtnText}>📊 View Full Dashboard</Text>
        </TouchableOpacity>

        {/* Spacer for FAB */}
        <View style={{ height: 80 }} />
      </ScrollView>

      {/* FAB — Log Meal */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('MealCapture', { memberId, memberName, programId })}
        activeOpacity={0.85}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 32 },
  headerCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 3,
  },
  headerTop: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  phaseBadge: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  phaseText: { fontSize: 12, fontWeight: '700', color: COLORS.primaryDark },
  statusBadge: { borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4 },
  statusText: { fontSize: 12, fontWeight: '600', textTransform: 'capitalize' },
  programName: {
    fontSize: 20,
    fontWeight: '800',
    color: COLORS.text,
    marginBottom: 16,
    lineHeight: 26,
  },
  dayRow: { flexDirection: 'row', alignItems: 'baseline', gap: 4, marginBottom: 8 },
  dayNumber: { fontSize: 40, fontWeight: '900', color: COLORS.primary },
  dayOf: { fontSize: 16, color: COLORS.textSecondary, fontWeight: '500' },
  daysRemaining: { fontSize: 13, color: COLORS.textSecondary, marginTop: 6 },
  compCard: {
    backgroundColor: COLORS.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  compHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  compIcon: { fontSize: 22, marginRight: 10 },
  compLabel: { flex: 1, fontSize: 15, fontWeight: '700', color: COLORS.text },
  adherenceBadge: { borderRadius: 20, paddingHorizontal: 10, paddingVertical: 3 },
  adherenceBadgeText: { fontSize: 12, fontWeight: '700' },
  dashBtn: {
    borderWidth: 1.5,
    borderColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  dashBtnText: { fontSize: 15, fontWeight: '700', color: COLORS.primary },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  fabText: { fontSize: 28, color: COLORS.white, lineHeight: 32 },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.background,
    padding: 32,
  },
  emptyEmoji: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: COLORS.text, marginBottom: 8 },
  emptySub: { fontSize: 14, color: COLORS.textSecondary, textAlign: 'center', lineHeight: 20 },
});
