import { api } from "../api.js";
import { showToast } from "./Toast.js";

export function renderBotModal(onSuccess) {
  const modal = document.createElement("div");
  modal.className = "modal-overlay";
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>Connect Telegram Bot</h3>
        <button class="btn btn-secondary btn-sm" id="close-bot-modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Bot Display Name</label>
          <input type="text" id="bot-name" class="form-control" placeholder="e.g. My Sync Bot" />
        </div>
        <div class="form-group">
          <label>Bot API Token</label>
          <input type="password" id="bot-token" class="form-control" placeholder="123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ" />
          <div class="form-help">Obtain this token from @BotFather on Telegram. It will be encrypted at rest.</div>
        </div>
        <div id="bot-verify-result" style="display: none; padding: 12px; border-radius: 6px; font-size: 13px; margin-top: 12px;"></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="cancel-bot-modal">Cancel</button>
        <button class="btn btn-primary" id="save-bot-btn">Save Bot</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const close = () => modal.remove();
  modal.querySelector("#close-bot-modal").onclick = close;
  modal.querySelector("#cancel-bot-modal").onclick = close;

  modal.querySelector("#save-bot-btn").onclick = async () => {
    const name = modal.querySelector("#bot-name").value.trim();
    const token = modal.querySelector("#bot-token").value.trim();
    const saveBtn = modal.querySelector("#save-bot-btn");
    const resultBox = modal.querySelector("#bot-verify-result");

    if (!token) {
      showToast("Bot token is required", "error");
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = "Verifying with Telegram...";

    try {
      const newBot = await api.createBot(name, token);
      showToast(`Bot @${newBot.bot_username || newBot.name} added successfully!`, "success");
      close();
      if (onSuccess) onSuccess(newBot);
    } catch (err) {
      resultBox.style.display = "block";
      resultBox.style.background = "rgba(239, 68, 68, 0.15)";
      resultBox.style.color = "#f87171";
      resultBox.textContent = `Verification Error: ${err.message}`;
      showToast(err.message, "error");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Bot";
    }
  };
}
