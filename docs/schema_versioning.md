# Schema Versioning

PlantLab schema versions use `MAJOR.MINOR`.

Current version: `1.0`

Compatibility policy:

- `1.x` changes should be additive and backward compatible.
- Unknown additive fields are accepted by the backend and ignored by firmware.
- Removing or changing the meaning of a field requires a new major version.
- The backend rejects unsupported major versions before processing a message.

Firmware/backend compatibility:

- Firmware should send `schema_version`.
- Backend validates the major version.
- Minor version changes must preserve required field behavior.
- Firmware should ignore fields it does not recognize.

TODO:

- Add automated JSON Schema to Pydantic and TypeScript generation.
