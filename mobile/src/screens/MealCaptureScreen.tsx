import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { mealsAPI } from '../services/api';
import { scrollViewStyle } from '../utils/platform';
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

type Route = RouteProp<RootStackParamList, 'MealCapture'>;
type Nav = StackNavigationProp<RootStackParamList>;
type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

const MEAL_TYPES: { key: MealType; label: string; emoji: string }[] = [
  { key: 'breakfast', label: 'Breakfast', emoji: '🌅' },
  { key: 'lunch', label: 'Lunch', emoji: '☀️' },
  { key: 'dinner', label: 'Dinner', emoji: '🌙' },
  { key: 'snack', label: 'Snack', emoji: '🍎' },
];

export default function MealCaptureScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId, memberName, programId } = route.params;

  const [mealType, setMealType] = useState<MealType>('lunch');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageMime, setImageMime] = useState<string>('image/jpeg');
  const [uploadStatus, setUploadStatus] = useState<
    'idle' | 'uploading' | 'analyzing' | 'error'
  >('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pickImage = async (fromCamera: boolean) => {
    const perm = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (perm.status !== 'granted') {
      Alert.alert(
        'Permission Required',
        `Please allow ${fromCamera ? 'camera' : 'photo library'} access in Settings.`
      );
      return;
    }

    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    };

    const result = fromCamera
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setImageUri(asset.uri);
      setImageMime(asset.mimeType ?? 'image/jpeg');
      setErrorMsg('');
    }
  };

  const startPoll = (mealId: string) => {
    let count = 0;
    pollRef.current = setInterval(async () => {
      count++;
      try {
        const res = await mealsAPI.getStatus(memberId, mealId);
        const status: string = res.data.extraction_status;
        if (status === 'completed') {
          clearInterval(pollRef.current!);
          navigation.replace('NutritionResult', { memberId, memberName, mealId });
        } else if (status === 'failed') {
          clearInterval(pollRef.current!);
          setUploadStatus('error');
          setErrorMsg('AI analysis failed. Please try a clearer photo.');
        }
      } catch {
        // ignore poll errors
      }
      if (count >= 30) {
        clearInterval(pollRef.current!);
        setUploadStatus('error');
        setErrorMsg('Analysis timed out. Please try again.');
      }
    }, 2000);
  };

  const handleAnalyze = async () => {
    if (!imageUri) return;
    setUploadStatus('uploading');
    setErrorMsg('');
    try {
      const filename = imageUri.split('/').pop() ?? 'meal.jpg';
      const formData = new FormData();
      if (Platform.OS === 'web') {
        // Web/browser: fetch the URI and convert to Blob
        const blobRes = await fetch(imageUri);
        const blob = await blobRes.blob();
        formData.append('photo', blob, filename);
      } else {
        // Native iOS/Android: React Native FormData accepts { uri, name, type }
        formData.append('photo', { uri: imageUri, name: filename, type: imageMime } as any);
      }
      formData.append('meal_type', mealType);
      formData.append('logged_at', new Date().toISOString());
      if (programId) formData.append('program_id', programId);

      setUploadStatus('analyzing');
      const res = await mealsAPI.upload(memberId, formData);
      const mealId: string = res.data.id;
      startPoll(mealId);
    } catch (err: any) {
      setUploadStatus('error');
      setErrorMsg(
        err?.response?.data?.detail ?? 'Upload failed. Please try again.'
      );
    }
  };

  const isProcessing = uploadStatus === 'uploading' || uploadStatus === 'analyzing';

  return (
    <ScrollView style={[styles.container, scrollViewStyle]} contentContainerStyle={styles.content}>
      {/* Meal type selector */}
      <Text style={styles.sectionLabel}>Meal Type</Text>
      <View style={styles.mealTypeRow}>
        {MEAL_TYPES.map(({ key, label, emoji }) => {
          const active = mealType === key;
          return (
            <TouchableOpacity
              key={key}
              style={[styles.mealTypeBtn, active && styles.mealTypeBtnActive]}
              onPress={() => setMealType(key)}
              disabled={isProcessing}
            >
              <Text style={styles.mealTypeEmoji}>{emoji}</Text>
              <Text style={[styles.mealTypeLabel, active && styles.mealTypeLabelActive]}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Image preview / placeholder */}
      <View style={styles.imageBox}>
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.image} resizeMode="cover" />
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderEmoji}>🍽️</Text>
            <Text style={styles.placeholderText}>No photo selected</Text>
          </View>
        )}
      </View>

      {/* Capture buttons */}
      {!isProcessing && (
        <View style={styles.captureRow}>
          <TouchableOpacity
            style={[styles.captureBtn, styles.captureBtnOutline]}
            onPress={() => pickImage(true)}
          >
            <Text style={styles.captureBtnOutlineText}>📷 Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.captureBtn, styles.captureBtnOutline]}
            onPress={() => pickImage(false)}
          >
            <Text style={styles.captureBtnOutlineText}>🖼 Gallery</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Analyze button */}
      {imageUri && (
        <TouchableOpacity
          style={[styles.analyzeBtn, isProcessing && styles.analyzeBtnDisabled]}
          onPress={handleAnalyze}
          disabled={isProcessing}
          activeOpacity={0.85}
        >
          {isProcessing ? (
            <View style={styles.analyzingRow}>
              <ActivityIndicator color={COLORS.white} style={{ marginRight: 10 }} />
              <Text style={styles.analyzeBtnText}>
                {uploadStatus === 'uploading' ? 'Uploading…' : 'Analyzing with AI…'}
              </Text>
            </View>
          ) : (
            <Text style={styles.analyzeBtnText}>✨ Analyze Meal</Text>
          )}
        </TouchableOpacity>
      )}

      {/* Error */}
      {uploadStatus === 'error' && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{errorMsg}</Text>
          <TouchableOpacity
            onPress={() => { setUploadStatus('idle'); setImageUri(null); }}
          >
            <Text style={styles.retryText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      )}

      <Text style={styles.hint}>
        AI will identify foods and extract nutritional data from your photo.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 10,
  },
  mealTypeRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  mealTypeBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    backgroundColor: COLORS.white,
  },
  mealTypeBtnActive: {
    borderColor: COLORS.primary,
    backgroundColor: COLORS.primaryLight,
  },
  mealTypeEmoji: { fontSize: 18, marginBottom: 2 },
  mealTypeLabel: { fontSize: 11, color: COLORS.textSecondary, fontWeight: '600' },
  mealTypeLabelActive: { color: COLORS.primaryDark },
  imageBox: {
    height: 220,
    borderRadius: 14,
    overflow: 'hidden',
    backgroundColor: COLORS.border,
    marginBottom: 16,
  },
  image: { width: '100%', height: '100%' },
  placeholder: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  placeholderEmoji: { fontSize: 48, marginBottom: 8 },
  placeholderText: { fontSize: 14, color: COLORS.textSecondary },
  captureRow: { flexDirection: 'row', gap: 12, marginBottom: 14 },
  captureBtn: { flex: 1, borderRadius: 10, paddingVertical: 13, alignItems: 'center' },
  captureBtnOutline: {
    borderWidth: 1.5,
    borderColor: COLORS.primary,
    backgroundColor: COLORS.white,
  },
  captureBtnOutlineText: { fontSize: 14, fontWeight: '700', color: COLORS.primary },
  analyzeBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
    marginBottom: 16,
  },
  analyzeBtnDisabled: { backgroundColor: '#6EE7B7' },
  analyzeBtnText: { fontSize: 16, fontWeight: '700', color: COLORS.white },
  analyzingRow: { flexDirection: 'row', alignItems: 'center' },
  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginBottom: 14,
  },
  errorText: { fontSize: 14, color: COLORS.danger, textAlign: 'center', marginBottom: 8 },
  retryText: { fontSize: 14, fontWeight: '700', color: COLORS.primary },
  hint: {
    fontSize: 12,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
  },
});
