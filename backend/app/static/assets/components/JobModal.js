import { api } from "../api.js";
import { showToast } from "./Toast.js";
import { renderBotModal } from "./BotModal.js";

const COMMON_TIMEZONES = [
  "UTC",
  "Asia/Tehran",
  "Europe/Berlin",
  "Europe/London",
  "Europe/Paris",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Asia/Dubai",
  "Asia/Istanbul",
  "Asia/Singapore",
  "Asia/Tokyo",
];

export async function renderJobModal(jobToEdit = null, onSuccess) {
  let bots = [];
  try {
    bots = await api.getBots();
  } catch (e) {
    showToast("Failed to load bots: " + e.message, "error");
  }

  const modal = document.createElement("div");
  modal.className = "modal-overlay";

  const isEdit = !!jobToEdit;
  const initialCopyMode = jobToEdit ? jobToEdit.copy_mode : "incremental";
  const initialFrequency = jobToEdit ? jobToEdit.frequency : "daily";
  const initialTz = jobToEdit ? jobToEdit.timezone : "UTC";
  const initialScheduleEnabled = jobToEdit ? jobToEdit.schedule_enabled : false;

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 680px;">
      <div class="modal-header">
        <h3>${isEdit ? "Edit Copy Job" : "Create New Copy Job"}</h3>
        <button class="btn btn-secondary btn-sm" id="close-job-modal">✕</button>
      </div>
      <div class="modal-body">
        <!-- Basic Info -->
        <div class="form-group">
          <label>Job Name</label>
          <input type="text" id="job-name" class="form-control" placeholder="e.g. Daily Tech News Sync" value="${jobToEdit ? jobToEdit.name : ""}" />
        </div>

        <div class="form-group">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <label style="margin-bottom: 0;">Telegram Bot</label>
            <button class="btn btn-secondary btn-sm" id="quick-add-bot-btn" type="button">+ New Bot</button>
          </div>
          <select id="job-bot-id" class="form-control">
            ${bots.length === 0 ? `<option value="">No bots registered yet. Add one!</option>` : ""}
            ${bots
              .map(
                (b) =>
                  `<option value="${b.id}" ${jobToEdit && jobToEdit.bot_id === b.id ? "selected" : ""}>
                    ${b.name} (@${b.bot_username || "unknown"})
                  </option>`
              )
              .join("")}
          </select>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Source Channel ID</label>
            <input type="text" id="job-source" class="form-control" placeholder="-1001234567890" value="${jobToEdit ? jobToEdit.source_chat_id : ""}" />
            <div class="form-help">Bot must be a member or admin.</div>
          </div>
          <div class="form-group">
            <label>Destination Channel ID</label>
            <input type="text" id="job-dest" class="form-control" placeholder="-1009876543210" value="${jobToEdit ? jobToEdit.destination_chat_id : ""}" />
            <div class="form-help">Bot MUST be Admin with 'Post Messages'.</div>
          </div>
        </div>

        <div style="margin-bottom: 18px;">
          <button class="btn btn-secondary btn-sm" type="button" id="probe-channels-btn">
            🔍 Validate Bot Permissions & Probe Channels
          </button>
          <div id="probe-results" style="display: none; margin-top: 10px; font-size: 13px; padding: 10px; border-radius: 6px;"></div>
        </div>

        <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 20px 0;" />

        <!-- Copy Mode -->
        <div class="form-group">
          <label>Copy Mode</label>
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">
            <label style="display: flex; align-items: center; gap: 8px; font-weight: normal; cursor: pointer;">
              <input type="radio" name="copy-mode" value="incremental" ${initialCopyMode === "incremental" ? "checked" : ""} />
              <div>
                <strong>Incremental (Recommended)</strong>
                <div class="form-help" style="margin: 0;">Copies only new messages since the last successful execution.</div>
              </div>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-weight: normal; cursor: pointer;">
              <input type="radio" name="copy-mode" value="full" ${initialCopyMode === "full" ? "checked" : ""} />
              <div>
                <strong>Full History</strong>
                <div class="form-help" style="margin: 0;">Copies all messages starting from message #1 on every run.</div>
              </div>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-weight: normal; cursor: pointer;">
              <input type="radio" name="copy-mode" value="range" ${initialCopyMode === "range" ? "checked" : ""} />
              <div>
                <strong>Specific Message Range</strong>
                <div class="form-help" style="margin: 0;">Only process messages between custom Start and End IDs.</div>
              </div>
            </label>
          </div>
        </div>

        <div id="range-inputs" class="form-row" style="display: ${initialCopyMode === "range" ? "grid" : "none"}; margin-bottom: 18px;">
          <div class="form-group">
            <label>Start Message ID</label>
            <input type="number" id="start-msg-id" class="form-control" value="${jobToEdit ? jobToEdit.start_message_id : 1}" />
          </div>
          <div class="form-group">
            <label>End Message ID</label>
            <input type="number" id="end-msg-id" class="form-control" placeholder="Leave empty for auto-scan" value="${jobToEdit && jobToEdit.end_message_id ? jobToEdit.end_message_id : ""}" />
          </div>
        </div>

        <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 20px 0;" />

        <!-- Schedule Settings -->
        <div class="form-group">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
            <input type="checkbox" id="schedule-enabled" ${initialScheduleEnabled ? "checked" : ""} />
            <span style="font-size: 15px; font-weight: 600; color: var(--text-main);">Enable Automatic Scheduling</span>
          </label>
        </div>

        <div id="schedule-fields" style="display: ${initialScheduleEnabled ? "block" : "none"};">
          <div class="form-row">
            <div class="form-group">
              <label>Frequency</label>
              <select id="schedule-freq" class="form-control">
                <option value="daily" ${initialFrequency === "daily" ? "selected" : ""}>Every day</option>
                <option value="weekly" ${initialFrequency === "weekly" ? "selected" : ""}>Every week</option>
                <option value="once" ${initialFrequency === "once" ? "selected" : ""}>Once</option>
                <option value="custom" ${initialFrequency === "custom" ? "selected" : ""}>Custom (Cron expression)</option>
              </select>
            </div>
            <div class="form-group" id="time-group">
              <label>Time of Day</label>
              <input type="time" id="schedule-time" class="form-control" value="${jobToEdit ? jobToEdit.schedule_time : "01:00"}" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Timezone</label>
              <select id="schedule-tz" class="form-control">
                ${COMMON_TIMEZONES.map(
                  (tz) =>
                    `<option value="${tz}" ${initialTz === tz ? "selected" : ""}>${tz}</option>`
                ).join("")}
              </select>
            </div>
            <div class="form-group" id="date-group" style="display: ${initialFrequency === "once" ? "block" : "none"};">
              <label>Execution Date</label>
              <input type="date" id="schedule-date" class="form-control" value="${jobToEdit ? jobToEdit.schedule_date || "" : ""}" />
            </div>
          </div>

          <div class="form-group" id="cron-group" style="display: ${initialFrequency === "custom" ? "block" : "none"};">
            <label>Cron Expression</label>
            <input type="text" id="schedule-cron" class="form-control" placeholder="0 1 * * *" value="${jobToEdit ? jobToEdit.cron_expression || "" : ""}" />
            <div class="form-help">Format: minute hour day-of-month month day-of-week (evaluated in the selected timezone).</div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>If previous execution is still running:</label>
              <select id="if-running" class="form-control">
                <option value="skip" ${jobToEdit && jobToEdit.if_running === "skip" ? "selected" : ""}>Do not start another execution (Skip)</option>
                <option value="allow" ${jobToEdit && jobToEdit.if_running === "allow" ? "selected" : ""}>Allow concurrent execution</option>
              </select>
            </div>
            <div class="form-group">
              <label>If a scheduled run was missed (server offline):</label>
              <select id="if-missed" class="form-control">
                <option value="run_once" ${jobToEdit && jobToEdit.if_missed === "run_once" ? "selected" : ""}>Run once immediately upon return</option>
                <option value="skip" ${jobToEdit && jobToEdit.if_missed === "skip" ? "selected" : ""}>Skip missed execution</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" id="cancel-job-btn">Cancel</button>
        <button class="btn btn-primary" id="save-job-btn">${isEdit ? "Update Job" : "Create Job"}</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const close = () => modal.remove();
  modal.querySelector("#close-job-modal").onclick = close;
  modal.querySelector("#cancel-job-btn").onclick = close;

  // Toggle copy mode range inputs
  modal.querySelectorAll("input[name='copy-mode']").forEach((radio) => {
    radio.onchange = () => {
      const mode = modal.querySelector("input[name='copy-mode']:checked").value;
      modal.querySelector("#range-inputs").style.display = mode === "range" ? "grid" : "none";
    };
  });

  // Toggle schedule visibility
  const schedCheckbox = modal.querySelector("#schedule-enabled");
  schedCheckbox.onchange = () => {
    modal.querySelector("#schedule-fields").style.display = schedCheckbox.checked ? "block" : "none";
  };

  // Toggle frequency inputs
  const freqSelect = modal.querySelector("#schedule-freq");
  freqSelect.onchange = () => {
    const freq = freqSelect.value;
    modal.querySelector("#date-group").style.display = freq === "once" ? "block" : "none";
    modal.querySelector("#cron-group").style.display = freq === "custom" ? "block" : "none";
  };

  // Quick add bot button
  modal.querySelector("#quick-add-bot-btn").onclick = () => {
    renderBotModal((newBot) => {
      const botSelect = modal.querySelector("#job-bot-id");
      const opt = document.createElement("option");
      opt.value = newBot.id;
      opt.textContent = `${newBot.name} (@${newBot.bot_username || "unknown"})`;
      opt.selected = true;
      botSelect.appendChild(opt);
    });
  };

  // Probe channels button
  modal.querySelector("#probe-channels-btn").onclick = async () => {
    const botId = parseInt(modal.querySelector("#job-bot-id").value);
    const sourceChat = modal.querySelector("#job-source").value.trim();
    const destChat = modal.querySelector("#job-dest").value.trim();
    const probeBox = modal.querySelector("#probe-results");

    if (!botId) {
      showToast("Please select a bot first", "error");
      return;
    }
    if (!sourceChat || !destChat) {
      showToast("Please enter both Source and Destination Channel IDs", "error");
      return;
    }

    probeBox.style.display = "block";
    probeBox.style.background = "var(--bg-card-sub)";
    probeBox.style.color = "var(--text-main)";
    probeBox.innerHTML = `<em>Testing connection to Telegram and probing channels...</em>`;

    try {
      const [srcRes, dstRes] = await Promise.all([
        api.probeChannel(botId, sourceChat),
        api.probeChannel(botId, destChat),
      ]);

      let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;

      // Source result
      if (srcRes.success) {
        html += `<div style="color: #34d399;">✓ Source Channel: <strong>${srcRes.title || sourceChat}</strong> (${srcRes.type || "channel"})</div>`;
      } else {
        html += `<div style="color: #f87171;">✕ Source Channel: ${srcRes.error}</div>`;
      }

      // Destination result
      if (dstRes.success) {
        if (dstRes.can_post_messages) {
          html += `<div style="color: #34d399;">✓ Destination Channel: <strong>${dstRes.title || destChat}</strong> (Bot has admin permission to post messages)</div>`;
        } else {
          html += `<div style="color: #fbbf24;">⚠ Destination Channel: <strong>${dstRes.title || destChat}</strong> (Bot found, but lacks 'can_post_messages' admin permission!)</div>`;
        }
      } else {
        html += `<div style="color: #f87171;">✕ Destination Channel: ${dstRes.error}</div>`;
      }

      html += `</div>`;
      probeBox.innerHTML = html;
    } catch (err) {
      probeBox.innerHTML = `<span style="color: #f87171;">Probe failed: ${err.message}</span>`;
    }
  };

  // Save / Update
  modal.querySelector("#save-job-btn").onclick = async () => {
    const name = modal.querySelector("#job-name").value.trim();
    const botId = parseInt(modal.querySelector("#job-bot-id").value);
    const sourceChat = modal.querySelector("#job-source").value.trim();
    const destChat = modal.querySelector("#job-dest").value.trim();
    const copyMode = modal.querySelector("input[name='copy-mode']:checked").value;
    const scheduleEnabled = modal.querySelector("#schedule-enabled").checked;
    const frequency = modal.querySelector("#schedule-freq").value;
    const scheduleTime = modal.querySelector("#schedule-time").value;
    const timezone = modal.querySelector("#schedule-tz").value;
    const scheduleDate = modal.querySelector("#schedule-date").value;
    const cronExpr = modal.querySelector("#schedule-cron").value.trim();
    const ifRunning = modal.querySelector("#if-running").value;
    const ifMissed = modal.querySelector("#if-missed").value;

    const startMsgId = parseInt(modal.querySelector("#start-msg-id").value) || 1;
    const endMsgVal = modal.querySelector("#end-msg-id").value.trim();
    const endMsgId = endMsgVal ? parseInt(endMsgVal) : null;

    if (!name || !botId || !sourceChat || !destChat) {
      showToast("Please fill in Job Name, Bot, and both Channel IDs", "error");
      return;
    }

    const payload = {
      name,
      bot_id: botId,
      source_chat_id: sourceChat,
      destination_chat_id: destChat,
      copy_mode: copyMode,
      start_message_id: startMsgId,
      end_message_id: endMsgId,
      schedule_enabled: scheduleEnabled,
      frequency,
      schedule_time: scheduleTime,
      timezone,
      schedule_date: scheduleDate || null,
      cron_expression: cronExpr || null,
      if_running: ifRunning,
      if_missed: ifMissed,
    };

    try {
      if (isEdit) {
        await api.updateJob(jobToEdit.id, payload);
        showToast(`Job '${name}' updated successfully`, "success");
      } else {
        await api.createJob(payload);
        showToast(`Job '${name}' created successfully`, "success");
      }
      close();
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}
