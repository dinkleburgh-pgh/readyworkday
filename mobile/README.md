# Mobile App Wrapper Scaffold (Android + iOS)

This folder starts a native wrapper setup for the existing TruckApp web app.

## Layout

```text
mobile/
  README.md
  capacitor/
    .env.example
    .gitignore
    capacitor.config.ts
    package.json
    tsconfig.json
    web/
      .gitkeep
```

## Approach

- Use Capacitor as a native shell.
- Load your existing deployed TruckApp URL inside the native WebView.
- Keep the current web app as the source of truth.

## Quick Start

1. Open a terminal in `mobile/capacitor`.
2. Run `npm install`.
3. Copy `.env.example` to `.env` and set `TRUCKAPP_MOBILE_URL`.
4. Run `npm run cap:sync`.
5. Add platforms:
   - `npm run cap:add:android`
   - `npm run cap:add:ios` (Mac only)
6. Open native IDE projects:
   - `npm run cap:open:android`
   - `npm run cap:open:ios`

See `mobile/capacitor/package.json` scripts for all commands.

Detailed setup instructions are in `mobile/capacitor/SETUP.md`.

API integration targets for native Android are in `mobile/ANDROID_REST_TARGETS.md`.

## Notes

- iOS builds require macOS + Xcode.
- Android builds work from Windows with Android Studio.
- This is an initial scaffold. Native signing, push notifications, camera APIs, and store deployment are separate follow-up steps.

## Android + Rust API Integration

If you already have a Gradle Android app, connect it to the Rust API service instead of parsing app files directly.

Base URL (local dev):

- `http://10.0.2.2:8787` (Android Emulator)
- `http://<your-lan-ip>:8787` (physical device)

Suggested Retrofit interface:

```kotlin
interface TruckApi {
   @GET("/health")
   suspend fun health(): HealthResponse

   @GET("/api/v1/state")
   suspend fun state(): JsonObject

   @GET("/api/v1/fleet")
   suspend fun fleet(): JsonObject

   @PUT("/api/v1/state")
   suspend fun saveState(@Body payload: JsonObject): SaveResponse

   @PUT("/api/v1/fleet")
   suspend fun saveFleet(@Body payload: JsonObject): SaveResponse
}
```

High-level flow:

1. Start TruckApp + Rust API with Docker Compose.
2. Android app calls Rust API endpoints.
3. Keep Streamlit as UI/admin surface; use API for mobile workflow data and actions.
