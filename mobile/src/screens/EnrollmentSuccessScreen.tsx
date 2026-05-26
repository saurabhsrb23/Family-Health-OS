import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../navigation/AppNavigator';

const COLORS = {
  primary: '#10B981',
  primaryLight: '#D1FAE5',
  primaryDark: '#065F46',
  text: '#111827',
  textSecondary: '#6B7280',
  background: '#F9FAFB',
  white: '#FFFFFF',
  border: '#E5E7EB',
};

type Nav = StackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'EnrollmentSuccess'>;

export default function EnrollmentSuccessScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { memberName, programTitle } = route.params;

  function handleViewProgram() {
    navigation.reset({
      index: 0,
      routes: [{ name: 'MemberList' }],
    });
  }

  function handleAddAnother() {
    navigation.navigate('AddMember');
  }

  return (
    <View style={styles.container}>
      {/* Checkmark */}
      <View style={styles.checkCircle}>
        <Text style={styles.checkEmoji}>✓</Text>
      </View>

      <Text style={styles.title}>Program Launched! 🎉</Text>
      <Text style={styles.subtitle}>{memberName} is now enrolled</Text>

      {/* Info Card */}
      <View style={styles.infoCard}>
        <Text style={styles.infoRow}>📋 {programTitle}</Text>
        <Text style={styles.infoRow}>📅 90-day program starts today</Text>
        <Text style={styles.infoRow}>🥗 Nutrition · 💪 Strength · 🏥 Clinical</Text>
      </View>

      {/* Buttons */}
      <TouchableOpacity style={styles.primaryBtn} onPress={handleViewProgram}>
        <Text style={styles.primaryBtnText}>View Program</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.outlinedBtn} onPress={handleAddAnother}>
        <Text style={styles.outlinedBtnText}>Add Another Member</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },

  checkCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  checkEmoji: { fontSize: 40, color: COLORS.white, fontWeight: '700' },

  title: {
    fontSize: 24,
    fontWeight: '800',
    color: COLORS.text,
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginBottom: 24,
    textAlign: 'center',
  },

  infoCard: {
    backgroundColor: COLORS.primaryLight,
    borderRadius: 12,
    padding: 16,
    width: '100%',
    marginBottom: 32,
  },
  infoRow: {
    fontSize: 14,
    color: COLORS.primaryDark,
    marginBottom: 6,
    lineHeight: 20,
  },

  primaryBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    width: '100%',
    marginBottom: 12,
  },
  primaryBtnText: { color: COLORS.white, fontSize: 16, fontWeight: '600' },

  outlinedBtn: {
    backgroundColor: COLORS.white,
    borderWidth: 1.5,
    borderColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    width: '100%',
  },
  outlinedBtnText: { color: COLORS.primary, fontSize: 16, fontWeight: '600' },
});
