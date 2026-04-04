---
name: mobile-app-builder
description: Build production-ready iOS and Android mobile apps using React Native and Expo. Use when the user wants a mobile app, phone app, iOS app, Android app, or cross-platform app. Triggers on phrases like "build me a mobile app", "create an iOS app", "I need an Android app", "build a React Native app". Generates complete Expo project with navigation, screens, local storage, and App Store submission pack.
metadata:
  version: '1.0'
  category: build
  icon: 📱
  color: '#8b5cf6'
---

# Mobile App Builder

## When to Use This Skill

Apply this skill when the user wants to build a native mobile application:

- "Build me a mobile app for X"
- "Create an iOS/Android app"
- "I need a React Native app"
- "Build a phone app that does Y"
- Any request for a mobile, native, or cross-platform app

## What This Skill Builds

A production-ready React Native / Expo application:

**App Structure**
- Expo SDK (latest stable)
- React Navigation (bottom tabs + stack navigator)
- TypeScript throughout
- Expo Router for file-based routing (optional)

**Screens**
- Onboarding flow (3-slide swipeable intro)
- Auth screens (login, register) with form validation
- Main tab screens (home, list, profile)
- Detail screens with back navigation
- Settings screen

**State & Storage**
- React Context for global state (auth, theme)
- AsyncStorage for local persistence
- Optional: Zustand for complex state

**UI Components**
- Custom Button (variants: primary/secondary/outline/danger)
- Card component with shadow
- ListItem with icon + chevron
- EmptyState component
- LoadingSpinner
- Toast/Snackbar notifications

**Platform Features**
- Dark/light mode support
- Safe area handling (notch/dynamic island)
- Haptic feedback on key actions
- Proper keyboard avoiding behavior
- Pull-to-refresh on list screens

**App Store Ready**
- app.json with all required metadata
- Icon and splash screen configuration
- Build instructions for EAS Build
- Step-by-step App Store + Google Play submission guide

## Instructions

1. **Parse the request** — identify: app category, core screens, data model, auth requirements, device features needed (camera, location, notifications)

2. **Show build plan** — list screens, navigation structure, and data flow

3. **Build in 3 passes**:
   - Pass 1: Config (package.json, app.json, tsconfig, theme.ts, types.ts)
   - Pass 2: Navigation shell + reusable components (Button, Card, ListItem, EmptyState)
   - Pass 3: All screens with real logic and data

4. **Code quality rules**:
   - React Native StyleSheet (no inline style objects for performance)
   - Proper TypeScript interfaces for all props and data
   - No web-only APIs (no localStorage, no window, no document)
   - Expo-compatible imports only
   - Real content specific to the app domain

5. **Preview**: Use Expo Snack iframe for preview — include snack-compatible code

## Output Format

```tsx:/src/screens/HomeScreen.tsx
// complete React Native screen code
```

## Example Input → Output

Input: "Build a fitness tracking app where users log workouts, set goals, and see their progress over time"

Output includes:
- `/src/screens/HomeScreen.tsx` — today's workout summary + streak
- `/src/screens/LogWorkoutScreen.tsx` — exercise picker + set/rep logging
- `/src/screens/ProgressScreen.tsx` — charts and personal records
- `/src/screens/ProfileScreen.tsx` — goals, settings, history
- `/src/components/` — WorkoutCard, ExerciseItem, ProgressChart
- `app.json` — Expo config with correct app name and icons
- EAS build commands in README
