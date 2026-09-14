// Authenticated API client

const TOKEN_KEY = "cloner_token";
const USER_KEY = "cloner_user";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  getUser: () => localStorage.getItem(USER_KEY),
  setUser: (user) => localStorage.setItem(USER_KEY, user),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.hash = "#/login";
  },
  isAuthenticated: () => !!localStorage.getItem(TOKEN_KEY),
};

export async function apiRequest(endpoint, options = {}) {
  const token = auth.getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    auth.logout();
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    let errorDetail = "Request failed";
    try {
      const errData = await response.json();
      errorDetail = errData.detail || errData.message || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  // If response is empty or blob (e.g. backup download)
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }
  return response;
}

export const api = {
  // Auth
  login: async (username, password) => {
    const res = await apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    auth.setToken(res.access_token);
    auth.setUser(res.username);
    return res;
  },
  getMe: () => apiRequest("/api/auth/me"),
  changePassword: (old_password, new_password) =>
    apiRequest("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ old_password, new_password }),
    }),

  // Dashboard
  getStats: () => apiRequest("/api/dashboard/stats"),

  // Bots
  getBots: () => apiRequest("/api/bots"),
  createBot: (name, token) =>
    apiRequest("/api/bots", {
      method: "POST",
      body: JSON.stringify({ name, token }),
    }),
  updateBot: (id, data) =>
    apiRequest(`/api/bots/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteBot: (id) => apiRequest(`/api/bots/${id}`, { method: "DELETE" }),
  testBot: (id) => apiRequest(`/api/bots/${id}/test`, { method: "POST" }),

  // Jobs
  getJobs: () => apiRequest("/api/jobs"),
  getJob: (id) => apiRequest(`/api/jobs/${id}`),
  createJob: (data) =>
    apiRequest("/api/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateJob: (id, data) =>
    apiRequest(`/api/jobs/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteJob: (id) => apiRequest(`/api/jobs/${id}`, { method: "DELETE" }),
  runJob: (id) => apiRequest(`/api/jobs/${id}/run`, { method: "POST" }),
  stopJob: (id) => apiRequest(`/api/jobs/${id}/stop`, { method: "POST" }),
  pauseSchedule: (id) => apiRequest(`/api/jobs/${id}/pause`, { method: "POST" }),
  resumeSchedule: (id) => apiRequest(`/api/jobs/${id}/resume`, { method: "POST" }),
  probeChannel: (bot_id, chat_id) =>
    apiRequest("/api/jobs/probe-channel", {
      method: "POST",
      body: JSON.stringify({ bot_id, chat_id }),
    }),

  // Executions & Logs
  getExecutions: (jobId) => apiRequest(`/api/jobs/${jobId}/executions`),
  getExecution: (execId) => apiRequest(`/api/executions/${execId}`),
  getExecutionLogs: (execId, level) =>
    apiRequest(`/api/executions/${execId}/logs${level ? `?level=${level}` : ""}`),

  // System
  getSystemInfo: () => apiRequest("/api/system/info"),
};
