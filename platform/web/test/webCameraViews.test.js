import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path) => readFile(join(testDir, path), "utf8");

function escaped(text) {
  return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
}

test("web dashboard renders latest top and side camera views together", async () => {
  const dashboardSource = await readText("../src/screens/DeviceDashboardScreen.tsx");
  const apiSource = await readText("../src/api/devices.ts");
  const typeSource = await readText("../src/types/api.ts");

  for (const requiredText of [
    "<CameraViewsRow",
    'title: "Top view"',
    'title: "Side view"',
    'runCommand("capture_image", { cameraRole: "top" })',
    'runCommand("capture_image", { cameraRole: "side" })',
    'isActionBlocked("capture_image", { cameraRole: "top" })',
    'isActionBlocked("capture_image", { cameraRole: "side" })',
    "findLatestCameraImage(dashboard.recentImages, \"top\")",
    "findLatestCameraImage(dashboard.recentImages, \"side\")",
  ]) {
    assert.match(dashboardSource, escaped(requiredText));
  }

  assert.match(apiSource, escaped("/api/devices/${deviceId}/images?camera_role=top&limit=1"));
  assert.match(apiSource, escaped("/api/devices/${deviceId}/images?camera_role=side&limit=1"));
  assert.match(apiSource, escaped("cameraImages,"));
  assert.match(apiSource, escaped("cameraRole: created.camera_role ?? options?.cameraRole"));
  assert.match(typeSource, escaped("cameraImages?: Partial<Record<CameraRole, LatestImage>>;"));
  assert.match(typeSource, escaped('cameraRole?: CameraRole | "all";'));
});
