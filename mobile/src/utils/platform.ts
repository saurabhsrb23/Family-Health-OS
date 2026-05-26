import { Platform } from 'react-native';

/**
 * Cross-platform card shadow.
 * - Native: uses shadow* props (iOS) + elevation (Android)
 * - Web: uses boxShadow to avoid deprecation warnings
 */
export function cardShadow(depth: 'sm' | 'md' = 'md') {
  if (Platform.OS === 'web') {
    return depth === 'sm'
      ? { boxShadow: '0px 1px 4px rgba(0,0,0,0.08)' }
      : { boxShadow: '0px 2px 8px rgba(0,0,0,0.10)' };
  }
  return depth === 'sm'
    ? { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 }
    : { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 };
}

/**
 * On web, ScrollView with flex:1 has no bounded height so it doesn't scroll.
 * height: 0 + flex: 1 forces the parent (navigator) to control the height.
 */
export const scrollViewStyle = Platform.OS === 'web'
  ? { flex: 1, height: 0 } as const
  : { flex: 1 } as const;
