import { api } from "../api.js";
import { showToast } from "../components/Toast.js";
import { renderJobModal } from "../components/JobModal.js";

export async function renderJobDetail(container, jobId) {
  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 300px;">
      <div style="color: var(--text-muted);">Loading job #${jobId} details...</div>
    </div>
  `;

  let job = null;
  try {
    job = await api.getJob(jobId);
  } catch (err) {
    container.innerHTML = `
      <div style="padding: 20px;">
        <a href="#/" style="color: #60a5fa; text-decoration: none;">← Back to Dashboard</a>
        <div style="color: #f87171; margin-top: 16px;">Failed to load job: ${err.message}</div>
      </div>
    `;
    return;
  }

  const latestExec = job.executions && job.executions.length > 0 ? job.executions[0] : null;
  const isRunning = job.status === "RUNNING";

  const getStatusBadge = (status) => {
    const s = (status || "IDLE").toUpperCase();
    if (s === "RUNNING") return `<span class="badge badge-running">● Running</span>`;
    if (s === "SCHEDULED") return `<span class="badge badge-scheduled">✓ Scheduled</span>`;
    if (s === "PAUSED") return `<span class="badge badge-paused">⏸ Paused</span>`;
    if (s === "ERROR" || s === "FAILED") return `<span class="badge badge-error">✕ Error</span>`;
    return `<span class="badge badge-idle">○ Idle</span>`;
  };

  container.innerHTML = `
    <div style="margin-bottom: 20px;">
      <a href="#/" style="color: #60a5fa; text-decoration: none; font-size: 14px;">← Back to Dashboard</a>
    </div>

    <!-- Header -->
    <div class="page-header" style="align-items: center;">
      <div class="page-title">
        <div style="display: flex; align-items: center; gap: 12px;">
          <h2>${job.name}</h2>
          <span id="header-status-badge">${getStatusBadge(job.status)}</span>
        </div>
        <p style="margin-top: 4px;">
          Bot: <strong>@${job.bot ? job.bot.bot_username : job.bot_username || "Bot"}</strong> &bull;
          Source: <code>${job.source_title || job.source_chat_id}</code> ➔
          Destination: <code>${job.destination_title || job.destination_chat_id}</code>
        </p>
      </div>
      <div style="display: flex; gap: 8px;">
        ${
          isRunning
            ? `<button class="btn btn-danger" id="detail-stop-btn">■ Stop Execution</button>`
            : `<button class="btn btn-primary" id="detail-run-btn">▶ Run Now</button>`
        }
        ${
          job.schedule_enabled
            ? `<button class="btn btn-secondary" id="detail-pause-btn">⏸ Pause Schedule</button>`
            : `<button class="btn btn-secondary" id="detail-resume-btn">⏵ Resume Schedule</button>`
        }
        <button class="btn btn-secondary" id="detail-edit-btn">✎ Edit</button>
        <button class="btn btn-danger" id="detail-delete-btn">🗑 Delete</button>
      </div>
    </div>

    <!-- Live Execution Metrics -->
    <div class="card" style="border-color: ${isRunning ? "rgba(56, 189, 248, 0.4)" : "var(--border-color)"};">
      <div class="card-header">
        <h3>Current / Latest Execution</h3>
        <span style="font-size: 13px; color: var(--text-dim);" id="exec-trigger-text">
          ${latestExec ? `Triggered: ${latestExec.trigger} &bull; Execution #${latestExec.execution_number}` : "No executions recorded yet"}
        </span>
      </div>
      <div style="padding: 24px;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 20px;">
          <div>
            <div class="stat-label">Copied</div>
            <div class="stat-value" id="metric-copied" style="color: #34d399;">
              ${latestExec ? latestExec.copied_count.toLocaleString() : "0"}
            </div>
          </div>
          <div>
            <div class="stat-label">Skipped (Gaps / Deleted)</div>
            <div class="stat-value" id="metric-skipped" style="color: #94a3b8;">
              ${latestExec ? latestExec.skipped_count.toLocaleString() : "0"}
            </div>
          </div>
          <div>
            <div class="stat-label">Errors</div>
            <div class="stat-value" id="metric-errors" style="color: #f87171;">
              ${latestExec ? latestExec.error_count.toLocaleString() : "0"}
            </div>
          </div>
          <div>
            <div class="stat-label">Speed</div>
            <div class="stat-value" id="metric-speed" style="color: #38bdf8;">
              ${latestExec ? `${latestExec.speed} msg/s` : "0 msg/s"}
            </div>
          </div>
          <div>
            <div class="stat-label">Current Message ID</div>
            <div class="stat-value" id="metric-current-id">
              ${latestExec && latestExec.current_msg_id ? `#${latestExec.current_msg_id}` : `#${job.last_copied_message_id || 0}`}
            </div>
          </div>
        </div>

        <div class="progress-bar-container">
          <div class="progress-bar-fill" id="exec-progress-bar" style="width: ${isRunning ? "75%" : "100%"}; background: ${isRunning ? "linear-gradient(90deg, #3b82f6, #38bdf8)" : "#10b981"};"></div>
        </div>
      </div>
    </div>

    <!-- Configuration & Schedule Cards -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;">
      <!-- Config -->
      <div class="card">
        <div class="card-header">
          <h3>Job Configuration</h3>
        </div>
        <div style="padding: 20px; font-size: 14px; display: flex; flex-direction: column; gap: 12px;">
          <div><strong>Copy Mode:</strong> <span style="text-transform: capitalize;">${job.copy_mode}</span></div>
          <div><strong>Start Message ID:</strong> ${job.start_message_id}</div>
          <div><strong>Last Copied Message ID:</strong> #${job.last_copied_message_id || 0}</div>
          <div><strong>Batch Size:</strong> ${job.batch_size} messages</div>
          <div><strong>Overlap Policy:</strong> ${job.if_running === "skip" ? "Skip next run if previous is active" : "Allow concurrent runs"}</div>
          <div><strong>Missed Run Policy:</strong> ${job.if_missed === "run_once" ? "Run once immediately" : "Skip"}</div>
        </div>
      </div>

      <!-- Schedule -->
      <div class="card">
        <div class="card-header">
          <h3>Schedule Details</h3>
        </div>
        <div style="padding: 20px; font-size: 14px; display: flex; flex-direction: column; gap: 12px;">
          <div><strong>Status:</strong> ${job.schedule_enabled ? `<span style="color: #34d399;">Enabled</span>` : `<span style="color: #94a3b8;">Disabled / Paused</span>`}</div>
          <div><strong>Frequency:</strong> <span style="text-transform: capitalize;">${job.frequency}</span> (${job.schedule_time || "01:00"})</div>
          <div><strong>Timezone:</strong> <code>${job.timezone}</code></div>
          <div><strong>Next Run:</strong> ${job.next_run_at ? new Date(job.next_run_at).toLocaleString() : "None"}</div>
          <div><strong>Last Run:</strong> ${job.last_run_at ? new Date(job.last_run_at).toLocaleString() : "Never"}</div>
        </div>
      </div>
    </div>

    <!-- Live Logs Viewer -->
    <div class="card">
      <div class="card-header">
        <h3>Live Execution Logs</h3>
        <div style="display: flex; gap: 8px;">
          <select id="log-level-filter" class="form-control" style="width: auto; padding: 4px 10px; font-size: 12px;">
            <option value="">All Levels</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
          </select>
          <button class="btn btn-secondary btn-sm" id="refresh-logs-btn">↻ Refresh</button>
        </div>
      </div>
      <div style="padding: 20px;">
        <div class="log-terminal" id="log-terminal-container">
          <div style="color: var(--text-dim); text-align: center; padding: 20px;">Loading logs...</div>
        </div>
      </div>
    </div>

    <!-- Execution History -->
    <div class="card">
      <div class="card-header">
        <h3>Execution History</h3>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Trigger</th>
              <th>Started</th>
              <th>Finished</th>
              <th>Copied</th>
              <th>Skipped</th>
              <th>Errors</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="history-table-body">
            ${
              job.executions && job.executions.length > 0
                ? job.executions
                    .map(
                      (e) => `
                  <tr>
                    <td><strong>#${e.execution_number}</strong></td>
                    <td>${e.trigger}</td>
                    <td style="font-size: 13px;">${new Date(e.started_at).toLocaleString()}</td>
                    <td style="font-size: 13px;">${e.finished_at ? new Date(e.finished_at).toLocaleString() : "Running..."}</td>
                    <td style="color: #34d399; font-weight: 600;">${e.copied_count.toLocaleString()}</td>
                    <td style="color: #94a3b8;">${e.skipped_count.toLocaleString()}</td>
                    <td style="color: ${e.error_count > 0 ? "#f87171" : "#94a3b8"};">${e.error_count}</td>
                    <td>${getStatusBadge(e.status)}</td>
                  </tr>
                `
                    )
                    .join("")
                : `<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 24px;">No execution history yet</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
  `;

  // Action buttons
  const runBtn = container.querySelector("#detail-run-btn");
  if (runBtn) {
    runBtn.onclick = async () => {
      runBtn.disabled = true;
      try {
        await api.runJob(job.id);
        showToast("Job started!", "success");
        renderJobDetail(container, job.id);
      } catch (err) {
        showToast(err.message, "error");
        runBtn.disabled = false;
      }
    };
  }

  const stopBtn = container.querySelector("#detail-stop-btn");
  if (stopBtn) {
    stopBtn.onclick = async () => {
      stopBtn.disabled = true;
      try {
        await api.stopJob(job.id);
        showToast("Stop signal sent to worker", "warning");
        setTimeout(() => renderJobDetail(container, job.id), 1500);
      } catch (err) {
        showToast(err.message, "error");
        stopBtn.disabled = false;
      }
    };
  }

  const pauseBtn = container.querySelector("#detail-pause-btn");
  if (pauseBtn) {
    pauseBtn.onclick = async () => {
      try {
        await api.pauseSchedule(job.id);
        showToast("Schedule paused", "info");
        renderJobDetail(container, job.id);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  }

  const resumeBtn = container.querySelector("#detail-resume-btn");
  if (resumeBtn) {
    resumeBtn.onclick = async () => {
      try {
        await api.resumeSchedule(job.id);
        showToast("Schedule resumed", "success");
        renderJobDetail(container, job.id);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  }

  const editBtn = container.querySelector("#detail-edit-btn");
  if (editBtn) {
    editBtn.onclick = () => renderJobModal(job, () => renderJobDetail(container, job.id));
  }

  const deleteBtn = container.querySelector("#detail-delete-btn");
  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      if (!confirm(`Are you sure you want to permanently delete job '${job.name}'?`)) return;
      try {
        await api.deleteJob(job.id);
        showToast("Job deleted", "success");
        window.location.hash = "#/";
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  }

  // Load and render logs
  const terminal = container.querySelector("#log-terminal-container");
  const levelFilter = container.querySelector("#log-level-filter");
  const refreshLogsBtn = container.querySelector("#refresh-logs-btn");

  const loadLogs = async () => {
    if (!latestExec) {
      terminal.innerHTML = `<div style="color: var(--text-dim); text-align: center; padding: 20px;">No execution logs yet.</div>`;
      return;
    }
    try {
      const logs = await api.getExecutionLogs(latestExec.id, levelFilter.value);
      if (logs.length === 0) {
        terminal.innerHTML = `<div style="color: var(--text-dim); text-align: center; padding: 20px;">No logs recorded for execution #${latestExec.execution_number}.</div>`;
        return;
      }
      terminal.innerHTML = logs
        .map(
          (l) => `
        <div class="log-line">
          <span class="log-time">${new Date(l.timestamp).toLocaleTimeString()}</span>
          <span class="log-level-${l.level}">[${l.level}]</span>
          <span>${l.message}</span>
        </div>
      `
        )
        .join("");
      terminal.scrollTop = terminal.scrollHeight;
    } catch (err) {
      terminal.innerHTML = `<div style="color: #f87171; padding: 10px;">Failed to load logs: ${err.message}</div>`;
    }
  };

  levelFilter.onchange = loadLogs;
  refreshLogsBtn.onclick = loadLogs;
  loadLogs();
}
