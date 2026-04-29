import { ApiError } from "../lib/errors.js";

export function attachTrustedPlatformUser(req, _res, next) {
  const expectedSecret = (process.env.PLANTLAB_PROVISIONING_SHARED_SECRET || "").trim();
  if (!expectedSecret) {
    return next();
  }

  const providedSecret = (req.header("x-plantlab-service-secret") || "").trim();
  if (!providedSecret || providedSecret !== expectedSecret) {
    return next();
  }

  const userId = req.header("x-plantlab-user-id");
  const email = req.header("x-plantlab-user-email") || "";
  if (!userId) {
    return next(
      new ApiError(
        401,
        "unauthorized",
        "Trusted provisioning request is missing user identity."
      )
    );
  }

  req.user = {
    id: Number.parseInt(userId, 10),
    email
  };
  return next();
}
