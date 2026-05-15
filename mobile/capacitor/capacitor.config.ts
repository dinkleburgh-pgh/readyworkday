import type { CapacitorConfig } from "@capacitor/cli";
import fs from "node:fs";
import path from "node:path";

function loadEnvValue(key: string, fallback: string): string {
  const direct = String(process.env[key] || "").trim();
  if (direct) {
    return direct;
  }

  const envPath = path.resolve(__dirname, ".env");
  if (!fs.existsSync(envPath)) {
    return fallback;
  }

  try {
    const lines = fs.readFileSync(envPath, "utf-8").split(/\r?\n/);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        continue;
      }
      const idx = trimmed.indexOf("=");
      if (idx < 1) {
        continue;
      }
      const k = trimmed.slice(0, idx).trim();
      if (k !== key) {
        continue;
      }
      const v = trimmed.slice(idx + 1).trim();
      if (v) {
        return v;
      }
    }
  } catch {
    return fallback;
  }

  return fallback;
}

const appId = loadEnvValue("TRUCKAPP_APP_ID", "com.truckapp.mobile");
const appName = loadEnvValue("TRUCKAPP_APP_NAME", "TruckApp");
const serverUrl = loadEnvValue("TRUCKAPP_MOBILE_URL", "https://localhost:8501");

const config: CapacitorConfig = {
  appId,
  appName,
  webDir: "web",
  server: {
    url: serverUrl,
    cleartext: true,
    androidScheme: "https"
  },
  ios: {
    contentInset: "automatic"
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1000,
      launchAutoHide: true
    }
  }
};

export default config;
