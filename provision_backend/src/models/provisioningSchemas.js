import { z } from "zod";

export const claimTokenResponseSchema = z.object({
  ok: z.literal(true),
  claim_token: z.string(),
  setup_code: z.string(),
  setup_url: z.string().url(),
  expected_device_id: z.string().optional(),
  expires_at: z.string().datetime()
});

const bleDeviceIdentitySchema = z
  .object({
    source: z.string().trim().max(40).optional().nullable(),
    schema_version: z.number().int().positive().optional().nullable(),
    device_id: z
      .string()
      .trim()
      .min(3, "device_identity.device_id is required.")
      .max(120, "device_identity.device_id is too long."),
    hardware_device_id: z.string().trim().min(3).max(120).optional().nullable(),
    hardware_model: z.string().trim().max(120).optional().nullable(),
    hardware_version: z.string().trim().max(120).optional().nullable(),
    software_version: z.string().trim().max(120).optional().nullable(),
    node_role: z.string().trim().max(40).optional().nullable(),
    camera_role: z.enum(["top", "side"]).optional().nullable(),
    display_name: z.string().trim().max(120).optional().nullable(),
    ble_name: z.string().trim().max(120).optional().nullable(),
    serial_number: z.string().trim().max(120).optional().nullable()
  })
  .strict();

const capabilityValueSchema = z.union([
  z.boolean(),
  z.number().finite(),
  z.string().trim().max(120),
  z.array(z.string().trim().max(120)).max(20)
]);

export const claimTokenPayloadSchema = z
  .object({
    device_name: z.string().trim().max(120, "device_name is too long.").optional().nullable(),
    location: z.string().trim().max(120, "location is too long.").optional().nullable(),
    device_identity: bleDeviceIdentitySchema.optional()
  })
  .strict();

export const setupCodePayloadSchema = z
  .object({
    serial_number: z
      .string()
      .trim()
      .min(1, "serial_number is required.")
      .max(80, "serial_number is too long."),
    device_name: z.string().trim().max(120, "device_name is too long.").optional(),
    location: z.string().trim().max(120, "location is too long.").optional()
  })
  .strict();

export const claimTokenStatusPayloadSchema = z
  .object({
    claim_token: z
      .string()
      .trim()
      .min(6, "claim_token is required.")
      .max(120, "claim_token is too long.")
  })
  .strict();

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
  capabilities: z.record(z.string(), capabilityValueSchema).default({}),
  node_role: z.enum(["single_board", "master", "camera"]).default("single_board"),
  camera_role: z.enum(["top", "side"]).optional(),
  node_index: z.number().int().positive().optional(),
  display_name: z.string().trim().max(120, "display_name is too long.").optional(),
  hardware_model: z.string().trim().max(120, "hardware_model is too long.").optional(),
  factory_reset: z.boolean().default(false),
  attach_to_platform_device_id: z.number().int().positive().optional()
});

export const registerDeviceResponseSchema = z.object({
  ok: z.literal(true),
  device_id: z.string(),
  platform_device_id: z.number().int(),
  device_name: z.string(),
  status: z.string(),
  device_access_token: z.string(),
  node_role: z.enum(["single_board", "master", "camera"]).optional(),
  camera_role: z.enum(["top", "side"]).nullable().optional(),
  node_index: z.number().int().positive().nullable().optional()
});
