export function attachDevUser(req, _res, next) {
  if (process.env.ENABLE_DEV_AUTH !== "true") {
    return next();
  }

  const userId = req.header("x-dev-user-id") || process.env.DEV_AUTH_USER_ID || "1";
  const email = req.header("x-dev-user-email") || process.env.DEV_AUTH_EMAIL || "dev@example.com";

  req.user = {
    id: Number.parseInt(userId, 10),
    email
  };

  return next();
}
