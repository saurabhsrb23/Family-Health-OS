import React, { useCallback, useEffect, useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { membersAPI, adherenceAPI } from '../services/api';
import LoadingOverlay from '../components/LoadingOverlay';
import ProgressBar from '../components/ProgressBar';

interface AdherenceReport {
  overall_score: number;
  nutrition: { score: number; meals_logged: number; target: number };
  strength: { score: number; sessions_completed: number; target: number };
  clinical: { score: number; measurements_taken: number; target: number };
  rolling: { trend: string; current_avg: number; previous_avg: number };
}

const TREND_ICON: Record<string, string> = {
  improving: '📈',
  declining: '📉',
  stable: '➡️',
};

export default function AdherenceDashboard() {
  const [members, setMembers] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [report, setReport] = useState<AdherenceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadMembers = useCallback(async () => {
    try {
      const res = await membersAPI.list();
      const list = res.data.items ?? res.data;
      setMembers(list);
      if (list.length > 0 && !selected) setSelected(list[0]);
    } catch {
      Alert.alert('Error', 'Could not load members.');
    }
  }, [selected]);

  const loadReport = useCallback(async (memberId: string) => {
    setReport(null);
    try {
      const res = await adherenceAPI.getReport(memberId);
      setReport(res.data);
    } catch {
      Alert.alert('Error', 'Could not load adherence report.');
    }
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await loadMembers();
    if (selected) await loadReport(selected.id);
    setRefreshing(false);
  }, [loadMembers, loadReport, selected]);

  useEffect(() => {
    loadMembers().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selected) loadReport(selected.id);
  }, [selected, loadReport]);

  if (loading) return <LoadingOverlay message="Loading dashboard…" />;

  const score = report?.overall_score ?? 0;
  const scoreColor =
    score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : '#EF4444';

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor="#10B981" />
      }
    >
      {/* Member selector */}
      <Text style={styles.sectionLabel}>Family Member</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.memberScroll}>
        {members.map((m) => (
          <TouchableOpacity
            key={m.id}
            style={[styles.memberChip, selected?.id === m.id && styles.memberChipActive]}
            onPress={() => setSelected(m)}
          >
            <Text style={[styles.memberChipText, selected?.id === m.id && styles.memberChipTextActive]}>
              {m.full_name.split(' ')[0]}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {!report ? (
        <View style={styles.empty}>
          <Text style={styles.emptyText}>Loading adherence data…</Text>
        </View>
      ) : (
        <>
          {/* Overall score */}
          <View style={[styles.card, styles.scoreCard]}>
            <Text style={styles.scoreLabel}>Overall Adherence</Text>
            <Text style={[styles.scoreValue, { color: scoreColor }]}>
              {Math.round(score)}%
            </Text>
            <ProgressBar value={score} color={scoreColor} showPercent={false} />
            {report.rolling && (
              <View style={styles.trendRow}>
                <Text style={styles.trendIcon}>
                  {TREND_ICON[report.rolling.trend] ?? '➡️'}
                </Text>
                <Text style={styles.trendText}>
                  7-day trend:{' '}
                  <Text style={{ fontWeight: '700', textTransform: 'capitalize' }}>
                    {report.rolling.trend}
                  </Text>
                  {' '}({Math.round(report.rolling.current_avg)}% vs {Math.round(report.rolling.previous_avg)}%)
                </Text>
              </View>
            )}
          </View>

          {/* Component cards */}
          {[
            {
              key: 'nutrition',
              label: 'Nutrition',
              icon: '🥗',
              color: '#10B981',
              score: report.nutrition?.score ?? 0,
              detail: `${report.nutrition?.meals_logged ?? 0} / ${report.nutrition?.target ?? 0} meals`,
            },
            {
              key: 'strength',
              label: 'Strength Training',
              icon: '💪',
              color: '#3B82F6',
              score: report.strength?.score ?? 0,
              detail: `${report.strength?.sessions_completed ?? 0} / ${report.strength?.target ?? 0} sessions`,
            },
            {
              key: 'clinical',
              label: 'Clinical Monitoring',
              icon: '🩺',
              color: '#8B5CF6',
              score: report.clinical?.score ?? 0,
              detail: `${report.clinical?.measurements_taken ?? 0} / ${report.clinical?.target ?? 0} measurements`,
            },
          ].map(({ key, label, icon, color, score: s, detail }) => (
            <View key={key} style={styles.card}>
              <View style={styles.compHeader}>
                <Text style={styles.compIcon}>{icon}</Text>
                <Text style={styles.compLabel}>{label}</Text>
                <Text style={[styles.compScore, { color }]}>{Math.round(s)}%</Text>
              </View>
              <ProgressBar value={s} color={color} showPercent={false} />
              <Text style={styles.compDetail}>{detail}</Text>
            </View>
          ))}

          {/* Weight note */}
          <View style={styles.weightNote}>
            <Text style={styles.weightNoteText}>
              Score weights: Nutrition 40% · Strength 40% · Clinical 20%
            </Text>
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  content: { padding: 16, paddingBottom: 40 },
  sectionLabel: { fontSize: 13, fontWeight: '700', color: '#374151', marginBottom: 8 },
  memberScroll: { marginBottom: 16 },
  memberChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: '#D1D5DB',
    backgroundColor: '#FFFFFF',
    marginRight: 8,
  },
  memberChipActive: { borderColor: '#10B981', backgroundColor: '#ECFDF5' },
  memberChipText: { fontSize: 13, color: '#6B7280', fontWeight: '600' },
  memberChipTextActive: { color: '#10B981' },
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
  scoreCard: { alignItems: 'center' },
  scoreLabel: { fontSize: 14, color: '#6B7280', fontWeight: '600', marginBottom: 6 },
  scoreValue: { fontSize: 48, fontWeight: '900', marginBottom: 8 },
  trendRow: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 6 },
  trendIcon: { fontSize: 18 },
  trendText: { fontSize: 13, color: '#4B5563' },
  compHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  compIcon: { fontSize: 20, marginRight: 8 },
  compLabel: { flex: 1, fontSize: 14, fontWeight: '700', color: '#374151' },
  compScore: { fontSize: 16, fontWeight: '800' },
  compDetail: { fontSize: 12, color: '#9CA3AF', marginTop: 6 },
  weightNote: {
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  weightNoteText: { fontSize: 11, color: '#6B7280' },
  empty: { alignItems: 'center', marginTop: 40 },
  emptyText: { fontSize: 14, color: '#9CA3AF' },
});
