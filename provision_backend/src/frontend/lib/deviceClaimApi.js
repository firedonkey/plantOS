export class ClaimTokenError extends Error {
  constructor(message, statusCode = 500, payload = null) {
    super(message);
    this.name = "ClaimTokenError";
    this.statusCode = statusCode;
    this.payload = payload;
  }
}

export async function requestDeviceClaimToken({ signal } = {}) {
  const response = await fetch("/api/devices/claim-token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json"
    },
    credentials: "include",
    body: JSON.stringify({}),
    signal
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch (_error) {
    payload = null;
  }

  if (!response.ok || !payload?.ok) {
    const message =
      payload?.message ||
      payload?.error ||
      "Could not create a claim token. Please try again.";
    throw new ClaimTokenError(message, response.status, payload);
  }

  return {
    claimToken: payload.claim_token,
    expiresAt: payload.expires_at
  };
}

export async function copyTextToClipboard(text) {
  if (!text) {
    return false;
  }

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  return copied;
}

export function formatExpiry(expiresAt) {
  if (!expiresAt) {
    return "";
  }

  const date = new Date(expiresAt);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    day: "numeric"
  }).format(date);
}
