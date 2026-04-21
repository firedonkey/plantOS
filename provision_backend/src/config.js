const REQUIRED_ENV = ["DATABASE_URL"];

export function getConfig() {
  const missing = REQUIRED_ENV.filter((name) => !process.env[name]);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(", ")}`);
  }

  return {
    port: Number.parseInt(process.env.PORT || "3000", 10),
    databaseUrl: process.env.DATABASE_URL,
    claimTokenTtlMinutes: Number.parseInt(process.env.CLAIM_TOKEN_TTL_MINUTES || "15", 10),
    deviceTokenBytes: Number.parseInt(process.env.DEVICE_ACCESS_TOKEN_BYTES || "32", 10)
  };
}
