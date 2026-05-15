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

## Notes

- iOS builds require macOS + Xcode.
- Android builds work from Windows with Android Studio.
- This is an initial scaffold. Native signing, push notifications, camera APIs, and store deployment are separate follow-up steps.
