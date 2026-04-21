-- Suggested PostgreSQL schema for PlantLab device onboarding.
-- This assumes an existing users table owned by your auth system.

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices (
  id BIGSERIAL PRIMARY KEY,
  device_id TEXT NOT NULL UNIQUE,
  owner_user_id BIGINT NOT NULL REFERENCES users(id),
  device_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'onboarding',
  hardware_version TEXT,
  software_version TEXT,
  capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_devices_owner_user_id
  ON devices(owner_user_id);

CREATE TABLE IF NOT EXISTS device_claim_tokens (
  claim_token TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  used_by_device_id TEXT REFERENCES devices(device_id)
);

CREATE INDEX IF NOT EXISTS idx_device_claim_tokens_user_id
  ON device_claim_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_device_claim_tokens_expires_at
  ON device_claim_tokens(expires_at);

CREATE TABLE IF NOT EXISTS device_access_tokens (
  id BIGSERIAL PRIMARY KEY,
  device_id BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_device_access_tokens_device_id
  ON device_access_tokens(device_id);
