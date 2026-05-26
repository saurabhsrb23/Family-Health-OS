import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';

interface ActiveProgram {
  id: string;
  name: string;
  day_number: number;
  days_remaining: number;
}

interface Member {
  id: string;
  full_name: string;
  relationship_type: string;
  date_of_birth?: string;
  active_program?: ActiveProgram | null;
}

interface Props {
  member: Member;
  onPress: () => void;
  onMealPress: () => void;
}

function getAge(dob?: string): string {
  if (!dob) return '';
  const diff = Date.now() - new Date(dob).getTime();
  return `${Math.floor(diff / (365.25 * 24 * 3600 * 1000))} yrs`;
}

const RELATION_COLORS: Record<string, string> = {
  self: '#10B981',
  spouse: '#8B5CF6',
  child: '#F59E0B',
  parent: '#3B82F6',
  sibling: '#EC4899',
};

export default function MemberCard({ member, onPress, onMealPress }: Props) {
  const color = RELATION_COLORS[member.relationship_type] ?? '#6B7280';
  const prog = member.active_program;

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.header}>
        <View style={[styles.avatar, { backgroundColor: color }]}>
          <Text style={styles.avatarText}>{member.full_name[0].toUpperCase()}</Text>
        </View>
        <View style={styles.info}>
          <Text style={styles.name}>{member.full_name}</Text>
          <View style={styles.meta}>
            <View style={[styles.badge, { backgroundColor: color + '20' }]}>
              <Text style={[styles.badgeText, { color }]}>
                {member.relationship_type}
              </Text>
            </View>
            {member.date_of_birth && (
              <Text style={styles.age}>{getAge(member.date_of_birth)}</Text>
            )}
          </View>
        </View>
      </View>

      {prog ? (
        <View style={styles.programBox}>
          <Text style={styles.programName} numberOfLines={1}>{prog.name}</Text>
          <Text style={styles.programDay}>Day {prog.day_number} · {prog.days_remaining} days left</Text>
          <View style={styles.track}>
            <View
              style={[
                styles.fill,
                { width: `${Math.min(100, (prog.day_number / 90) * 100)}%`, backgroundColor: color },
              ]}
            />
          </View>
        </View>
      ) : (
        <Text style={styles.noProgram}>No active program</Text>
      )}

      <TouchableOpacity
        style={[styles.mealBtn, { borderColor: color }]}
        onPress={onMealPress}
        activeOpacity={0.7}
      >
        <Text style={[styles.mealBtnText, { color }]}>📷 Log Meal</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  avatarText: { color: '#FFFFFF', fontSize: 20, fontWeight: '700' },
  info: { flex: 1 },
  name: { fontSize: 16, fontWeight: '700', color: '#111827' },
  meta: { flexDirection: 'row', alignItems: 'center', marginTop: 4, gap: 8 },
  badge: { borderRadius: 4, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { fontSize: 12, fontWeight: '600', textTransform: 'capitalize' },
  age: { fontSize: 12, color: '#9CA3AF' },
  programBox: { marginBottom: 12 },
  programName: { fontSize: 14, fontWeight: '600', color: '#374151', marginBottom: 2 },
  programDay: { fontSize: 12, color: '#6B7280', marginBottom: 6 },
  track: { height: 6, backgroundColor: '#E5E7EB', borderRadius: 3, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 3 },
  noProgram: { fontSize: 13, color: '#9CA3AF', marginBottom: 12, fontStyle: 'italic' },
  mealBtn: {
    borderWidth: 1.5,
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  mealBtnText: { fontSize: 14, fontWeight: '600' },
});
