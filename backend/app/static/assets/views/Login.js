import { api } from "../api.js";
import { showToast } from "../components/Toast.js";

export function renderLogin(container, onLoginSuccess) {
  container.innerHTML = `
    <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #070a13; padding: 20px;">
      <div style="width: 100%; max-width: 400px; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 36px 32px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
        <div style="text-align: center; margin-bottom: 28px;">
          <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #38bdf8, #2563eb); border-radius: 12px; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: white;">
            ⚡
          </div>
          <h2 style="font-size: 20px; font-weight: 700; color: white;">Telegram Channel Cloner</h2>
          <p style="font-size: 13px; color: #94a3b8; margin-top: 6px;">Sign in to access your self-hosted dashboard</p>
        </div>

        <form id="login-form">
          <div class="form-group">
            <label>Username</label>
            <input type="text" id="login-username" class="form-control" placeholder="admin" required autofocus />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="login-password" class="form-control" placeholder="••••••••" required />
          </div>

          <div id="login-error" style="display: none; padding: 10px; border-radius: 6px; background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 13px; margin-bottom: 16px;"></div>

          <button type="submit" id="login-btn" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 10px; font-size: 15px;">
            Sign In
          </button>
        </form>

        <div style="margin-top: 24px; text-align: center; font-size: 12px; color: #64748b;">
          Portainer / Dockerized Production Instance
        </div>
      </div>
    </div>
  `;

  const form = container.querySelector("#login-form");
  const errBox = container.querySelector("#login-error");
  const btn = container.querySelector("#login-btn");

  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.style.display = "none";
    btn.disabled = true;
    btn.textContent = "Signing in...";

    const username = container.querySelector("#login-username").value.trim();
    const password = container.querySelector("#login-password").value;

    try {
      await api.login(username, password);
      showToast("Signed in successfully", "success");
      if (onLoginSuccess) onLoginSuccess();
    } catch (err) {
      errBox.style.display = "block";
      errBox.textContent = err.message;
      btn.disabled = false;
      btn.textContent = "Sign In";
    }
  };
}
