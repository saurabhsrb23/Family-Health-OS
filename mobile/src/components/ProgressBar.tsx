import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface Props {
  value: number;       // 0–100
  label?: string;
  color?: string;
  showLabel?: boolean; // alias for showPercent
  showPercent?: boolean;
  height?: number;
}

export const ProgressBar: React.FC<Props> = ({
  value,
  label,
  color = '#10B981',
  showLabel,
  showPercent,
  height = 8,
}) => {
  const clamped = Math.min(100, Math.max(0, value));
  // Support both prop names
  const displayHeader = (showLabel ?? showPercent ?? true);

  return (
    <View style={styles.container}>
      {(label || displayHeader) && (
        <View style={styles.row}>
          {label ? <Text style={styles.label}>{label}</Text> : <View />}
          {displayHeader && (
            <Text style={[styles.percent, { color }]}>{Math.round(clamped)}%</Text>
          )}
        </View>
      )}
      <View style={[styles.track, { height }]}>
        <View
          style={[styles.fill, { width: `${clamped}%`, backgroundColor: color, height }]}
        />
      </View>
    </View>
  );
};

export default ProgressBar;

const styles = StyleSheet.create({
  container: { marginVertical: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  label: { fontSize: 13, color: '#374151', fontWeight: '500' },
  percent: { fontSize: 13, fontWeight: '700' },
  track: { backgroundColor: '#E5E7EB', borderRadius: 4, overflow: 'hidden' },
  fill: { borderRadius: 4 },
});
