export function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

export function isMockFallbackEnabled(): boolean {
  const value = String(import.meta.env.VITE_ENABLE_MOCK_FALLBACK ?? "false").trim().toLowerCase();
  return value === "1" || value === "true" || value === "yes" || value === "on";
}
