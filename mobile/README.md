# CrucibAI Mobile Smoke Tests

Device-farm scaffolding using Detox for React Native targets.
Requires macOS + Xcode (iOS) or Android SDK + emulator (Android).

## Why offline in CI
CI environments don't have iOS Simulators or Android emulators by default.
These tests are skipped unless `DETOX_E2E=1` is exported.

## Run locally
```bash
cd mobile
npm install
npx detox build --configuration ios.sim.debug
npx detox test   --configuration ios.sim.debug
```

## Skip in CI
```bash
# (default)  DETOX_E2E unset  →  tests are skipped
DETOX_E2E=1 npm test
```
