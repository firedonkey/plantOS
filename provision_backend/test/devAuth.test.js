import test from "node:test";
import assert from "node:assert/strict";

import { attachDevUser } from "../src/middleware/devAuth.js";

test("attachDevUser preserves an existing trusted user", async () => {
  process.env.ENABLE_DEV_AUTH = "true";
  process.env.DEV_AUTH_USER_ID = "1";
  process.env.DEV_AUTH_EMAIL = "dev@example.com";

  const req = {
    user: {
      id: 3,
      email: "dev@plantlab.local"
    },
    header() {
      return undefined;
    }
  };

  let nextCalled = false;
  attachDevUser(req, {}, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, true);
  assert.deepEqual(req.user, {
    id: 3,
    email: "dev@plantlab.local"
  });
});

test("attachDevUser fills a dev user when no trusted user exists", async () => {
  process.env.ENABLE_DEV_AUTH = "true";
  process.env.DEV_AUTH_USER_ID = "1";
  process.env.DEV_AUTH_EMAIL = "dev@example.com";

  const req = {
    header(name) {
      if (name === "x-dev-user-id") {
        return "7";
      }
      if (name === "x-dev-user-email") {
        return "tester@example.com";
      }
      return undefined;
    }
  };

  let nextCalled = false;
  attachDevUser(req, {}, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, true);
  assert.deepEqual(req.user, {
    id: 7,
    email: "tester@example.com"
  });
});
