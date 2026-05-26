import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// For Android emulator use 10.0.2.2, for physical device use your machine's LAN IP
const API_BASE_URL = 'http://192.168.0.6:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach Bearer token ──────────────────────────────────
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: auto-refresh on 401 ────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token } = response.data;
        await AsyncStorage.setItem('access_token', access_token);
        original.headers.Authorization = `Bearer ${access_token}`;
        return api(original);
      } catch (refreshError) {
        await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user']);
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

// ── Typed API methods ─────────────────────────────────────────────────────────
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

export const membersAPI = {
  list: () => api.get('/members'),
  get: (id: string) => api.get(`/members/${id}`),
  create: (data: any) => api.post('/members', data),
};

export const programsAPI = {
  list: (memberId: string) => api.get(`/members/${memberId}/programs`),
  get: (memberId: string, programId: string) =>
    api.get(`/members/${memberId}/programs/${programId}`),
  create: (memberId: string, data: any) =>
    api.post(`/members/${memberId}/programs`, data),
};

export const mealsAPI = {
  upload: (memberId: string, formData: FormData) =>
    api.post(`/members/${memberId}/meals`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }),
  list: (memberId: string, params?: any) =>
    api.get(`/members/${memberId}/meals`, { params }),
  get: (memberId: string, mealId: string) =>
    api.get(`/members/${memberId}/meals/${mealId}`),
  getStatus: (memberId: string, mealId: string) =>
    api.get(`/members/${memberId}/meals/${mealId}/status`),
};

export const adherenceAPI = {
  getReport: (memberId: string, reportDate?: string) =>
    api.get(`/members/${memberId}/adherence`, {
      params: reportDate ? { report_date: reportDate } : undefined,
    }),
  getDailyNutrition: (memberId: string) =>
    api.get(`/members/${memberId}/adherence/nutrition/daily`),
};

export const workoutsAPI = {
  log: (memberId: string, data: any) =>
    api.post(`/members/${memberId}/workouts`, data),
  list: (memberId: string, params?: any) =>
    api.get(`/members/${memberId}/workouts`, { params }),
};

export const measurementsAPI = {
  log: (memberId: string, data: any) =>
    api.post(`/members/${memberId}/measurements`, data),
  list: (memberId: string, params?: any) =>
    api.get(`/members/${memberId}/measurements`, { params }),
  latest: (memberId: string) =>
    api.get(`/members/${memberId}/measurements/latest`),
};

export default api;
