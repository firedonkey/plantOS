import express from "express";

import { getConfig } from "./config.js";
import { ensureProvisioningSchema } from "./db/ensureSchema.js";
import { pool } from "./db/pool.js";
import { sendError } from "./lib/errors.js";
import { attachDevUser } from "./middleware/devAuth.js";
import { devicesRouter } from "./routes/devices.js";

const config = getConfig();
const app = express();

app.disable("x-powered-by");
app.use(express.json({ limit: "256kb" }));

app.get("/health", async (_req, res, next) => {
  try {
    await pool.query("SELECT 1");
    return res.json({ ok: true, service: "plantlab-provision-backend" });
  } catch (error) {
    return next(error);
  }
});

// Replace this with your real session or JWT auth middleware in production.
// For local testing only, set ENABLE_DEV_AUTH=true.
app.use(attachDevUser);

app.use("/api/devices", devicesRouter);

app.use((error, req, res, _next) => {
  if (req.path !== "/health") {
    sendError(res, error);
    return;
  }
  sendError(res, error);
});

async function start() {
  await ensureProvisioningSchema(pool);
  app.listen(config.port, () => {
    console.log(`[provision-backend] listening on port ${config.port}`);
  });
}

start().catch((error) => {
  console.error("[provision-backend] startup failed", error);
  process.exit(1);
});
