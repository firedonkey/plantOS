import { z } from "zod";

export const claimTokenResponseSchema = z.object({
  ok: z.literal(true),
  claim_token: z.string(),
  expires_at: z.string().datetime()
});

export const claimTokenPayloadSchema = z.object({}).strict();

export const registerDeviceSchema = z.object({
  device_id: z
    .string()
    .trim()
    .min(3, "device_id must be at least 3 characters.")
    .max(120, "device_id must be at most 120 characters."),
  claim_token: z
    .string()
    .trim()
    .min(6, "claim_token is required.")
    .max(120, "claim_token is too long."),
  hardware_version: z
    .string()
    .trim()
    .min(1, "hardware_version is required.")
    .max(60, "hardware_version is too long."),
  software_version: z
    .string()
    .trim()
    .min(1, "software_version is required.")
    .max(60, "software_version is too long."),
  capabilities: z.record(z.string(), z.boolean()).default({})
});

export const registerDeviceResponseSchema = z.object({
  ok: z.literal(true),
  device_id: z.string(),
  device_name: z.string(),
  status: z.string(),
  device_access_token: z.string()
});
