import React, { useCallback, useEffect, useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import { adherenceAPI } from '../services/api';
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

type Route = RouteProp<RootStackParamList, 'AdherenceDashboard'>;

function scoreColor(score: number): string {
  if (score >= 80) return COLORS.primary;
  if (score >= 50) return COLORS.warning;
  return COLORS.danger;
}

function scoreLabel(score: number): { text: string; color: string; bg: string } {
  if (score >= 80) return { text: 'On Track', color: COLORS.primaryDark, bg: COLORS.primaryLight };
  if (score >= 50) return { text: 'Needs Attention', color: '#92400E', bg: '#FEF3C7' };
  return { text: 'At Risk', color: '#991B1B', bg: '#FEE2E2' };
}

function trendIcon(trend?: string): string {
  if (trend === 'improving') return '↑ Improving';
  if (trend === 'declining') return '↓ Declining';
  return '→ Stable';
}

function trendColor(trend?: string): string {
  if (trend === 'improving') return COLORS.primary;
  if (trend === 'declining') return COLORS.danger;
  return COLORS.warning;
}

// Simple 7-bar chart using Views
function BarChart({ bars }: { bars: { pct: number; color: string }[] }) {
  const MAX_HEIGHT = 60;
  return (
    <View style={barStyles.container}>
      {bars.map((bar, i) => (
        <View key={i} style={barStyles.barWrap}>
          <View
            style={[
              barStyles.bar,
              {
                height: Math.max(4, (bar.pct / 100) * MAX_HEIGHT),
                backgroundColor: bar.color,
              },
            ]}
          />
          <Text style={barStyles.dayLabel}>
            {['M', 'T', 'W', 'T', 'F', 'S', 'S'][i] ?? ''}
          </Text>
        </View>
      ))}
    </View>
  );
}

const barStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    height: 80,
    marginTop: 8,
  },
  barWrap: { flex: 1, alignItems: 'center', justifyContent: 'flex-end', marginHorizontal: 2 },
  bar: { width: '100%', borderRadius: 3, minHeight: 4 },
  dayLabel: { fontSize: 10, color: COLORS.textSecondary, marginTop: 4 },
});

// Build 7-bar data from rolling adherence — backend returns days: [{date, adherence_pct}]
function buildBars(rolling: any): { pct: number; color: string }[] {
  const barColor = (pct: number) =>
    pct >= 80 ? COLORS.primary : pct >= 40 ? COLORS.warning : COLORS.danger;
  const fallback = (pct: number) => ({ pct, color: barColor(pct) });

  if (!rolling) return Array(7).fill({ pct: 0, color: COLORS.border });

  const days: any[] = rolling.days ?? [];
  if (days.length > 0) {
    const last7 = days.slice(-7);
    const padded = Array(7 - last7.length).fill({ pct: 0, color: COLORS.border });
    return [...padded, ...last7.map((d: any) => fallback(d.adherence_pct ?? 0))];
  }

  const avg = rolling.average_pct ?? 0;
  return Array(7).fill(fallback(avg));
}

export default function AdherenceDashboard() {
  const route = useRoute<Route>();
  const { memberId, memberName } = route.params;

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchReport = useCallback(async () => {
    try {
      const res = await adherenceAPI.getReport(memberId);
      setReport(res.data);
    } catch {
      // show empty state
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [memberId]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  if (loading) return <LoadingOverlay visible message="Loading dashboard…" />;

  const score = report?.overall_pct ?? 0;
  const sColor = scoreColor(score);
  const sLabel = scoreLabel(score);
  const rolling = report?.nutrition?.rolling_7day ?? report?.strength?.rolling_7day;
  const nutrition = report?.nutrition ?? {};
  const strength = report?.strength ?? {};
  const clinical = report?.clinical ?? {};

  // Week number from program (approximate from day_number)
  const weekNum = Math.ceil((report?.day_number ?? 1) / 7);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => { setRefreshing(true); fetchReport(); }}
          tintColor={COLORS.primary}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.memberName}>{memberName}</Text>
        {weekNum > 0 && (
          <Text style={styles.weekSub}>Week {weekNum} of 13</Text>
        )}
      </View>

      {/* Overall score card */}
      <View style={styles.scoreCard}>
        <Text style={[styles.scoreBig, { color: sColor }]}>
          {Math.round(score)}%
        </Text>
        <View style={[styles.labelBadge, { backgroundColor: sLabel.bg }]}>
          <Text style={[styles.labelBadgeText, { color: sLabel.color }]}>
            {sLabel.text}
          </Text>
        </View>
        {rolling && (
          <Text style={[styles.trendText, { color: trendColor(rolling.trend) }]}>
            {trendIcon(rolling.trend)}
          </Text>
        )}
        <Text style={styles.weightNote}>
          Nutrition 40% · Strength 40% · Clinical 20%
        </Text>
      </View>

      {/* Nutrition card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🥗 Nutrition</Text>
        <View style={styles.dataRow}>
          <Text style={styles.dataLabel}>Calories</Text>
          <Text style={styles.dataValue}>
            {nutrition.today_calories_actual ?? '--'} / {nutrition.today_calories_target ?? '--'} kcal
          </Text>
        </View>
        <ProgressBar
          value={nutrition.today_adherence_pct ?? 0}
          color={COLORS.primary}
          showLabel={false}
        />
        <View style={[styles.dataRow, { marginTop: 12 }]}>
          <Text style={styles.dataLabel}>Protein</Text>
          <Text style={styles.dataValue}>
            {nutrition.today_protein_actual ?? '--'} / {nutrition.today_protein_target ?? '--'} g
          </Text>
        </View>
        <ProgressBar
          value={
            nutrition.today_protein_target
              ? Math.min(100, ((nutrition.today_protein_actual ?? 0) / nutrition.today_protein_target) * 100)
              : 0
          }
          color={COLORS.primary}
          showLabel={false}
        />
        {rolling && (
          <Text style={[styles.trendSmall, { color: trendColor(rolling.trend) }]}>
            {trendIcon(rolling.trend)}
          </Text>
        )}
      </View>

      {/* Strength card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>💪 Strength</Text>
        <View style={styles.dataRow}>
          <Text style={styles.dataLabel}>Sessions this week</Text>
          <Text style={styles.dataValue}>
            {strength.sessions_this_week ?? '--'} / {strength.target_sessions ?? '--'}
          </Text>
        </View>
        <ProgressBar
          value={strength.week_adherence_pct ?? 0}
          color="#3B82F6"
          showLabel={false}
        />
        <Text style={styles.barChartLabel}>7-Day Trend</Text>
        <BarChart bars={buildBars(rolling)} />
        <View style={styles.barLegend}>
          {[
            { color: COLORS.primary, label: 'Met' },
            { color: COLORS.warning, label: 'Partial' },
            { color: COLORS.danger, label: 'Missed' },
          ].map(({ color, label }) => (
            <View key={label} style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: color }]} />
              <Text style={styles.legendText}>{label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Clinical card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🏥 Clinical</Text>
        <View style={styles.dataRow}>
          <Text style={styles.dataLabel}>Measurements this week</Text>
          <Text style={styles.dataValue}>
            {clinical.measurements_this_week ?? '--'} / {clinical.target_measurements ?? '--'}
          </Text>
        </View>
        <ProgressBar
          value={clinical.week_adherence_pct ?? 0}
          color="#8B5CF6"
          showLabel={false}
        />
        <View style={styles.clinicalStats}>
          <View style={styles.clinicalStat}>
            <Text style={styles.clinicalStatLabel}>Latest BP</Text>
            <Text style={styles.clinicalStatValue}>
              {clinical.latest_bp ?? '--'}
            </Text>
          </View>
          <View style={styles.clinicalDivider} />
          <View style={styles.clinicalStat}>
            <Text style={styles.clinicalStatLabel}>Weight</Text>
            <Text style={styles.clinicalStatValue}>
              {clinical.latest_weight_kg != null
                ? `${clinical.latest_weight_kg} kg`
                : '--'}
            </Text>
          </View>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  header: { marginBottom: 16 },
  memberName: { fontSize: 22, fontWeight: '800', color: COLORS.text },
  weekSub: { fontSize: 13, color: COLORS.textSecondary, marginTop: 2 },
  scoreCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 3,
  },
  scoreBig: { fontSize: 64, fontWeight: '900', lineHeight: 72 },
  labelBadge: {
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 6,
    marginTop: 8,
    marginBottom: 8,
  },
  labelBadgeText: { fontSize: 14, fontWeight: '700' },
  trendText: { fontSize: 14, fontWeight: '700', marginBottom: 8 },
  weightNote: { fontSize: 11, color: COLORS.textSecondary, textAlign: 'center' },
  card: {
    backgroundColor: COLORS.white,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: { fontSize: 16, fontWeight: '800', color: COLORS.text, marginBottom: 14 },
  dataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  dataLabel: { fontSize: 13, color: COLORS.textSecondary, fontWeight: '500' },
  dataValue: { fontSize: 13, color: COLORS.text, fontWeight: '700' },
  trendSmall: { fontSize: 12, fontWeight: '700', marginTop: 10 },
  barChartLabel: { fontSize: 12, color: COLORS.textSecondary, marginTop: 14, fontWeight: '600' },
  barLegend: { flexDirection: 'row', gap: 16, marginTop: 8 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 11, color: COLORS.textSecondary },
  clinicalStats: {
    flexDirection: 'row',
    marginTop: 14,
    backgroundColor: COLORS.background,
    borderRadius: 10,
    padding: 14,
  },
  clinicalStat: { flex: 1, alignItems: 'center' },
  clinicalStatLabel: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 4 },
  clinicalStatValue: { fontSize: 18, fontWeight: '800', color: COLORS.text },
  clinicalDivider: { width: 1, backgroundColor: COLORS.border, marginVertical: 4 },
});
