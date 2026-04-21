import crypto from "crypto";

export function generateClaimToken() {
  return `PL-${crypto.randomBytes(6).toString("base64url").toUpperCase()}`;
}

export function generateDeviceAccessToken(byteLength = 32) {
  return `pla_${crypto.randomBytes(byteLength).toString("base64url")}`;
}

export function hashToken(token) {
  return crypto.createHash("sha256").update(token).digest("hex");
}
