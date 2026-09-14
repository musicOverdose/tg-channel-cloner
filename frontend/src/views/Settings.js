import { api, auth } from "../api.js";
import { showToast } from "../components/Toast.js";

export async function renderSettings(container) {
  let sysInfo = null;
  try {
    sysInfo = await api.getSystemInfo();
  } catch (err) {
    sysInfo = { version: "1.0.0", status: "online", database_type: "SQLite", max_concurrent_jobs: 10, system_time_utc: new Date().toISOString() };
  }

  container.innerHTML = `
    <div class="page-header">
      <div class="page-title">
        <h2>System Settings & Maintenance</h2>
        <p>Application diagnostics, password management, and database backup exports.</p>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;">
      <!-- System Information -->
      <div class="card">
        <div class="card-header">
          <h3>Instance Diagnostics</h3>
        </div>
        <div style="padding: 24px; font-size: 14px; display: flex; flex-direction: column; gap: 14px;">
          <div><strong>Application Version:</strong> <code>v${sysInfo.version}</code></div>
          <div><strong>Database Engine:</strong> <span class="badge badge-completed">${sysInfo.database_type}</span></div>
          <div><strong>Max Concurrent Jobs:</strong> ${sysInfo.max_concurrent_jobs}</div>
          <div><strong>Active Cloner Tasks:</strong> ${sysInfo.active_workers}</div>
          <div><strong>System Time (UTC):</strong> <code>${new Date(sysInfo.system_time_utc).toUTCString()}</code></div>
          <div><strong>Deployment Target:</strong> Portainer / Docker Compose</div>
        </div>
      </div>

      <!-- Database Backup -->
      <div class="card">
        <div class="card-header">
          <h3>Database Backup & Portability</h3>
        </div>
        <div style="padding: 24px; font-size: 14px;">
          <p style="color: var(--text-muted); margin-bottom: 16px;">
            Export an authoritative point-in-time snapshot of the database including all jobs, bot credentials, schedules, and execution logs.
          </p>
          <a href="/api/system/backup" download class="btn btn-primary" id="backup-btn" style="text-decoration: none;">
            💾 Download Database Backup (.db)
          </a>
          <div class="form-help" style="margin-top: 12px;">
            The backup can be placed into <code>/data/cloner.db</code> on any new server or VPS to instantly restore your stack.
          </div>
        </div>
      </div>
    </div>

    <!-- Security & Password -->
    <div class="card" style="max-width: 600px;">
      <div class="card-header">
        <h3>Change Administrator Password</h3>
      </div>
      <div style="padding: 24px;">
        <form id="change-pwd-form">
          <div class="form-group">
            <label>Current Password</label>
            <input type="password" id="old-password" class="form-control" required />
          </div>
          <div class="form-group">
            <label>New Password (min 6 characters)</label>
            <input type="password" id="new-password" class="form-control" required />
          </div>
          <div class="form-group">
            <label>Confirm New Password</label>
            <input type="password" id="confirm-password" class="form-control" required />
          </div>
          <button type="submit" class="btn btn-primary" id="save-pwd-btn">Update Password</button>
        </form>
      </div>
    </div>
  `;

  // Change password handler
  const form = container.querySelector("#change-pwd-form");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const oldPwd = container.querySelector("#old-password").value;
    const newPwd = container.querySelector("#new-password").value;
    const confirmPwd = container.querySelector("#confirm-password").value;

    if (newPwd !== confirmPwd) {
      showToast("New passwords do not match", "error");
      return;
    }

    try {
      await api.changePassword(oldPwd, newPwd);
      showToast("Password updated successfully!", "success");
      form.reset();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}
