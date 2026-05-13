export function getApiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

export function isMockFallbackEnabled(): boolean {
  const value = String(process.env.EXPO_PUBLIC_ENABLE_MOCK_FALLBACK ?? "false").trim().toLowerCase();
  return value === "1" || value === "true" || value === "yes" || value === "on";
}
