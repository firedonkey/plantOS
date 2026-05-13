export function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

export function getAuthMode(): "production" | "dev" {
  const mode = String(import.meta.env.VITE_AUTH_MODE ?? "production").trim().toLowerCase();
  if (mode === "dev" || isDevAuthEnabled()) {
    return "dev";
  }
  return "production";
}

export function isDevAuthEnabled(): boolean {
  return envFlag("VITE_ENABLE_DEV_AUTH", false);
}

export function isMockFallbackEnabled(): boolean {
  return envFlag("VITE_ENABLE_MOCK_FALLBACK", false);
}

function envFlag(name: string, defaultValue: boolean): boolean {
  const value = String(import.meta.env[name] ?? (defaultValue ? "true" : "false")).trim().toLowerCase();
  return value === "1" || value === "true" || value === "yes" || value === "on";
}
