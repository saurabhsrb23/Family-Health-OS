# Family Health OS — Mobile App

React Native + Expo mobile client for the 90-day Family Health OS platform.
Connects to the FastAPI backend for JWT auth, meal photo upload, AI nutrition extraction, and adherence tracking.

---

## Table of Contents

1. [Screens](#1-screens)
2. [Run on Physical Phone (Expo Go)](#2-run-on-physical-phone-expo-go)
3. [Run on Web Browser](#3-run-on-web-browser)
4. [Run on Android Emulator](#4-run-on-android-emulator)
5. [Run on iOS Simulator](#5-run-on-ios-simulator)
6. [API URL Configuration](#6-api-url-configuration)
7. [Demo Flow](#7-demo-flow)
8. [Key Features](#8-key-features)
9. [Project Structure](#9-project-structure)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Screens

### Core Screens

| Screen | File | Description |
|---|---|---|
| **Login** | `LoginScreen.tsx` | Email/password login · JWT token saved to AsyncStorage |
| **Member List** | `MemberListScreen.tsx` | All family members · program progress bars · pull-to-refresh · "+" to enroll |
| **Program Overview** | `ProgramOverviewScreen.tsx` | Day counter · phase · component adherence cards · FAB to log meal |
| **Meal Capture** | `MealCaptureScreen.tsx` | Meal type selector · camera or gallery · upload · AI polling |
| **Nutrition Result** | `NutritionResultScreen.tsx` | AI-extracted calories/protein/carbs/fat · daily progress bar |
| **Adherence Dashboard** | `AdherenceDashboard.tsx` | Overall score · nutrition/strength/clinical cards · 7-day bar chart |

### Enrollment Flow (UI/UX Requirement 3.2)

| Screen | File | Description |
|---|---|---|
| **Add Member** | `AddMemberScreen.tsx` | Live-initial avatar · name/DOB/phone · relationship & gender selectors · POST /members |
| **Create Program** | `CreateProgramScreen.tsx` | Pre-filled 90-day title · start date · live end-date preview · no API call yet |
| **Configure Components** | `ConfigureComponentsScreen.tsx` | Nutrition / Strength / Clinical config cards · all defaults pre-filled · POST /members/{id}/programs |
| **Enrollment Success** | `EnrollmentSuccessScreen.tsx` | Success confirmation · navigation.reset() back to MemberList · no back navigation |

---

## 2. Run on Physical Phone (Expo Go)

### Step 1 — Install Expo Go

| Platform | Link |
|---|---|
| iPhone | App Store → search "Expo Go" → install version **54.x** |
| Android | Play Store → search "Expo Go" → install version **54.x** |

### Step 2 — Start the backend

```bash
# From the project root (Family-Health-OS/)
docker-compose up --build
```

Wait until you see: `Application startup complete.`

### Step 3 — Find your machine's LAN IP

```bash
# Mac / Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows (Command Prompt)
ipconfig | findstr "IPv4"
```

Example result: `192.168.0.6`

### Step 4 — Update the API URL

Open [src/services/api.ts](src/services/api.ts) and set line 5:

```typescript
const API_BASE_URL = 'http://192.168.0.6:8000/api/v1';
//                          ^^^^^^^^^^^^ your LAN IP
```

> Your phone and laptop must be on the **same Wi-Fi network**.

### Step 5 — Start Metro and scan the QR code

```bash
cd mobile
npm install          # first time only
npx expo start --clear
```

- **iPhone:** Open Camera app → point at QR code in terminal → tap the yellow banner
- **Android:** Open Expo Go → tap "Scan QR code" → point at QR code

---

## 3. Run on Web Browser

No phone needed — runs at `http://localhost:8081`.

```bash
# 1. Start backend
docker-compose up --build   # from project root

# 2. Start Expo web
cd mobile
npm install
npx expo start --web
```

Browser opens automatically at **http://localhost:8081**.

**API URL for web** — set in [src/services/api.ts](src/services/api.ts):

```typescript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

> Web uses the browser's file picker instead of the native camera.
> Photo upload works via `fetch → Blob` (handled automatically).

---

## 4. Run on Android Emulator

### Prerequisites
- [Android Studio](https://developer.android.com/studio) installed
- A virtual device created (API 33+ recommended)

### Steps

```bash
# 1. Start Android Studio → Device Manager → Start emulator

# 2. Update API URL in src/services/api.ts
const API_BASE_URL = 'http://10.0.2.2:8000/api/v1';
# 10.0.2.2 is the Android emulator's alias for your machine's localhost

# 3. Start the app
cd mobile
npx expo start --android
```

---

## 5. Run on iOS Simulator

### Prerequisites
- macOS only
- Xcode installed from the App Store

### Steps

```bash
# 1. Update API URL in src/services/api.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';

# 2. Start the app
cd mobile
npx expo start --ios
```

---

## 6. API URL Configuration

Edit **one line** in [src/services/api.ts](src/services/api.ts):

| Scenario | API_BASE_URL value |
|---|---|
| Physical iPhone / Android (Expo Go) | `http://<YOUR_LAN_IP>:8000/api/v1` |
| Web browser (localhost) | `http://localhost:8000/api/v1` |
| Android emulator | `http://10.0.2.2:8000/api/v1` |
| iOS simulator | `http://localhost:8000/api/v1` |

Find your LAN IP:
- **Mac:** System Settings → Wi-Fi → Details → IP Address
- **Windows:** Settings → Wi-Fi → network name → Properties → IPv4 address

---

## 7. Demo Flow

**Login credentials:** `demo@familyhealthos.com` / `Demo@1234`

### Daily Tracking Flow

| Step | Screen | What to do |
|---|---|---|
| 1 | Login | Enter credentials or tap "Quick Demo Login" |
| 2 | Member List | See Rahul (Day 31) and Priya (Day 15) with progress bars |
| 3 | Program Overview | Tap Rahul's card → see Phase 2, adherence per component |
| 4 | Meal Capture | Tap the green **+** FAB → select Lunch → take/pick a photo |
| 5 | AI Analysis | Tap "✨ Analyze Meal" → 2s mock AI → see extracted macros |
| 6 | Nutrition Result | See calories, protein, carbs, fat + daily progress bar |
| 7 | Dashboard | Tap "📊 View Dashboard" → overall score + 7-day trend chart |

### Enrollment Flow (Add New Member)

| Step | Screen | What to do |
|---|---|---|
| 1 | Member List | Tap the **+** icon in the top-right header |
| 2 | Add Member | Type a name (avatar shows initials live) · select Relationship · tap "Continue →" |
| 3 | Create Program | Title pre-filled · start date defaults to today · end date updates live · tap "Configure Components →" |
| 4 | Configure Components | Adjust nutrition / strength / clinical targets (all pre-filled with defaults) · tap "🚀 Launch Program" |
| 5 | Enrollment Success | Confirmation screen · tap "View Program" to return to Member List |

---

## 8. Key Features

| Feature | How it works |
|---|---|
| **JWT auth with auto-refresh** | Axios interceptor catches 401 → silently calls `/auth/refresh` → retries original request |
| **Token persistence** | `AsyncStorage` stores access_token + refresh_token — survives app restart |
| **Camera + gallery** | `expo-image-picker` with permission request flow · aspect ratio 4:3 · 80% quality |
| **Multi-format photo support** | JPEG, PNG, HEIC (iPhone default), WebP, GIF all accepted |
| **AI extraction polling** | `setInterval` every 2s · stops on `completed`/`failed` · max 30 polls (60s timeout) |
| **Pull-to-refresh** | `RefreshControl` on all list screens |
| **Error states** | Retry buttons on every screen — no blank screens, no crashes |
| **FAB navigation** | Floating + button on Program Overview → direct to Meal Capture |
| **Web + native support** | Photo upload uses `fetch → Blob` on web, `{ uri, name, type }` on native |
| **Audit-safe navigation** | `memberName` flows through the full navigation stack — no missing params |
| **Enrollment flow** | 4-screen wizard: Add Member → Create Program → Configure Components → Success |
| **Live avatar initials** | Avatar circle on Add Member updates with initials as user types the name |
| **Live end-date preview** | Create Program computes end date (start + 89 days) live as user edits start date |
| **Pre-filled defaults** | All enrollment fields have sensible defaults — user can tap through in seconds |
| **Stack reset on success** | EnrollmentSuccess uses `navigation.reset()` — back button cannot return to config screens |

---

## 9. Project Structure

```
mobile/
├── App.tsx                        # Root: GestureHandlerRootView + AuthProvider + Navigator
├── app.json                       # Expo config (name, icons, camera permissions)
├── package.json                   # Expo SDK 54, React Native 0.76.3
├── tsconfig.json
└── src/
    ├── services/
    │   └── api.ts                 # Axios instance · request/response interceptors · API methods
    │                              #   authAPI, membersAPI, programsAPI, mealsAPI, adherenceAPI
    │                              #   membersAPI.create · programsAPI.create
    ├── context/
    │   └── AuthContext.tsx        # Auth state · login/logout · AsyncStorage persistence
    ├── navigation/
    │   └── AppNavigator.tsx       # Stack navigator · auth-gated routing · typed param list
    │                              #   RootStackParamList includes all 10 routes
    ├── components/
    │   ├── MemberCard.tsx         # Member card: avatar, relationship badge, progress, Log Meal btn
    │   ├── ProgressBar.tsx        # Reusable bar: value, color, label, height props
    │   └── LoadingOverlay.tsx     # Full-screen spinner with optional message
    └── screens/
        ├── LoginScreen.tsx        # Email/password form + quick-fill demo button
        ├── MemberListScreen.tsx   # FlatList of MemberCards + "+" header button + Sign Out
        ├── ProgramOverviewScreen.tsx  # Program header + component adherence cards + FAB
        ├── MealCaptureScreen.tsx  # Meal type picker + image picker + upload + polling
        ├── NutritionResultScreen.tsx  # Macro display + protein progress bar
        ├── AdherenceDashboard.tsx # Score card + nutrition/strength/clinical cards + bar chart
        ├── WorkoutLogScreen.tsx   # Session type · energy · exercises (add/remove) · POST /workouts
        ├── ClinicalLogScreen.tsx  # Measurement type tabs · BP/weight/glucose fields · POST /measurements
        │
        │   ── Enrollment Flow ──────────────────────────────────────────────────
        ├── AddMemberScreen.tsx          # Live avatar · member details · relationship/gender
        ├── CreateProgramScreen.tsx      # Program title · start date · live 90-day end date
        ├── ConfigureComponentsScreen.tsx  # Nutrition/Strength/Clinical config · POST /programs
        └── EnrollmentSuccessScreen.tsx  # Success confirmation · stack reset to MemberList
```

### Navigation Flow

```
Login
  └── MemberList ──── tap "+" header ──────────────────────────────────────────┐
        ├── ProgramOverview (tap member card)                                   │
        │     ├── MealCapture (tap FAB)                                         │
        │     │     └── NutritionResult (after upload)                         │
        │     │           └── AdherenceDashboard (tap "View Dashboard")        │
        │     └── AdherenceDashboard (tap "View Full Dashboard")               │
        └── MealCapture (tap "Log Meal" on member card)                        │
              └── NutritionResult                                               │
                    └── AdherenceDashboard                                     │
                                                                               │
  ┌────────────────────────────────────────────────────────────────────────────┘
  │  Enrollment Flow
  └── AddMember
        └── CreateProgram
              └── ConfigureComponents
                    └── EnrollmentSuccess
                          └── MemberList  (navigation.reset — no back)
```

---

## 10. Troubleshooting

### "Network Error" — can't reach backend

1. Check backend is running: `docker-compose ps`
2. Test from phone browser: open `http://<LAN_IP>:8000/health`
3. Confirm API URL in `src/services/api.ts` matches your LAN IP
4. Confirm phone and laptop are on the **same Wi-Fi**

### "Project incompatible with this version of Expo Go"

This project requires **Expo Go 54.x** (SDK 54).
- Update Expo Go in the App Store / Play Store
- Or clear cache: `npx expo start --clear`

### TurboModule / PlatformConstants crash

React Native version mismatch — clear and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
npx expo start --clear
```

### Blank screen after navigating

Clear Metro cache and reload:

```bash
npx expo start --clear
```
Then press `r` in the terminal to reload.

### Camera permission denied

- **iPhone:** Settings → Expo Go → Camera → Allow
- **Android:** Settings → Apps → Expo Go → Permissions → Camera → Allow
- **iOS Simulator:** Device menu → Privacy & Security → Camera → toggle Expo Go

### "Metro bundler failed to start"

Port 8081 already in use:

```bash
npx expo start --port 8082
```

Or kill the existing process:

```bash
# Mac / Linux
lsof -ti:8081 | xargs kill

# Windows
netstat -ano | findstr :8081
taskkill /PID <PID> /F
```

### "Unable to resolve module"

```bash
rm -rf node_modules package-lock.json
npm install
npx expo start --clear
```

### Login fails with 401

Backend database may be in a bad state:

```bash
docker-compose down -v
docker-compose up --build
```

This wipes the DB and re-seeds fresh demo data.
