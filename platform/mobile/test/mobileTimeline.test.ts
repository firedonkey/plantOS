import assert from "node:assert/strict";
import { test } from "node:test";

import { getDeviceTimeline } from "../src/api/devices";

test("mobile timeline API maps backend diagnostics timeline events", async () => {
  process.env.EXPO_PUBLIC_API_BASE_URL = "https://backend.example.test";
  const originalFetch = globalThis.fetch;
  const requests: string[] = [];

  globalThis.fetch = (async (input: string | URL | Request) => {
    const url = String(input);
    requests.push(url);
    assert.match(url, /event_type=IMAGE_UPLOADED/);
    assert.match(url, /severity=info/);
    return {
      ok: true,
      json: async () => ({
        events: [
          {
            id: 91,
            event_type: "IMAGE_UPLOADED",
            severity: "info",
            occurred_at: "2026-05-27T12:00:00Z",
            hardware_device_id: "cam-01",
            node_role: "camera",
            correlation_id: "img_91",
            summary: "Image uploaded #91 (manual)",
            data: { image_id: 91, upload_reason: "manual" },
            created_at: "2026-05-27T12:00:01Z",
          },
        ],
        next_before: "2026-05-27T11:59:00Z",
      }),
    } as Response;
  }) as typeof fetch;

  try {
    const result = await getDeviceTimeline("7", { eventType: "IMAGE_UPLOADED", severity: "info" });

    assert.equal(result.usedMock, false);
    assert.equal(requests.length, 1);
    assert.equal(result.timeline.nextBefore, "2026-05-27T11:59:00Z");
    assert.deepEqual(result.timeline.events[0], {
      id: "91",
      eventType: "IMAGE_UPLOADED",
      severity: "info",
      occurredAt: "2026-05-27T12:00:00Z",
      hardwareDeviceId: "cam-01",
      nodeRole: "camera",
      correlationId: "img_91",
      summary: "Image uploaded #91 (manual)",
      code: undefined,
      message: undefined,
      data: { image_id: 91, upload_reason: "manual" },
      createdAt: "2026-05-27T12:00:01Z",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
