import { api } from "../api.js";
import { showToast } from "../components/Toast.js";
import { renderBotModal } from "../components/BotModal.js";

export async function renderBots(container) {
  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 300px;">
      <div style="color: var(--text-muted);">Loading bots...</div>
    </div>
  `;

  let bots = [];
  try {
    bots = await api.getBots();
  } catch (err) {
    container.innerHTML = `<div style="color: #f87171; padding: 20px;">Failed to load bots: ${err.message}</div>`;
    return;
  }

  container.innerHTML = `
    <div class="page-header">
      <div class="page-title">
        <h2>Telegram Bots</h2>
        <p>Manage bot credentials used for channel cloning operations. Tokens are encrypted at rest.</p>
      </div>
      <div>
        <button class="btn btn-primary" id="add-bot-btn">
          <span>+</span> Connect Telegram Bot
        </button>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>Configured Bots (${bots.length})</h3>
      </div>
      ${
        bots.length > 0
          ? `
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Bot Name</th>
                <th>Username</th>
                <th>Telegram ID</th>
                <th>Token (Masked)</th>
                <th>Status</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${bots
                .map(
                  (b) => `
                <tr>
                  <td><strong>${b.name}</strong></td>
                  <td><a href="https://t.me/${b.bot_username}" target="_blank" style="color: #60a5fa; text-decoration: none;">@${b.bot_username || "Unknown"}</a></td>
                  <td style="color: var(--text-dim); font-size: 13px;">${b.telegram_id || "—"}</td>
                  <td><code>${b.masked_token}</code></td>
                  <td>
                    <span class="badge ${b.is_active ? "badge-completed" : "badge-idle"}">
                      ${b.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td style="text-align: right;">
                    <div style="display: flex; gap: 8px; justify-content: flex-end;">
                      <button class="btn btn-secondary btn-sm test-bot-btn" data-id="${b.id}" title="Test Bot Connection">
                        ⚡ Test
                      </button>
                      <button class="btn btn-danger btn-sm delete-bot-btn" data-id="${b.id}" title="Delete Bot">
                        🗑 Delete
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
          <div style="font-size: 36px; margin-bottom: 12px;">🤖</div>
          <h4 style="font-size: 18px; font-weight: 600;">No Telegram Bots Configured</h4>
          <p style="color: var(--text-muted); font-size: 14px; max-width: 450px; margin: 8px auto 20px;">
            Connect a Telegram Bot token to start cloning channels. Bots can be generated via @BotFather on Telegram.
          </p>
          <button class="btn btn-primary" id="add-first-bot-btn">+ Connect First Bot</button>
        </div>
      `
      }
    </div>
  `;

  const openAddModal = () => renderBotModal(() => renderBots(container));

  const addBtn = container.querySelector("#add-bot-btn");
  if (addBtn) addBtn.onclick = openAddModal;

  const firstBtn = container.querySelector("#add-first-bot-btn");
  if (firstBtn) firstBtn.onclick = openAddModal;

  container.querySelectorAll(".test-bot-btn").forEach((btn) => {
    btn.onclick = async () => {
      const id = parseInt(btn.dataset.id);
      btn.disabled = true;
      btn.textContent = "Testing...";
      try {
        const res = await api.testBot(id);
        if (res.success) {
          showToast(`Connection OK! Bot @${res.bot_username} (${res.first_name}) is online.`, "success");
        } else {
          showToast(`Test failed: ${res.error}`, "error");
        }
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        btn.disabled = false;
        btn.textContent = "⚡ Test";
      }
    };
  });

  container.querySelectorAll(".delete-bot-btn").forEach((btn) => {
    btn.onclick = async () => {
      const id = parseInt(btn.dataset.id);
      if (!confirm("Are you sure you want to delete this bot?")) return;
      try {
        await api.deleteBot(id);
        showToast("Bot removed", "success");
        renderBots(container);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });
}
