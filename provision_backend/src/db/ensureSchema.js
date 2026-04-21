export async function ensureProvisioningSchema(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS device_serial_numbers (
      serial_number TEXT PRIMARY KEY,
      hardware_model TEXT,
      status TEXT NOT NULL DEFAULT 'available',
      claimed_by_user_id INTEGER REFERENCES users(id),
      claimed_by_device_id INTEGER REFERENCES devices(id),
      claimed_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await pool.query(`
    INSERT INTO device_serial_numbers (serial_number, hardware_model, status)
    VALUES ('123', 'raspberry_pi_3_test', 'available')
    ON CONFLICT (serial_number) DO NOTHING
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS device_claim_tokens (
      claim_token TEXT PRIMARY KEY,
      serial_number TEXT REFERENCES device_serial_numbers(serial_number),
      device_name TEXT,
      location TEXT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      expires_at TIMESTAMPTZ NOT NULL,
      used_at TIMESTAMPTZ,
      used_by_device_id INTEGER REFERENCES devices(id)
    )
  `);

  await pool.query(`
    ALTER TABLE device_claim_tokens
      ADD COLUMN IF NOT EXISTS serial_number TEXT REFERENCES device_serial_numbers(serial_number)
  `);

  await pool.query(`
    ALTER TABLE device_claim_tokens
      ADD COLUMN IF NOT EXISTS device_name TEXT
  `);

  await pool.query(`
    ALTER TABLE device_claim_tokens
      ADD COLUMN IF NOT EXISTS location TEXT
  `);

  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_device_claim_tokens_user_id
      ON device_claim_tokens(user_id)
  `);

  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_device_claim_tokens_expires_at
      ON device_claim_tokens(expires_at)
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS device_hardware_ids (
      hardware_device_id TEXT PRIMARY KEY,
      device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
      hardware_version TEXT,
      software_version TEXT,
      capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      last_seen_at TIMESTAMPTZ
    )
  `);

  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_device_hardware_ids_device_id
      ON device_hardware_ids(device_id)
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS device_access_tokens (
      id BIGSERIAL PRIMARY KEY,
      device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
      token_hash TEXT NOT NULL UNIQUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      revoked_at TIMESTAMPTZ
    )
  `);

  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_device_access_tokens_device_id
      ON device_access_tokens(device_id)
  `);
}
