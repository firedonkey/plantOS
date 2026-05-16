import AsyncStorage from "@react-native-async-storage/async-storage";

const HIDDEN_DEVICE_IDS_KEY = "plantlab.hidden_device_ids";

export async function hideDeviceFromActiveList(deviceId: string): Promise<void> {
  const normalized = normalizeDeviceId(deviceId);
  if (!normalized) {
    return;
  }
  const ids = await loadHiddenDeviceIds();
  ids.add(normalized);
  await AsyncStorage.setItem(HIDDEN_DEVICE_IDS_KEY, JSON.stringify([...ids]));
}

export async function loadHiddenDeviceIds(): Promise<Set<string>> {
  const raw = await AsyncStorage.getItem(HIDDEN_DEVICE_IDS_KEY);
  if (!raw) {
    return new Set();
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return new Set();
    }
    return new Set(parsed.map((value) => normalizeDeviceId(String(value))).filter(Boolean));
  } catch {
    return new Set();
  }
}

function normalizeDeviceId(deviceId: string): string {
  return String(deviceId).trim();
}
