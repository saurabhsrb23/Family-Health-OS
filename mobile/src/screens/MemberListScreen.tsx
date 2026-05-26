import React, { useCallback, useEffect, useState } from 'react';
import {
  FlatList,
  View,
  Text,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { membersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import MemberCard from '../components/MemberCard';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#10B981',
  primaryLight: '#D1FAE5',
  primaryDark: '#065F46',
  danger: '#EF4444',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Nav = StackNavigationProp<RootStackParamList>;

export default function MemberListScreen() {
  const navigation = useNavigation<Nav>();
  const { logout } = useAuth();

  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const fetchMembers = useCallback(async () => {
    setError('');
    try {
      const res = await membersAPI.list();
      setMembers(res.data.items ?? res.data);
    } catch {
      setError('Could not load family members. Check your connection.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // Set logout button in header
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity onPress={logout} style={{ marginRight: 16 }}>
          <Text style={{ color: COLORS.white, fontWeight: '600', fontSize: 14 }}>
            Sign Out
          </Text>
        </TouchableOpacity>
      ),
    });
    fetchMembers();
  }, [navigation, logout, fetchMembers]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>Loading family members…</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorEmoji}>⚠️</Text>
        <Text style={styles.errorTitle}>Something went wrong</Text>
        <Text style={styles.errorSub}>{error}</Text>
        <TouchableOpacity
          style={styles.retryBtn}
          onPress={() => { setLoading(true); fetchMembers(); }}
        >
          <Text style={styles.retryBtnText}>Try Again</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.list}
      data={members}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <MemberCard
          member={item}
          onPress={() =>
            navigation.navigate('ProgramOverview', {
              memberId: item.id,
              memberName: item.full_name,
              programId: item.active_program?.id,
            })
          }
          onMealPress={() =>
            navigation.navigate('MealCapture', {
              memberId: item.id,
              programId: item.active_program?.id,
            })
          }
        />
      )}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => { setRefreshing(true); fetchMembers(); }}
          tintColor={COLORS.primary}
        />
      }
      ListHeaderComponent={
        <Text style={styles.listHeader}>
          {members.length} member{members.length !== 1 ? 's' : ''}
        </Text>
      }
      ListEmptyComponent={
        <View style={styles.empty}>
          <Text style={styles.emptyEmoji}>👨‍👩‍👧‍👦</Text>
          <Text style={styles.emptyTitle}>No family members yet</Text>
          <Text style={styles.emptySub}>
            Add family members to start tracking their health journey.
          </Text>
        </View>
      }
      contentContainerStyle={members.length === 0 ? styles.emptyContainer : styles.content}
    />
  );
}

const styles = StyleSheet.create({
  list: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingVertical: 8, paddingBottom: 24 },
  emptyContainer: { flex: 1 },
  listHeader: {
    fontSize: 13,
    color: COLORS.textSecondary,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.background,
    padding: 32,
  },
  loadingText: { marginTop: 12, fontSize: 14, color: COLORS.textSecondary },
  errorEmoji: { fontSize: 40, marginBottom: 12 },
  errorTitle: { fontSize: 18, fontWeight: '700', color: COLORS.text, marginBottom: 6 },
  errorSub: { fontSize: 14, color: COLORS.textSecondary, textAlign: 'center', marginBottom: 20 },
  retryBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingHorizontal: 32,
    paddingVertical: 12,
  },
  retryBtnText: { color: COLORS.white, fontWeight: '700', fontSize: 15 },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  emptyEmoji: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: COLORS.text, marginBottom: 8 },
  emptySub: { fontSize: 14, color: COLORS.textSecondary, textAlign: 'center', lineHeight: 20 },
});
