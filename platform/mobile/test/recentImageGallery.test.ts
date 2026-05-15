import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path: string) => readFile(join(testDir, path), "utf8");

test("recent image gallery sends auth headers only to backend proxy image URLs", async () => {
  const source = await readText("../src/components/RecentImageGallery.tsx");

  assert.match(source, /function shouldUseImageHeaders\(url: string\): boolean/);
  assert.equal(source.includes('const path = url.replace(/^https?:\\/\\/[^/]+/i, "");'), true);
  assert.match(source, /path\.startsWith\("\/api\/images\/"\)/);
  assert.match(source, /path\.split\("\?"\)\[0\]\.endsWith\("\/content"\)/);
  assert.match(source, /shouldUseImageHeaders\(image\.url\) && imageHeaders/);
});

test("recent image gallery shows fallback UI when an image fails to load", async () => {
  const source = await readText("../src/components/RecentImageGallery.tsx");

  assert.match(source, /const \[failedImageKeys, setFailedImageKeys\]/);
  assert.match(source, /onError=\{\(\) => setFailedImageKeys/);
  assert.match(source, /Image unavailable/);
  assert.match(source, /styles\.imageFallback/);
});
