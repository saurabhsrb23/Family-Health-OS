import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';

interface Props {
  visible?: boolean;
  message?: string;
}

// Named export (overlay mode — used inline with visible prop)
export const LoadingOverlay: React.FC<Props> = ({ visible = true, message }) => {
  if (!visible) return null;
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#10B981" />
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F9FAFB',
  },
  message: {
    marginTop: 12,
    fontSize: 14,
    color: '#6B7280',
  },
});

// Default export (full-screen replacement — used as a screen)
export default LoadingOverlay;
