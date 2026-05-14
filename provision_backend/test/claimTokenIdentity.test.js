import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");

function readSource(path) {
  return readFileSync(resolve(repoRoot, path), "utf8");
}

test("claim token schema accepts BLE identity without serial number", () => {
  const source = readSource("src/models/provisioningSchemas.js");

  assert.match(source, /const bleDeviceIdentitySchema = z/);
  assert.match(source, /device_id:[\s\S]*?min\(3, "device_identity\.device_id is required\."\)/);
  assert.match(source, /hardware_device_id: z\.string\(\)\.trim\(\)\.min\(3\)\.max\(120\)\.optional\(\)\.nullable\(\)/);
  assert.match(source, /software_version: z\.string\(\)\.trim\(\)\.max\(120\)\.optional\(\)\.nullable\(\)/);
  assert.match(source, /ble_name: z\.string\(\)\.trim\(\)\.max\(120\)\.optional\(\)\.nullable\(\)/);
  assert.match(source, /serial_number: z\.string\(\)\.trim\(\)\.max\(120\)\.optional\(\)\.nullable\(\)/);
  assert.match(source, /device_identity: bleDeviceIdentitySchema\.optional\(\)/);
});

test("register schema still requires claim token and device id", () => {
  const source = readSource("src/models/provisioningSchemas.js");

  assert.match(source, /export const registerDeviceSchema = z\.object/);
  assert.match(source, /device_id:[\s\S]*?min\(3, "device_id must be at least 3 characters\."\)/);
  assert.match(source, /claim_token:[\s\S]*?min\(6, "claim_token is required\."\)/);
  assert.match(source, /hardware_version:[\s\S]*?min\(1, "hardware_version is required\."\)/);
  assert.match(source, /software_version:[\s\S]*?min\(1, "software_version is required\."\)/);
});

test("provision service persists expected identity and rejects mismatched registration", () => {
  const source = readSource("src/services/deviceProvisioningService.js");

  assert.match(source, /function normalizeBleDeviceIdentity/);
  assert.match(source, /expectedDeviceId: hardwareDeviceId/);
  assert.match(source, /expected_device_id,\s*\n\s*device_identity,/);
  assert.match(source, /deviceIdentity \? JSON\.stringify\(deviceIdentity\) : null/);
  assert.match(source, /claim\.expected_device_id && payload\.device_id !== claim\.expected_device_id/);
  assert.match(source, /expected_device_id_mismatch/);
});

test("provision routes expose serialless claim-token response and keep setup-code fallback", () => {
  const source = readSource("src/routes/devices.js");

  assert.match(source, /devicesRouter\.post\(\s*\n\s*"\/claim-token"/);
  assert.match(source, /createClaimTokenForUser\(req\.user\.id/);
  assert.match(source, /deviceIdentity: payload\.device_identity/);
  assert.match(source, /expected_device_id: claimToken\.expected_device_id \|\| undefined/);
  assert.match(source, /devicesRouter\.post\(\s*\n\s*"\/setup-code"/);
  assert.match(source, /createClaimTokenForUserAndSerial/);
});
