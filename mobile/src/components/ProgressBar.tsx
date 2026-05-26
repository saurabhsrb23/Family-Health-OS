import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface Props {
  value: number; // 0–100
  label?: string;
  color?: string;
  showPercent?: boolean;
}

export default function ProgressBar({
  value,
  label,
  color = '#10B981',
  showPercent = true,
}: Props) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <View style={styles.container}>
      {(label || showPercent) && (
        <View style={styles.row}>
          {label ? <Text style={styles.label}>{label}</Text> : <View />}
          {showPercent && (
            <Text style={[styles.percent, { color }]}>{Math.round(clamped)}%</Text>
          )}
        </View>
      )}
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${clamped}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginVertical: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  label: { fontSize: 13, color: '#374151', fontWeight: '500' },
  percent: { fontSize: 13, fontWeight: '700' },
  track: {
    height: 8,
    backgroundColor: '#E5E7EB',
    borderRadius: 4,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: 4 },
});
