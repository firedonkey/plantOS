-- Suggested PostgreSQL schema for PlantLab device onboarding.
-- This assumes the existing platform `users` and `devices` tables already exist.

CREATE TABLE IF NOT EXISTS device_claim_tokens (
  claim_token TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  used_by_device_id INTEGER REFERENCES devices(id)
);

CREATE INDEX IF NOT EXISTS idx_device_claim_tokens_user_id
  ON device_claim_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_device_claim_tokens_expires_at
  ON device_claim_tokens(expires_at);

CREATE TABLE IF NOT EXISTS device_hardware_ids (
  hardware_device_id TEXT PRIMARY KEY,
  device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  hardware_version TEXT,
  software_version TEXT,
  capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_device_hardware_ids_device_id
  ON device_hardware_ids(device_id);

CREATE TABLE IF NOT EXISTS device_access_tokens (
  id BIGSERIAL PRIMARY KEY,
  device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_device_access_tokens_device_id
  ON device_access_tokens(device_id);

INSERT INTO device_serial_numbers (serial_number, hardware_model, status)
VALUES
  ('123', 'raspberry_pi_3_test', 'available'),
  ('SN-20260428-016521', 'raspberry_pi_3_label_test', 'available')
ON CONFLICT (serial_number) DO NOTHING;
