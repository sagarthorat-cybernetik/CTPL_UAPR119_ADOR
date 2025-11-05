/* ============================================================
   BTS Monitoring System — Main JS
   Handles: Login, Token Storage, Logout, Auth Header Utility
   ============================================================ */

// ----------------------
// Global Configuration
// ----------------------
const API_BASE = window.location.origin; // same Flask host
const TOKEN_KEY = "bts_auth_token";
const USER_KEY = "bts_user";

// ----------------------
// Helper: Token Handling
// ----------------------
function setToken(token, username = "Admin") {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, username);
}

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

function getAuthHeaders() {
  const token = getToken();
  return token
    ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
    : { "Content-Type": "application/json" };
}

// ----------------------
// Login Logic
// ----------------------
async function loginUser(username, password) {
  try {
    const response = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    const statusDiv = document.getElementById("loginStatus");

    if (response.ok) {
      statusDiv.style.color = "#00ff99";
      statusDiv.textContent = "✓ Login successful, redirecting...";
      // For demo, simulate token returned (Flask returns JWT normally)
      if (data.token) {
        setToken(data.token, username);
      } else {
        // If backend doesn't send token explicitly (since it's stored in auth.py)
        setToken("local-demo-token", username);
      }
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1000);
    } else {
      statusDiv.style.color = "#ff3c3c";
      statusDiv.textContent = data.error || "✗ Invalid credentials";
    }
  } catch (err) {
    console.error("Login error:", err);
    const statusDiv = document.getElementById("loginStatus");
    if (statusDiv) {
      statusDiv.style.color = "#ff3c3c";
      statusDiv.textContent = "✗ Unable to connect to server";
    }
  }
}

// ----------------------
// Logout Logic
// ----------------------
function logoutUser() {
  clearToken();
  window.location.href = "/";
}

// ----------------------
// Event Listeners
// ----------------------

// --- Login Page ---
document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const logoutBtn = document.getElementById("logoutBtn");
  const adminBtn = document.getElementById("adminBtn");
  const userName = document.getElementById("userName");

  // Handle login form submit
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value.trim();
      await loginUser(username, password);
    });
  }

  // Handle logout button
  if (logoutBtn) {
    logoutBtn.addEventListener("click", logoutUser);
  }

  // Display logged user name
  if (userName && sessionStorage.getItem(USER_KEY)) {
    userName.textContent = sessionStorage.getItem(USER_KEY);
  }

  // Handle admin button
  if (adminBtn) {
    adminBtn.addEventListener("click", () => {
      window.location.href = "/admin";
    });
  }
});

// ----------------------
// Utility: Fetch Wrapper
// ----------------------
async function apiFetch(url, options = {}) {
  const headers = getAuthHeaders();
  const config = { ...options, headers: { ...headers, ...(options.headers || {}) } };

  try {
    const res = await fetch(url, config);
    if (res.status === 401) {
      // Token expired or invalid → logout
      clearToken();
      alert("Session expired. Please log in again.");
      window.location.href = "/";
      return null;
    }
    return res;
  } catch (err) {
    console.error("API fetch error:", err);
    return null;
  }
}

// ----------------------
// Expose for other scripts
// ----------------------
window.BTS = {
  apiFetch,
  getAuthHeaders,
  logoutUser,
  getToken,
  setToken,
  clearToken,
  API_BASE,
};
