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

export async function createClaimTokenForUser(userId) {
  const claimToken = generateClaimToken();
  const createdAt = nowUtc();
  const expiresAt = expiresAtFromNow(config.claimTokenTtlMinutes);

  const query = `
    INSERT INTO device_claim_tokens (
      claim_token,
      user_id,
      created_at,
      expires_at,
      used_at,
      used_by_device_id
    )
    VALUES ($1, $2, $3, $4, NULL, NULL)
    RETURNING claim_token, expires_at
  `;

  const { rows } = await withTransaction((client) =>
    client.query(query, [claimToken, userId, createdAt, expiresAt])
  );

  return rows[0];
}

export async function registerDeviceFromClaim(payload) {
  return withTransaction(async (client) => {
    const claimResult = await client.query(
      `
        SELECT
          dct.claim_token,
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
          d.device_id,
          d.owner_user_id,
          d.device_name,
          d.status
        FROM devices d
        WHERE d.device_id = $1
        FOR UPDATE
      `,
      [payload.device_id]
    );

    const existingDevice = deviceResult.rows[0];
    if (existingDevice && existingDevice.owner_user_id !== claim.user_id) {
      throw new ApiError(
        409,
        "device_owned_by_another_user",
        "This device is already registered to another user."
      );
    }

    let deviceRow;
    if (existingDevice) {
      const { rows } = await client.query(
        `
          UPDATE devices
          SET
            owner_user_id = $2,
            hardware_version = $3,
            software_version = $4,
            capabilities = $5::jsonb,
            status = 'online',
            updated_at = NOW()
          WHERE id = $1
          RETURNING id, device_id, device_name, status
        `,
        [
          existingDevice.id,
          claim.user_id,
          payload.hardware_version,
          payload.software_version,
          JSON.stringify(payload.capabilities)
        ]
      );
      deviceRow = rows[0];
    } else {
      const { rows } = await client.query(
        `
          INSERT INTO devices (
            device_id,
            owner_user_id,
            device_name,
            status,
            hardware_version,
            software_version,
            capabilities,
            created_at,
            updated_at,
            last_seen_at
          )
          VALUES ($1, $2, $3, 'online', $4, $5, $6::jsonb, NOW(), NOW(), NOW())
          RETURNING id, device_id, device_name, status
        `,
        [
          payload.device_id,
          claim.user_id,
          buildDefaultDeviceName(payload.device_id),
          payload.hardware_version,
          payload.software_version,
          JSON.stringify(payload.capabilities)
        ]
      );
      deviceRow = rows[0];
    }

    const deviceAccessToken = generateDeviceAccessToken(config.deviceTokenBytes);
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
      `,
      [deviceRow.id, tokenHash]
    );

    await client.query(
      `
        UPDATE device_claim_tokens
        SET used_at = NOW(), used_by_device_id = $2
        WHERE claim_token = $1
      `,
      [payload.claim_token, deviceRow.device_id]
    );

    return {
      ok: true,
      device_id: deviceRow.device_id,
      device_name: deviceRow.device_name,
      status: deviceRow.status,
      device_access_token: deviceAccessToken
    };
  });
}
