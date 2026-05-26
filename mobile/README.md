# Praan Health — Mobile App

React Native + Expo mobile client for the Family Health OS. Connects to the FastAPI backend to provide a complete 90-day family health tracking experience.

---

## Screens

| Screen | File | Description |
|---|---|---|
| **Login** | `LoginScreen.tsx` | Email/password login, demo quick-fill button, JWT token persistence via AsyncStorage |
| **Member List** | `MemberListScreen.tsx` | All family members with active program progress bars, pull-to-refresh, logout |
| **Program Overview** | `ProgramOverviewScreen.tsx` | 90-day progress (day/phase/days remaining), per-component adherence cards, FAB to log a meal |
| **Meal Capture** | `MealCaptureScreen.tsx` | Meal type selector, camera + gallery photo picker, upload to AI, real-time polling |
| **Nutrition Result** | `NutritionResultScreen.tsx` | AI-extracted macros (calories/protein/carbs/fat), today's protein progress vs target |
| **Adherence Dashboard** | `AdherenceDashboard.tsx` | Overall score, nutrition/strength/clinical cards, 7-day trend, simple bar chart |

---

## Setup

### Prerequisites
- Node.js 18+
- Expo CLI: `npm install -g expo-cli`
- **Backend must be running** (see root README): `docker-compose up --build`

### Install & Run

```bash
cd mobile
npm install
npx expo start
```

Then:
- Press `a` — Android emulator (requires Android Studio)
- Press `i` — iOS simulator (requires Xcode, macOS only)
- Scan QR code with **Expo Go** app (iOS or Android physical device)

---

## API Configuration

Update `src/services/api.ts`:

```typescript
// iOS simulator
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Android emulator (default)
const API_BASE_URL = 'http://10.0.2.2:8000/api/v1';

// Physical device — replace with your machine's LAN IP
const API_BASE_URL = 'http://192.168.1.x:8000/api/v1';
```

---

## Demo Flow

1. **Login**: `demo@familyhealthos.com` / `Demo@1234` (or tap "Quick Demo Login")
2. **Member List**: See Rahul (Day 30) and Priya (Day 15) with program progress
3. **Program Overview**: Tap Rahul → see Phase 2, adherence per component
4. **Log Meal**: Tap the green **+** FAB → select Breakfast → choose/take photo
5. **AI Analysis**: Tap "Analyze Meal" → wait 2-3s → see extracted macros
6. **Dashboard**: Tap "View Dashboard" → overall score + 7-day trend

---

## Key Features

| Feature | Implementation |
|---|---|
| JWT auth with auto-refresh | Axios interceptor catches 401, silently refreshes token, retries original request |
| Token persistence | `AsyncStorage.multiSet(['access_token', 'refresh_token', 'user'])` on login |
| Camera integration | `expo-image-picker` with permission request flow, `allowsEditing: true`, aspect `[4,3]` |
| AI extraction polling | `setInterval` every 2s, stops on `completed`/`failed`, max 30 polls before timeout |
| Pull-to-refresh | `RefreshControl` on all list screens |
| Error states | Friendly messages with retry buttons on every screen (no blank screens or crashes) |
| FAB navigation | Floating action button on Program Overview → directly to Meal Capture |

---

## Project Structure

```
mobile/
├── App.tsx                          # Root: GestureHandlerRootView + AuthProvider + AppNavigator
├── app.json                         # Expo config, bundle IDs, camera permissions
├── package.json
└── src/
    ├── services/
    │   └── api.ts                   # Axios instance, request/response interceptors, typed API methods
    ├── context/
    │   └── AuthContext.tsx          # Auth state, login/logout, AsyncStorage persistence
    ├── navigation/
    │   └── AppNavigator.tsx         # Stack navigator, auth-gated routing (Login vs app screens)
    ├── components/
    │   ├── LoadingOverlay.tsx       # Full-screen spinner with optional message
    │   ├── ProgressBar.tsx          # Reusable progress bar (label, percent, color, height props)
    │   └── MemberCard.tsx           # Family member card with program progress + Log Meal button
    └── screens/
        ├── LoginScreen.tsx
        ├── MemberListScreen.tsx
        ├── ProgramOverviewScreen.tsx
        ├── MealCaptureScreen.tsx
        ├── NutritionResultScreen.tsx
        └── AdherenceDashboard.tsx
```

---

## Production Considerations

| Feature | Library / Approach |
|---|---|
| Push notifications | `expo-notifications` for meal reminders + adherence alerts |
| Background fetch | `expo-background-fetch` to sync adherence data while app is backgrounded |
| Biometric auth | `expo-local-authentication` — Face ID / fingerprint unlock |
| Offline storage | `WatermelonDB` — SQLite-backed ORM, sync on reconnect |
| Crash reporting | `@sentry/react-native` — error boundaries + native crash reports |
| Performance monitoring | `react-native-performance` + Sentry tracing |
| Deep linking | Expo Router or React Navigation deep link config (e.g. `praan://member/123`) |
| App Store deployment | EAS Build (`eas build --platform ios`) + EAS Submit |

---

## Troubleshooting

**"Network Error" on login**
→ Check `API_BASE_URL` in `src/services/api.ts`. Use `10.0.2.2` for Android emulator, `localhost` for iOS simulator.

**"Metro bundler failed to start"**
→ `npx expo start --clear` to clear Metro cache.

**Camera permission denied**
→ On iOS simulator: Device → Privacy & Security → Camera → toggle Expo Go.

**"Unable to resolve module"**
→ `rm -rf node_modules && npm install && npx expo start --clear`
