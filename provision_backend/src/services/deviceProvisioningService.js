import { getConfig } from "../config.js";
import { withTransaction } from "../db/pool.js";
import { ApiError } from "../lib/errors.js";
import { generateClaimToken, generateDeviceAccessToken, hashToken } from "../lib/tokens.js";

const config = getConfig();

function nowUtc() {
  return new Date();
}

function expiresAtFromNow(minutes) {
  return new Date(Date.now() + minutes * 60 * 1000);
}

function buildDefaultDeviceName(deviceId) {
  return `PlantLab ${deviceId}`;
}

function buildDefaultNodeDisplayName(nodeRole, nodeIndex) {
  if (nodeRole === "master") {
    return "Master";
  }
  if (nodeRole === "camera") {
    return nodeIndex ? `Camera ${nodeIndex}` : "Camera";
  }
  return "Raspberry Pi";
}

async function ensureDeviceAccessTokenRecord(client, deviceId, deviceAccessToken) {
  const tokenHash = hashToken(deviceAccessToken);
  await client.query(
    `
      INSERT INTO device_access_tokens (
        device_id,
        token_hash,
        created_at,
        revoked_at
      )
      VALUES ($1, $2, NOW(), NULL)
      ON CONFLICT (token_hash) DO NOTHING
    `,
    [deviceId, tokenHash]
  );
}

async function upsertDeviceHardwareNode(client, payload) {
  await client.query(
    `
      INSERT INTO device_hardware_ids (
        hardware_device_id,
        device_id,
        node_role,
        node_index,
        display_name,
        hardware_model,
        hardware_version,
        software_version,
        capabilities,
        status,
        created_at,
        updated_at,
        last_seen_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, NOW(), NOW(), NOW())
      ON CONFLICT (hardware_device_id) DO UPDATE
      SET
        device_id = EXCLUDED.device_id,
        node_role = EXCLUDED.node_role,
        node_index = EXCLUDED.node_index,
        display_name = EXCLUDED.display_name,
        hardware_model = EXCLUDED.hardware_model,
        hardware_version = EXCLUDED.hardware_version,
        software_version = EXCLUDED.software_version,
        capabilities = EXCLUDED.capabilities,
        status = EXCLUDED.status,
        updated_at = NOW(),
        last_seen_at = NOW()
    `,
    [
      payload.device_id,
      payload.platform_device_id,
      payload.node_role,
      payload.node_index,
      payload.display_name || buildDefaultNodeDisplayName(payload.node_role, payload.node_index),
      payload.hardware_model || null,
      payload.hardware_version,
      payload.software_version,
      JSON.stringify(payload.capabilities),
      "online"
    ]
  );
}

export async function createClaimTokenForUser(userId) {
  return createClaimTokenForUserAndSerial(userId, null);
}

export async function createClaimTokenForUserAndSerial(userId, serialNumber, metadata = {}) {
  const claimToken = generateClaimToken();
  const createdAt = nowUtc();
  const expiresAt = expiresAtFromNow(config.claimTokenTtlMinutes);

  const normalizedSerialNumber = serialNumber?.trim() || null;
  const deviceName = metadata.deviceName?.trim() || null;
  const location = metadata.location?.trim() || null;

  const { rows } = await withTransaction(async (client) => {
    if (normalizedSerialNumber) {
      const serialResult = await client.query(
        `
          SELECT serial_number, status, claimed_by_user_id
          FROM device_serial_numbers
          WHERE serial_number = $1
          FOR UPDATE
        `,
        [normalizedSerialNumber]
      );
      const serial = serialResult.rows[0];
      if (!serial) {
        throw new ApiError(
          404,
          "serial_number_not_found",
          "Device serial number was not found."
        );
      }
      if (serial.status !== "available") {
        if (serial.claimed_by_user_id === userId) {
          throw new ApiError(
            409,
            "serial_number_already_in_account",
            "This device is already in your account. Remove or factory reset the existing device before adding it again."
          );
        }
        throw new ApiError(
          409,
          "serial_number_not_available",
          "Device serial number is not available."
        );
      }
    }

    const query = `
      INSERT INTO device_claim_tokens (
        claim_token,
        serial_number,
        device_name,
        location,
        user_id,
        created_at,
        expires_at,
        used_at,
        used_by_device_id
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, NULL, NULL)
      RETURNING claim_token, serial_number, device_name, location, expires_at
    `;

    return client.query(query, [
      claimToken,
      normalizedSerialNumber,
      deviceName,
      location,
      userId,
      createdAt,
      expiresAt
    ]);
  });

  return rows[0];
}

export async function registerDeviceFromClaim(payload) {
  return withTransaction(async (client) => {
    const claimResult = await client.query(
      `
        SELECT
          dct.claim_token,
          dct.serial_number,
          dct.device_name,
          dct.location,
          dct.user_id,
          dct.created_at,
          dct.expires_at,
          dct.used_at,
          dct.used_by_device_id
        FROM device_claim_tokens dct
        WHERE dct.claim_token = $1
        FOR UPDATE
      `,
      [payload.claim_token]
    );

    const claim = claimResult.rows[0];
    if (!claim) {
      throw new ApiError(
        400,
        "invalid_or_expired_claim_token",
        "Claim token is invalid."
      );
    }

    if (claim.used_at) {
      throw new ApiError(
        409,
        "claim_token_already_used",
        "Claim token was already used."
      );
    }

    if (new Date(claim.expires_at).getTime() <= Date.now()) {
      throw new ApiError(
        400,
        "invalid_or_expired_claim_token",
        "Claim token has expired."
      );
    }

    const deviceResult = await client.query(
      `
        SELECT
          d.id,
          d.user_id,
          d.name,
          h.hardware_device_id
        FROM device_hardware_ids h
        JOIN devices d ON d.id = h.device_id
        WHERE h.hardware_device_id = $1
        FOR UPDATE
      `,
      [payload.device_id]
    );

    const existingDevice = deviceResult.rows[0];
    if (existingDevice && existingDevice.user_id !== claim.user_id) {
      throw new ApiError(
        409,
        "device_owned_by_another_user",
        "This device is already registered to another user."
      );
    }

    const attachDeviceId = payload.attach_to_platform_device_id || null;
    let deviceRow;
    let deviceAccessToken;

    if (attachDeviceId) {
      const attachResult = await client.query(
        `
          SELECT id, user_id, name, location, api_token
          FROM devices
          WHERE id = $1
          FOR UPDATE
        `,
        [attachDeviceId]
      );
      const attachedDevice = attachResult.rows[0];
      if (!attachedDevice || attachedDevice.user_id !== claim.user_id) {
        throw new ApiError(
          404,
          "attach_target_not_found",
          "Target device for node attachment was not found."
        );
      }
      if (existingDevice && existingDevice.id !== attachedDevice.id) {
        throw new ApiError(
          409,
          "hardware_already_attached_elsewhere",
          "This hardware node is already attached to another device."
        );
      }

      deviceAccessToken = attachedDevice.api_token || generateDeviceAccessToken(config.deviceTokenBytes);
      if (!attachedDevice.api_token) {
        const { rows } = await client.query(
          `
            UPDATE devices
            SET
              api_token = $2,
              status_updated_at = NOW()
            WHERE id = $1
            RETURNING id, name, api_token
          `,
          [attachedDevice.id, deviceAccessToken]
        );
        deviceRow = rows[0];
      } else {
        deviceRow = {
          id: attachedDevice.id,
          name: attachedDevice.name,
          api_token: attachedDevice.api_token
        };
      }

      await upsertDeviceHardwareNode(client, {
        ...payload,
        platform_device_id: deviceRow.id
      });
      await ensureDeviceAccessTokenRecord(client, deviceRow.id, deviceAccessToken);
    } else if (existingDevice) {
      deviceAccessToken = generateDeviceAccessToken(config.deviceTokenBytes);
      const { rows } = await client.query(
        `
          UPDATE devices
          SET
            name = COALESCE($3, name),
            location = COALESCE($4, location),
            api_token = $2,
            status_message = 'online',
            status_updated_at = NOW()
          WHERE id = $1
          RETURNING id, name
        `,
        [existingDevice.id, deviceAccessToken, claim.device_name, claim.location]
      );
      deviceRow = rows[0];

      await upsertDeviceHardwareNode(client, {
        ...payload,
        platform_device_id: deviceRow.id
      });
      await ensureDeviceAccessTokenRecord(client, deviceRow.id, deviceAccessToken);
    } else {
      deviceAccessToken = generateDeviceAccessToken(config.deviceTokenBytes);
      const { rows } = await client.query(
        `
          INSERT INTO devices (
            user_id,
            name,
            location,
            api_token,
            status_message,
            status_updated_at,
            created_at
          )
          VALUES ($1, $2, $3, $4, 'online', NOW(), NOW())
          RETURNING id, name
        `,
        [
          claim.user_id,
          claim.device_name || buildDefaultDeviceName(payload.device_id),
          claim.location || null,
          deviceAccessToken
        ]
      );
      deviceRow = rows[0];

      await upsertDeviceHardwareNode(client, {
        ...payload,
        platform_device_id: deviceRow.id
      });
      await ensureDeviceAccessTokenRecord(client, deviceRow.id, deviceAccessToken);
    }

    await client.query(
      `
        UPDATE device_claim_tokens
        SET used_at = NOW(), used_by_device_id = $2
        WHERE claim_token = $1
      `,
      [payload.claim_token, deviceRow.id]
    );

    if (claim.serial_number) {
      await client.query(
        `
          UPDATE device_serial_numbers
          SET
            status = 'claimed',
            claimed_by_user_id = $2,
            claimed_by_device_id = $3,
            claimed_at = COALESCE(claimed_at, NOW()),
            updated_at = NOW()
          WHERE serial_number = $1
        `,
        [claim.serial_number, claim.user_id, deviceRow.id]
      );
    }

    return {
      ok: true,
      device_id: payload.device_id,
      platform_device_id: deviceRow.id,
      device_name: deviceRow.name,
      status: "online",
      device_access_token: deviceAccessToken,
      node_role: payload.node_role,
      node_index: payload.node_index ?? null
    };
  });
}
