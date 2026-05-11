export function getApiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}
