# Android and iOS Setup Guide

This guide shows how to create native apps from the existing TruckApp web app.

## 1. Prerequisites

### Required for both

- Node.js 20+
- npm 10+
- A deployed HTTPS URL for TruckApp (recommended for production)

### Android

- Windows, macOS, or Linux
- Android Studio (latest)
- Android SDK + emulator (or physical Android device)

### iOS

- macOS only
- Xcode (latest stable)
- CocoaPods
- Apple Developer account for TestFlight/App Store distribution

## 2. Configure the Wrapper

From `mobile/capacitor`:

```bash
npm install
```

Create `.env` from `.env.example` and set values:

```dotenv
TRUCKAPP_MOBILE_URL=https://your-truckapp-domain.example
TRUCKAPP_APP_ID=com.yourcompany.truckapp
TRUCKAPP_APP_NAME=TruckApp
```

Sync Capacitor:

```bash
npm run cap:sync
```

## 3. Android App Setup

Add Android platform:

```bash
npm run cap:add:android
```

Open in Android Studio:

```bash
npm run cap:open:android
```

In Android Studio:

1. Let Gradle finish sync.
2. Set `applicationId` if needed.
3. Choose emulator/device and run.
4. For release builds, configure signing keystore.

Release checklist:

1. Update app icon/splash assets.
2. Set release signing config.
3. Build AAB for Play Store.
4. Complete Play Console listing.

## 4. iOS App Setup

Add iOS platform (Mac only):

```bash
npm run cap:add:ios
```

Open in Xcode:

```bash
npm run cap:open:ios
```

In Xcode:

1. Select team + bundle identifier.
2. Set deployment target.
3. Run on simulator/device.
4. Archive for TestFlight/App Store.

Release checklist:

1. Update app icon/splash assets.
2. Configure signing/capabilities.
3. Archive and upload via Xcode.
4. Complete App Store Connect metadata.

## 5. Updating App Content

Because this wrapper uses `server.url`, your native app loads the live web app.

- Web changes deploy instantly to app users.
- Native store updates are only needed when changing native capabilities or wrapper configuration.

## 6. Common Commands

```bash
npm run cap:doctor
npm run cap:sync
npm run cap:open:android
npm run cap:open:ios
```

## 7. Notes

- iOS cannot auto-install from web; users must choose Add to Home Screen in Safari.
- If your production site is HTTPS, keep `TRUCKAPP_MOBILE_URL` as HTTPS.
- For local testing on physical devices, use a LAN URL reachable by that device.
