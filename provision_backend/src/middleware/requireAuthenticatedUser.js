import { ApiError } from "../lib/errors.js";

// This middleware assumes your existing auth layer already populated req.user.
// Replace the shape checks here if your auth system uses different fields.
export function requireAuthenticatedUser(req, _res, next) {
  if (!req.user || !req.user.id) {
    return next(
      new ApiError(401, "unauthorized", "You must be signed in to perform this action.")
    );
  }

  return next();
}
