export function getConfig() {
  const databaseUrl = process.env.DATABASE_URL;
  const cloudSqlConnectionName = process.env.CLOUD_SQL_CONNECTION_NAME;
  const dbPassword = process.env.DB_PASSWORD;
  const dbUser = process.env.DB_USER || "plantlab_user";
  const dbName = process.env.DB_NAME || "plantlab";
  const dbHost = process.env.DB_HOST;
  const dbPort = Number.parseInt(process.env.DB_PORT || "5432", 10);

  if (!databaseUrl && !dbHost && (!cloudSqlConnectionName || !dbPassword)) {
    throw new Error(
      "Set DATABASE_URL, DB_HOST + DB_PASSWORD, or CLOUD_SQL_CONNECTION_NAME + DB_PASSWORD."
    );
  }

  const database = databaseUrl
    ? { connectionString: databaseUrl }
    : {
        user: dbUser,
        password: dbPassword,
        database: dbName,
        host: cloudSqlConnectionName ? `/cloudsql/${cloudSqlConnectionName}` : dbHost,
        port: cloudSqlConnectionName ? undefined : dbPort
      };

  return {
    port: Number.parseInt(process.env.PORT || "3000", 10),
    database,
    claimTokenTtlMinutes: Number.parseInt(process.env.CLAIM_TOKEN_TTL_MINUTES || "15", 10),
    deviceTokenBytes: Number.parseInt(process.env.DEVICE_ACCESS_TOKEN_BYTES || "32", 10)
  };
}
