import assert from "node:assert/strict";
import { access, readFile, stat } from "node:fs/promises";
import { constants } from "node:fs";
import { test } from "node:test";

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));

test("native iOS development build configuration is present", async () => {
  const [appConfig, easConfig, packageConfig, rootLayout] = await Promise.all([
    readJson(new URL("../app.json", import.meta.url)),
    readJson(new URL("../eas.json", import.meta.url)),
    readJson(new URL("../package.json", import.meta.url)),
    readFile(new URL("../app/_layout.tsx", import.meta.url), "utf8"),
  ]);

  assert.equal(packageConfig.dependencies["expo-dev-client"], "~6.0.21");
  assert.match(rootLayout, /import\s+["']expo-dev-client["'];/);
  assert.equal(packageConfig.scripts.start, "expo start");
  assert.equal(
    packageConfig.scripts["start:dev"],
    "bash scripts/mobile/start_dev_client.sh --host lan",
  );
  assert.equal(packageConfig.scripts["build:ios:dev"], "bash scripts/mobile/build_ios_dev.sh");
  assert.equal(
    packageConfig.scripts["build:ios:sim"],
    "bash scripts/mobile/build_ios_dev.sh --profile development-simulator",
  );
  assert.equal(packageConfig.scripts["clean:metro"], "bash scripts/mobile/clean_metro_cache.sh");
  assert.equal(packageConfig.scripts["register:ios"], "bash scripts/mobile/register_ios_device.sh");

  for (const scriptPath of [
    "../scripts/mobile/build_ios_dev.sh",
    "../scripts/mobile/start_dev_client.sh",
    "../scripts/mobile/clean_metro_cache.sh",
    "../scripts/mobile/register_ios_device.sh",
  ]) {
    const scriptUrl = new URL(scriptPath, import.meta.url);
    assert.equal((await stat(scriptUrl)).isFile(), true);
    await access(scriptUrl, constants.X_OK);
  }

  assert.equal(appConfig.expo.scheme, "plantlab");
  assert.equal(appConfig.expo.ios.bundleIdentifier, "com.plantlab.mobile");
  assert.equal(appConfig.expo.ios.buildNumber, "1");
  assert.match(
    appConfig.expo.ios.infoPlist.NSBluetoothAlwaysUsageDescription,
    /Bluetooth/,
  );
  assert.match(
    appConfig.expo.ios.infoPlist.NSLocalNetworkUsageDescription,
    /setup network/,
  );

  assert.deepEqual(easConfig.build.development, {
    developmentClient: true,
    distribution: "internal",
  });
  assert.equal(
    easConfig.build["development-simulator"].developmentClient,
    true,
  );
  assert.equal(easConfig.build["development-simulator"].ios.simulator, true);
});

test("README documents native iOS build workflow and validation", async () => {
  const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");

  for (const requiredText of [
    "Expo Go vs native development builds",
    "iOS development build prerequisites",
    "First-time EAS setup",
    "npm run register:ios",
    "Build and install on a real iPhone",
    "npm run clean:metro",
    "docs/mobile_troubleshooting.md",
    "EXPO_PUBLIC_API_BASE_URL",
    "Mac's LAN address",
    "Native capability validation checklist",
    "BLE provisioning",
    "Camera/QR",
    "Auth/session",
  ]) {
    assert.match(readme, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});
