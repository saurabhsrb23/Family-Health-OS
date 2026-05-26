import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  Alert,
  ScrollView,
  ActivityIndicator,
  Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { mealsAPI } from '../services/api';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Route = RouteProp<RootStackParamList, 'MealCapture'>;
type Nav = StackNavigationProp<RootStackParamList>;

type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export default function MealCaptureScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { memberId } = route.params;

  const [imageUri, setImageUri] = useState<string | null>(null);
  const [mealType, setMealType] = useState<MealType>('lunch');
  const [uploading, setUploading] = useState(false);

  const pickImage = async (fromCamera: boolean) => {
    const perm = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (perm.status !== 'granted') {
      Alert.alert('Permission Required', 'Please grant the required permission in Settings.');
      return;
    }

    const result = fromCamera
      ? await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 });

    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri);
    }
  };

  const handleUpload = async () => {
    if (!imageUri) {
      Alert.alert('No Image', 'Please select or capture a meal photo first.');
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      const filename = imageUri.split('/').pop() ?? 'meal.jpg';
      const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg';
      const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg';
      formData.append('file', { uri: imageUri, name: filename, type: mimeType } as any);
      formData.append('meal_type', mealType);

      const res = await mealsAPI.upload(memberId, formData);
      const mealId: string = res.data.id;
      navigation.replace('NutritionResult', { mealId, memberId });
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Upload failed. Please try again.';
      Alert.alert('Upload Error', msg);
    } finally {
      setUploading(false);
    }
  };

  const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner', 'snack'];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Meal type selector */}
      <Text style={styles.sectionLabel}>Meal Type</Text>
      <View style={styles.mealTypeRow}>
        {MEAL_TYPES.map((mt) => (
          <TouchableOpacity
            key={mt}
            style={[styles.mealTypeBtn, mealType === mt && styles.mealTypeBtnActive]}
            onPress={() => setMealType(mt)}
          >
            <Text style={[styles.mealTypeBtnText, mealType === mt && styles.mealTypeBtnTextActive]}>
              {mt}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Image preview */}
      <View style={styles.imageBox}>
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.image} resizeMode="cover" />
        ) : (
          <View style={styles.imagePlaceholder}>
            <Text style={styles.placeholderEmoji}>🍽️</Text>
            <Text style={styles.placeholderText}>No photo selected</Text>
          </View>
        )}
      </View>

      {/* Capture / Pick buttons */}
      <View style={styles.btnRow}>
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={() => pickImage(true)}>
          <Text style={styles.btnOutlineText}>📷 Camera</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={() => pickImage(false)}>
          <Text style={styles.btnOutlineText}>🖼️ Gallery</Text>
        </TouchableOpacity>
      </View>

      {/* Upload */}
      <TouchableOpacity
        style={[styles.btn, styles.btnPrimary, (!imageUri || uploading) && styles.btnDisabled]}
        onPress={handleUpload}
        disabled={!imageUri || uploading}
      >
        {uploading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.btnPrimaryText}>Analyze Nutrition</Text>
        )}
      </TouchableOpacity>

      <Text style={styles.hint}>
        AI will extract nutritional data from your meal photo using Gemini Vision.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  content: { padding: 16, paddingBottom: 40 },
  sectionLabel: { fontSize: 14, fontWeight: '700', color: '#374151', marginBottom: 10 },
  mealTypeRow: { flexDirection: 'row', gap: 8, marginBottom: 20, flexWrap: 'wrap' },
  mealTypeBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: '#D1D5DB',
    backgroundColor: '#FFFFFF',
  },
  mealTypeBtnActive: { borderColor: '#10B981', backgroundColor: '#ECFDF5' },
  mealTypeBtnText: { fontSize: 13, color: '#6B7280', textTransform: 'capitalize', fontWeight: '600' },
  mealTypeBtnTextActive: { color: '#10B981' },
  imageBox: {
    height: 240,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#E5E7EB',
    marginBottom: 16,
  },
  image: { width: '100%', height: '100%' },
  imagePlaceholder: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  placeholderEmoji: { fontSize: 48, marginBottom: 8 },
  placeholderText: { fontSize: 14, color: '#9CA3AF' },
  btnRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  btn: { flex: 1, borderRadius: 10, paddingVertical: 13, alignItems: 'center' },
  btnOutline: { borderWidth: 1.5, borderColor: '#10B981', backgroundColor: '#FFFFFF' },
  btnOutlineText: { fontSize: 14, color: '#10B981', fontWeight: '700' },
  btnPrimary: { backgroundColor: '#10B981', flex: 0, width: '100%', marginBottom: 16 },
  btnPrimaryText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  btnDisabled: { backgroundColor: '#6EE7B7' },
  hint: { fontSize: 12, color: '#9CA3AF', textAlign: 'center', lineHeight: 18 },
});
