import express from "express";

import { getConfig } from "../config.js";
import {
  claimTokenPayloadSchema,
  registerDeviceResponseSchema,
  registerDeviceSchema
} from "../models/provisioningSchemas.js";
import { ApiError } from "../lib/errors.js";
import { requireAuthenticatedUser } from "../middleware/requireAuthenticatedUser.js";
import {
  createClaimTokenForUser,
  registerDeviceFromClaim
} from "../services/deviceProvisioningService.js";

export const devicesRouter = express.Router();
const config = getConfig();

function buildSetupUrl(setupCode) {
  const url = new URL(config.localSetupUrl);
  url.searchParams.set("setup_code", setupCode);
  return url.toString();
}

devicesRouter.post(
  "/claim-token",
  requireAuthenticatedUser,
  async (req, res, next) => {
    try {
      claimTokenPayloadSchema.parse(req.body ?? {});

      const claimToken = await createClaimTokenForUser(req.user.id);
      return res.status(201).json({
        ok: true,
        claim_token: claimToken.claim_token,
        setup_code: claimToken.claim_token,
        setup_url: buildSetupUrl(claimToken.claim_token),
        expires_at: new Date(claimToken.expires_at).toISOString()
      });
    } catch (error) {
      return next(error);
    }
  }
);

devicesRouter.post("/register", async (req, res, next) => {
  try {
    const payload = registerDeviceSchema.parse(req.body);
    const response = await registerDeviceFromClaim(payload);
    registerDeviceResponseSchema.parse(response);
    return res.status(201).json(response);
  } catch (error) {
    if (error.name === "ZodError") {
      return next(
        new ApiError(422, "validation_error", "Request body is invalid.", error.flatten())
      );
    }
    return next(error);
  }
});
