export function getApiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

export function isMockFallbackEnabled(): boolean {
  const value = String(process.env.EXPO_PUBLIC_ENABLE_MOCK_FALLBACK ?? "false").trim().toLowerCase();
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
