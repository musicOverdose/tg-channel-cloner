import { api } from "../api.js";
import { showToast } from "../components/Toast.js";
import { renderJobModal } from "../components/JobModal.js";

export async function renderDashboard(container) {
  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 300px;">
      <div style="color: var(--text-muted);">Loading dashboard data...</div>
    </div>
  `;

  let stats = null;
  let jobs = [];

  try {
    [stats, jobs] = await Promise.all([api.getStats(), api.getJobs()]);
  } catch (err) {
    container.innerHTML = `<div style="color: #f87171; padding: 20px;">Failed to load dashboard: ${err.message}</div>`;
    return;
  }

  const formatUpcomingDate = (dateStr, tz) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString([], {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (_) {
      return dateStr;
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || "IDLE").toUpperCase();
    if (s === "RUNNING") return `<span class="badge badge-running">● Running</span>`;
    if (s === "SCHEDULED") return `<span class="badge badge-scheduled">✓ Scheduled</span>`;
    if (s === "PAUSED") return `<span class="badge badge-paused">⏸ Paused</span>`;
    if (s === "ERROR" || s === "FAILED") return `<span class="badge badge-error">✕ Error</span>`;
    return `<span class="badge badge-idle">○ Idle</span>`;
  };

  container.innerHTML = `
    <div class="page-header">
      <div class="page-title">
        <h2>Cloning Dashboard</h2>
        <p>Monitor your active cloning jobs, channel synchronizations, and persistent schedules.</p>
      </div>
      <div>
        <button class="btn btn-primary" id="create-job-btn">
          <span>+</span> Create Copy Job
        </button>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Jobs</div>
        <div class="stat-value">${stats.total_jobs}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active Running</div>
        <div class="stat-value" style="color: #38bdf8;">${stats.running_jobs}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Scheduled</div>
        <div class="stat-value" style="color: #34d399;">${stats.scheduled_jobs}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Messages Copied</div>
        <div class="stat-value" style="color: #a78bfa;">${(stats.total_copied_messages || 0).toLocaleString()}</div>
      </div>
    </div>

    <!-- Upcoming Runs -->
    <div class="card">
      <div class="card-header">
        <h3>Upcoming Scheduled Runs</h3>
      </div>
      ${
        stats.upcoming_runs && stats.upcoming_runs.length > 0
          ? `
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Scheduled Time</th>
                <th>Job Name</th>
                <th>Channels</th>
                <th>Frequency</th>
                <th>Timezone</th>
              </tr>
            </thead>
            <tbody>
              ${stats.upcoming_runs
                .map(
                  (run) => `
                <tr>
                  <td><strong>${formatUpcomingDate(run.next_run_at, run.timezone)}</strong></td>
                  <td><a href="#/jobs/${run.job_id}" style="color: #60a5fa; text-decoration: none; font-weight: 500;">${run.job_name}</a></td>
                  <td style="color: var(--text-muted); font-size: 13px;">${run.source_title} ➔ ${run.destination_title}</td>
                  <td><span class="badge badge-scheduled">${run.frequency}</span></td>
                  <td style="color: var(--text-dim); font-size: 12px;">${run.timezone}</td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
          : `
        <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 14px;">
          No upcoming scheduled jobs. Enable scheduling when creating or editing a job!
        </div>
      `
      }
    </div>

    <!-- Active Jobs Table -->
    <div class="card">
      <div class="card-header">
        <h3>Channel Copy Jobs</h3>
      </div>
      ${
        jobs.length > 0
          ? `
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Job Name</th>
                <th>Bot</th>
                <th>Source ➔ Destination</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Next Run</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${jobs
                .map(
                  (job) => `
                <tr id="job-row-${job.id}">
                  <td>
                    <a href="#/jobs/${job.id}" style="color: #f8fafc; font-weight: 600; text-decoration: none;">
                      ${job.name}
                    </a>
                  </td>
                  <td style="font-size: 13px; color: var(--text-muted);">
                    @${job.bot_username || "Bot"}
                  </td>
                  <td style="font-size: 13px;">
                    <div style="font-weight: 500;">${job.source_title || job.source_chat_id}</div>
                    <div style="color: var(--text-dim); font-size: 12px;">➔ ${job.destination_title || job.destination_chat_id}</div>
                  </td>
                  <td>
                    <span style="font-size: 12px; text-transform: capitalize; color: #94a3b8;">
                      ${job.copy_mode}
                    </span>
                  </td>
                  <td class="status-cell">
                    ${getStatusBadge(job.status)}
                  </td>
                  <td style="font-size: 13px; color: var(--text-muted);">
                    ${
                      job.schedule_enabled && job.next_run_at
                        ? `${formatUpcomingDate(job.next_run_at, job.timezone)}<br/><span style="font-size: 11px; color: var(--text-dim);">${job.timezone}</span>`
                        : `<span style="color: var(--text-dim);">Manual only</span>`
                    }
                  </td>
                  <td style="text-align: right;">
                    <div style="display: flex; gap: 6px; justify-content: flex-end;">
                      <button class="btn btn-secondary btn-sm run-btn" data-id="${job.id}" title="Run Now">
                        ▶ Run
                      </button>
                      ${
                        job.schedule_enabled
                          ? `<button class="btn btn-secondary btn-sm pause-btn" data-id="${job.id}" title="Pause Schedule">⏸</button>`
                          : `<button class="btn btn-secondary btn-sm resume-btn" data-id="${job.id}" title="Resume Schedule">⏵</button>`
                      }
                      <button class="btn btn-secondary btn-sm edit-btn" data-id="${job.id}" title="Edit Job">
                        ✎
                      </button>
                    </div>
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
          : `
        <div style="padding: 48px 24px; text-align: center;">
          <div style="font-size: 36px; margin-bottom: 12px;">🚀</div>
          <h4 style="font-size: 18px; font-weight: 600;">Welcome to Telegram Channel Cloner</h4>
          <p style="color: var(--text-muted); font-size: 14px; max-width: 450px; margin: 8px auto 20px;">
            No copy jobs configured yet. Create your first job to clone or synchronize channels!
          </p>
          <button class="btn btn-primary" id="create-first-job-btn">+ Create First Copy Job</button>
        </div>
      `
      }
    </div>
  `;

  // Create job button handlers
  const openCreateModal = () => renderJobModal(null, () => renderDashboard(container));
  const createBtn = container.querySelector("#create-job-btn");
  if (createBtn) createBtn.onclick = openCreateModal;

  const firstJobBtn = container.querySelector("#create-first-job-btn");
  if (firstJobBtn) firstJobBtn.onclick = openCreateModal;

  // Row action handlers
  container.querySelectorAll(".run-btn").forEach((btn) => {
    btn.onclick = async () => {
      const id = parseInt(btn.dataset.id);
      btn.disabled = true;
      btn.textContent = "Starting...";
      try {
        await api.runJob(id);
        showToast("Job started! Check Job Detail for live progress.", "success");
        renderDashboard(container);
      } catch (err) {
        showToast(err.message, "error");
        btn.disabled = false;
        btn.textContent = "▶ Run";
      }
    };
  });

  container.querySelectorAll(".pause-btn").forEach((btn) => {
    btn.onclick = async () => {
      const id = parseInt(btn.dataset.id);
      try {
        await api.pauseSchedule(id);
        showToast("Schedule paused", "info");
        renderDashboard(container);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });

  container.querySelectorAll(".resume-btn").forEach((btn) => {
    btn.onclick = async () => {
      const id = parseInt(btn.dataset.id);
      try {
        await api.resumeSchedule(id);
        showToast("Schedule resumed", "success");
        renderDashboard(container);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });

  container.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.onclick = async () => {
      const id = parseInt(btn.dataset.id);
      try {
        const job = await api.getJob(id);
        renderJobModal(job, () => renderDashboard(container));
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });
}
