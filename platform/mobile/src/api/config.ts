export function getApiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

export function getAuthMode(): "production" | "dev" {
  const mode = String(process.env.EXPO_PUBLIC_AUTH_MODE ?? "dev").trim().toLowerCase();
  if (mode === "production") {
    return "production";
  }
  return "dev";
}

export function isDevAuthEnabled(): boolean {
  return envFlag("EXPO_PUBLIC_ENABLE_DEV_AUTH", true);
}

export function isMockFallbackEnabled(): boolean {
  return envFlag("EXPO_PUBLIC_ENABLE_MOCK_FALLBACK", false);
}

function envFlag(name: string, defaultValue: boolean): boolean {
  const value = String(process.env[name] ?? (defaultValue ? "true" : "false")).trim().toLowerCase();
  return value === "1" || value === "true" || value === "yes" || value === "on";
}

export function getConfiguredWifiSsidOptions(): string[] {
  const raw = String(process.env.EXPO_PUBLIC_WIFI_SSID_OPTIONS ?? "");
  const seen = new Set<string>();
  const options: string[] = [];
  for (const item of raw.split(",")) {
    const ssid = item.trim();
    if (!ssid || seen.has(ssid)) {
      continue;
    }
    seen.add(ssid);
    options.push(ssid);
  }
  return options;
}
