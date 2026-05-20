const app = document.querySelector("#app");
const config = window.PLANTLAB_ADMIN_CONFIG || {};
const API_BASE_URL = String(config.apiBaseUrl || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "plantlab_admin_token";
const EMAIL_KEY = "plantlab_admin_email";

let state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  email: localStorage.getItem(EMAIL_KEY) || "dev@plantlab.local",
  loading: false,
  error: "",
  profile: null,
  diagnostics: null,
};

init();

async function init() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("auth") === "complete") {
    window.history.replaceState({}, "", window.location.pathname);
    await refreshSession();
  } else if (!state.token) {
    await refreshSession({ silent: true });
  }
  if (state.token) {
    await loadDashboard();
  } else {
    renderLogin();
  }
}

function renderLogin() {
  app.innerHTML = `
    <section class="auth-panel">
      <p class="eyebrow">PLANTLAB ADMIN</p>
      <h1>System Diagnostics</h1>
      <p class="subtitle">This panel is for admin accounts only. Normal users should use the PlantLab web dashboard.</p>
      ${state.error ? `<p class="status status-error">${escapeHtml(state.error)}</p>` : ""}
      <form class="login-form" data-login-form>
        <label>Email
          <input name="email" type="email" autocomplete="email" value="${escapeHtml(state.email)}" required>
        </label>
        <label>Password
          <input name="password" type="password" autocomplete="current-password" placeholder="Local dev password">
        </label>
        <button class="primary-button" type="submit">${state.loading ? "Signing in..." : "Sign in"}</button>
      </form>
      <button class="secondary-button" data-google-login type="button">Sign in with Google</button>
      <p class="meta-text">API: ${escapeHtml(API_BASE_URL)}</p>
    </section>
  `;
  app.querySelector("[data-login-form]").addEventListener("submit", onLogin);
  app.querySelector("[data-google-login]").addEventListener("click", startGoogleLogin);
}

async function onLogin(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  state.loading = true;
  state.error = "";
  state.email = String(form.get("email") || "").trim();
  renderLogin();
  try {
    const payload = await apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: state.email,
        password: String(form.get("password") || "password"),
      }),
    });
    setToken(payload.token, payload.email || state.email);
    await loadDashboard();
  } catch (error) {
    state.error = error.message || "Could not sign in.";
    state.loading = false;
    renderLogin();
  }
}

function startGoogleLogin() {
  const returnTo = `${window.location.origin}${window.location.pathname}?auth=complete`;
  const params = new URLSearchParams({ client: "web", return_to: returnTo });
  window.location.href = `${API_BASE_URL}/api/auth/google/start?${params.toString()}`;
}

async function refreshSession(options = {}) {
  try {
    const payload = await apiRequest("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
      body: JSON.stringify({}),
    });
    setToken(payload.access_token, payload.user?.email || state.email);
  } catch (error) {
    if (!options.silent) {
      state.error = error.message || "Could not restore admin session.";
    }
  }
}

async function loadDashboard() {
  state.loading = true;
  state.error = "";
  renderLoading();
  try {
    const me = await apiRequest("/api/me", {}, state.token);
    if (!me.authenticated || !me.user?.is_admin) {
      clearToken();
      state.error = "This account is not allowed to use the admin diagnostics panel.";
      state.loading = false;
      renderLogin();
      return;
    }
    state.profile = me.user;
    state.diagnostics = await apiRequest("/api/admin/diagnostics", {}, state.token);
    state.loading = false;
    renderDashboard();
  } catch (error) {
    state.error = error.message || "Could not load admin diagnostics.";
    state.loading = false;
    renderLogin();
  }
}

function renderLoading() {
  app.innerHTML = `
    <section class="auth-panel">
      <p class="eyebrow">PLANTLAB ADMIN</p>
      <h1>Loading diagnostics</h1>
      <p class="subtitle">Checking account access and system health.</p>
    </section>
  `;
}

function renderDashboard() {
  const diagnostics = state.diagnostics;
  const summary = diagnostics.summary;
  app.innerHTML = `
    <aside class="admin-sidebar">
      <div>
        <p class="eyebrow">PLANTLAB ADMIN</p>
        <h1>Diagnostics</h1>
        <p class="meta-text">${escapeHtml(state.profile.email)}</p>
      </div>
      <button class="secondary-button" data-refresh type="button">Refresh</button>
      <button class="secondary-button" data-logout type="button">Log out</button>
    </aside>
    <section class="admin-main">
      <header class="admin-header">
        <div>
          <h2>System Health</h2>
          <p class="subtitle">Generated ${formatDate(diagnostics.generated_at)}</p>
        </div>
        <span class="chip">Admin only</span>
      </header>
      <section class="metric-grid">
        ${metric("Users", summary.users)}
        ${metric("Devices", summary.devices)}
        ${metric("Active", summary.active_devices)}
        ${metric("Nodes", summary.hardware_nodes)}
        ${metric("Stale nodes", summary.stale_nodes)}
        ${metric("Warnings", summary.recent_warning_events)}
      </section>
      <section class="panel">
        <div class="panel-header">
          <h3>Devices</h3>
          <p class="subtitle">Latest 100 devices across all users.</p>
        </div>
        ${renderDeviceTable(diagnostics.devices)}
      </section>
      <section class="panel-grid">
        <div class="panel">
          <div class="panel-header">
            <h3>Users</h3>
            <p class="subtitle">Latest 50 accounts.</p>
          </div>
          ${renderUserTable(diagnostics.users)}
        </div>
        <div class="panel">
          <div class="panel-header">
            <h3>Recent Events</h3>
            <p class="subtitle">Latest diagnostic events.</p>
          </div>
          ${renderEventList(diagnostics.recent_events)}
        </div>
      </section>
      <section class="panel">
        <div class="panel-header">
          <h3>Firmware Releases</h3>
          <p class="subtitle">Most recent firmware release records.</p>
        </div>
        ${renderFirmwareTable(diagnostics.firmware_releases)}
      </section>
    </section>
  `;
  app.querySelector("[data-refresh]").addEventListener("click", loadDashboard);
  app.querySelector("[data-logout]").addEventListener("click", logout);
}

function renderDeviceTable(devices) {
  if (!devices.length) {
    return `<p class="empty-text">No devices found.</p>`;
  }
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Device</th>
            <th>Owner</th>
            <th>Status</th>
            <th>Nodes</th>
            <th>Latest data</th>
            <th>Attention</th>
          </tr>
        </thead>
        <tbody>
          ${devices
            .map(
              (device) => `
                <tr>
                  <td><strong>${escapeHtml(device.name)}</strong><span>${escapeHtml(device.location || "No location")}</span></td>
                  <td>${escapeHtml(device.owner_email)}</td>
                  <td><span class="status-pill status-${escapeHtml(device.status)}">${escapeHtml(device.status)}</span></td>
                  <td>${device.nodes.map((node) => `${escapeHtml(node.node_role || "node")} ${escapeHtml(node.software_version || "")}`).join("<br>") || "None"}</td>
                  <td>Reading ${formatDate(device.latest_reading_at)}<br>Image ${formatDate(device.latest_image_at)}</td>
                  <td>${escapeHtml(device.last_error_code || "None")}<span>${escapeHtml(device.last_error_message || "")}</span></td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderUserTable(users) {
  if (!users.length) {
    return `<p class="empty-text">No users found.</p>`;
  }
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>User</th><th>Devices</th><th>Last Seen</th></tr></thead>
        <tbody>
          ${users
            .map(
              (user) => `
                <tr>
                  <td><strong>${escapeHtml(user.email)}</strong><span>${escapeHtml(user.name || "")}</span></td>
                  <td>${user.active_device_count}/${user.device_count}</td>
                  <td>${formatDate(user.last_seen_at)}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderEventList(events) {
  if (!events.length) {
    return `<p class="empty-text">No diagnostic events reported.</p>`;
  }
  return `
    <div class="event-list">
      ${events
        .map(
          (event) => `
            <article class="event-row">
              <div>
                <strong>${escapeHtml(event.code || event.event_type)}</strong>
                <span>${escapeHtml(event.device_name)} · ${escapeHtml(event.owner_email)}</span>
              </div>
              <div>
                <span class="status-pill status-${escapeHtml(event.severity)}">${escapeHtml(event.severity)}</span>
                <span>${formatDate(event.occurred_at)}</span>
              </div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderFirmwareTable(releases) {
  if (!releases.length) {
    return `<p class="empty-text">No firmware releases found.</p>`;
  }
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Release</th><th>Role</th><th>Model</th><th>Version</th><th>Status</th><th>Published</th></tr></thead>
        <tbody>
          ${releases
            .map(
              (release) => `
                <tr>
                  <td>${escapeHtml(release.release_id)}</td>
                  <td>${escapeHtml(release.node_role)}</td>
                  <td>${escapeHtml(release.hardware_model || "Any")}</td>
                  <td>${escapeHtml(release.version)}</td>
                  <td>${escapeHtml(release.status)}</td>
                  <td>${formatDate(release.published_at)}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function metric(label, value) {
  return `<article class="metric-card"><span>${escapeHtml(label)}</span><strong>${Number(value || 0)}</strong></article>`;
}

async function apiRequest(path, options = {}, token = undefined) {
  const headers = new Headers(options.headers || {});
  headers.set("accept", "application/json");
  if (options.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(payload?.error?.message || payload?.detail || `API request failed: ${response.status}`);
  }
  return payload;
}

function setToken(token, email) {
  state.token = token;
  state.email = email;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EMAIL_KEY, email);
}

async function logout() {
  try {
    await apiRequest("/api/auth/logout", {
      method: "POST",
      credentials: "include",
      body: JSON.stringify({}),
    });
  } catch {
    // Local dev token logout is client-side only.
  }
  clearToken();
  state.profile = null;
  state.diagnostics = null;
  renderLogin();
}

function clearToken() {
  state.token = "";
  localStorage.removeItem(TOKEN_KEY);
}

function formatDate(value) {
  if (!value) {
    return "Not reported";
  }
  return new Date(value).toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
