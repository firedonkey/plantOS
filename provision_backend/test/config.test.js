import test from "node:test";
import assert from "node:assert/strict";

import { getConfig } from "../src/config.js";

function withEnv(values, fn) {
  const previous = new Map();
  for (const [key, value] of Object.entries(values)) {
    previous.set(key, process.env[key]);
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }
  try {
    return fn();
  } finally {
    for (const [key, value] of previous.entries()) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
}

test("config defaults provisioning DB pool to a small Cloud SQL-safe size", () => {
  withEnv(
    {
      DATABASE_URL: "postgresql://plantlab_user:secret@localhost:5432/plantlab",
      PLANTLAB_PROVISIONING_DB_POOL_MAX: undefined
    },
    () => {
      const config = getConfig();

      assert.equal(config.databasePoolMax, 3);
    }
  );
});

test("config allows provisioning DB pool max override", () => {
  withEnv(
    {
      DATABASE_URL: "postgresql://plantlab_user:secret@localhost:5432/plantlab",
      PLANTLAB_PROVISIONING_DB_POOL_MAX: "2"
    },
    () => {
      const config = getConfig();

      assert.equal(config.databasePoolMax, 2);
    }
  );
});
