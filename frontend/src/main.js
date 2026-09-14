import "./style.css";
import { auth } from "./api.js";
import { renderLogin } from "./views/Login.js";
import { renderDashboard } from "./views/Dashboard.js";
import { renderJobDetail } from "./views/JobDetail.js";
import { renderBots } from "./views/Bots.js";
import { renderSettings } from "./views/Settings.js";
import { showToast } from "./components/Toast.js";

let ws = null;
let wsReconnectTimer = null;

function setupWebSocket() {
  if (!auth.isAuthenticated()) return;
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/api/ws?token=${auth.getToken()}`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleWsEvent(payload);
      } catch (_) {}
    };

    ws.onclose = () => {
      ws = null;
      // Reconnect after 3 seconds if still authenticated
      clearTimeout(wsReconnectTimer);
      if (auth.isAuthenticated()) {
        wsReconnectTimer = setTimeout(setupWebSocket, 3000);
      }
    };

    ws.onerror = () => {
      if (ws) ws.close();
    };
  } catch (_) {}
}

function handleWsEvent({ type, data }) {
  if (type === "JOB_PROGRESS") {
    // Update live metrics on Job Detail page if open
    const currentHash = window.location.hash;
    if (currentHash === `#/jobs/${data.job_id}`) {
      const metricCopied = document.getElementById("metric-copied");
      const metricSkipped = document.getElementById("metric-skipped");
      const metricErrors = document.getElementById("metric-errors");
      const metricSpeed = document.getElementById("metric-speed");
      const metricCurrentId = document.getElementById("metric-current-id");

      if (metricCopied) metricCopied.textContent = (data.copied || 0).toLocaleString();
      if (metricSkipped) metricSkipped.textContent = (data.skipped || 0).toLocaleString();
      if (metricErrors) metricErrors.textContent = (data.errors || 0).toLocaleString();
      if (metricSpeed) metricSpeed.textContent = `${data.speed || 0} msg/s`;
      if (metricCurrentId) metricCurrentId.textContent = `#${data.current_msg_id || 0}`;
    }
  } else if (type === "JOB_STARTED") {
    showToast(`Job #${data.job_id} started execution`, "info");
    updateRowStatus(data.job_id, "RUNNING");
  } else if (type === "JOB_FINISHED") {
    showToast(`Job #${data.job_id} finished (${data.status})`, data.status === "COMPLETED" ? "success" : "warning");
    updateRowStatus(data.job_id, data.job_status);
  }
}

function updateRowStatus(jobId, status) {
  const row = document.getElementById(`job-row-${jobId}`);
  if (row) {
    const statusCell = row.querySelector(".status-cell");
    if (statusCell) {
      const s = (status || "IDLE").toUpperCase();
      if (s === "RUNNING") statusCell.innerHTML = `<span class="badge badge-running">● Running</span>`;
      else if (s === "SCHEDULED") statusCell.innerHTML = `<span class="badge badge-scheduled">✓ Scheduled</span>`;
      else if (s === "PAUSED") statusCell.innerHTML = `<span class="badge badge-paused">⏸ Paused</span>`;
      else if (s === "ERROR" || s === "FAILED") statusCell.innerHTML = `<span class="badge badge-error">✕ Error</span>`;
      else statusCell.innerHTML = `<span class="badge badge-idle">○ Idle</span>`;
    }
  }
}

function renderAppShell() {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="app-container">
      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="logo-icon">⚡</div>
          <div class="logo-text">
            <h1>Telegram Cloner</h1>
            <span>Self-Hosted Stack</span>
          </div>
        </div>
        <nav class="nav-links">
          <a class="nav-item" href="#/" id="nav-dashboard">
            <span>📊</span> Dashboard
          </a>
          <a class="nav-item" href="#/bots" id="nav-bots">
            <span>🤖</span> Telegram Bots
          </a>
          <a class="nav-item" href="#/settings" id="nav-settings">
            <span>⚙</span> System Settings
          </a>
        </nav>
        <div class="sidebar-footer">
          <div>
            <span style="font-weight: 600; color: #f8fafc;" id="sidebar-user">${auth.getUser() || "admin"}</span>
          </div>
          <button class="btn btn-secondary btn-sm" id="logout-btn" title="Sign Out">Sign Out</button>
        </div>
      </aside>
      <main class="main-content" id="view-container"></main>
    </div>
  `;

  document.getElementById("logout-btn").onclick = () => {
    if (ws) ws.close();
    auth.logout();
    navigate();
  };
}

function updateNavActive(route) {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  if (route === "/" || route.startsWith("/jobs/")) {
    const el = document.getElementById("nav-dashboard");
    if (el) el.classList.add("active");
  } else if (route.startsWith("/bots")) {
    const el = document.getElementById("nav-bots");
    if (el) el.classList.add("active");
  } else if (route.startsWith("/settings")) {
    const el = document.getElementById("nav-settings");
    if (el) el.classList.add("active");
  }
}

function navigate() {
  const hash = window.location.hash || "#/";
  const route = hash.slice(1);
  const app = document.getElementById("app");

  if (route === "/login") {
    if (ws) ws.close();
    renderLogin(app, () => {
      window.location.hash = "#/";
    });
    return;
  }

  // Auth guard
  if (!auth.isAuthenticated()) {
    window.location.hash = "#/login";
    return;
  }

  // Ensure shell is rendered
  if (!document.querySelector(".app-container")) {
    renderAppShell();
  }

  setupWebSocket();
  updateNavActive(route);

  const container = document.getElementById("view-container");

  if (route === "/" || route === "") {
    renderDashboard(container);
  } else if (route.startsWith("/jobs/")) {
    const id = parseInt(route.split("/")[2]);
    renderJobDetail(container, id);
  } else if (route === "/bots") {
    renderBots(container);
  } else if (route === "/settings") {
    renderSettings(container);
  } else {
    window.location.hash = "#/";
  }
}

window.addEventListener("hashchange", navigate);
window.addEventListener("DOMContentLoaded", navigate);
