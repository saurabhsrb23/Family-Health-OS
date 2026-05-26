import React, { useEffect, useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  Alert,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { programsAPI } from '../services/api';
import LoadingOverlay from '../components/LoadingOverlay';
import ProgressBar from '../components/ProgressBar';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Route = RouteProp<RootStackParamList, 'ProgramOverview'>;
type Nav = StackNavigationProp<RootStackParamList>;

const COMPONENT_COLORS: Record<string, string> = {
  nutrition: '#10B981',
  strength: '#3B82F6',
  clinical: '#8B5CF6',
};

export default function ProgramOverviewScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId, memberName } = route.params;

  const [programs, setPrograms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    navigation.setOptions({ title: `${memberName}'s Program` });
    programsAPI.list(memberId)
      .then((res) => setPrograms(res.data.items ?? res.data))
      .catch(() => Alert.alert('Error', 'Could not load programs.'))
      .finally(() => setLoading(false));
  }, [memberId, memberName, navigation]);

  if (loading) return <LoadingOverlay message="Loading program…" />;

  const active = programs.find((p) => p.status === 'active') ?? programs[0];

  if (!active) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No active care program found.</Text>
      </View>
    );
  }

  const progress = Math.min(100, ((active.day_number ?? 1) / 90) * 100);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header card */}
      <View style={styles.card}>
        <Text style={styles.programName}>{active.name}</Text>
        <Text style={styles.phase}>{active.current_phase ?? 'Phase 1'}</Text>

        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{active.day_number ?? 1}</Text>
            <Text style={styles.statLabel}>Day</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statValue}>{active.days_remaining ?? 90}</Text>
            <Text style={styles.statLabel}>Days Left</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statValue}>90</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
        </View>

        <ProgressBar value={progress} label="Overall Progress" color="#10B981" />
      </View>

      {/* Components */}
      {(active.components ?? []).map((comp: any) => {
        const color = COMPONENT_COLORS[comp.component_type] ?? '#6B7280';
        return (
          <View key={comp.id} style={styles.card}>
            <View style={styles.compHeader}>
              <View style={[styles.compBadge, { backgroundColor: color + '20' }]}>
                <Text style={[styles.compBadgeText, { color }]}>
                  {comp.component_type.toUpperCase()}
                </Text>
              </View>
              <Text style={styles.compStatus}>{comp.status}</Text>
            </View>
            <Text style={styles.compTitle}>
              {comp.component_type === 'nutrition'
                ? 'Nutrition Tracking'
                : comp.component_type === 'strength'
                ? 'Strength Training'
                : 'Clinical Monitoring'}
            </Text>
            {comp.config && (
              <View style={styles.configBox}>
                {Object.entries(comp.config).map(([k, v]) => (
                  <Text key={k} style={styles.configRow}>
                    <Text style={styles.configKey}>{k.replace(/_/g, ' ')}: </Text>
                    {String(v)}
                  </Text>
                ))}
              </View>
            )}
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  content: { padding: 16, paddingBottom: 32 },
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
  programName: { fontSize: 18, fontWeight: '800', color: '#111827', marginBottom: 4 },
  phase: { fontSize: 13, color: '#10B981', fontWeight: '600', marginBottom: 16 },
  statsRow: { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 16 },
  stat: { alignItems: 'center' },
  statValue: { fontSize: 24, fontWeight: '800', color: '#10B981' },
  statLabel: { fontSize: 12, color: '#9CA3AF', marginTop: 2 },
  statDivider: { width: 1, backgroundColor: '#E5E7EB', marginVertical: 4 },
  compHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  compBadge: { borderRadius: 4, paddingHorizontal: 10, paddingVertical: 3 },
  compBadgeText: { fontSize: 11, fontWeight: '700' },
  compStatus: { fontSize: 12, color: '#6B7280', textTransform: 'capitalize' },
  compTitle: { fontSize: 15, fontWeight: '700', color: '#374151', marginBottom: 8 },
  configBox: { backgroundColor: '#F9FAFB', borderRadius: 8, padding: 10 },
  configRow: { fontSize: 13, color: '#4B5563', marginBottom: 3 },
  configKey: { fontWeight: '600', textTransform: 'capitalize' },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyText: { fontSize: 15, color: '#9CA3AF' },
});
