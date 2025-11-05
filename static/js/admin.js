/* ============================================================
   BTS Monitoring System — Admin Threshold Panel
   Handles: Fetch, Edit, Save, Reset Thresholds
   ============================================================ */

const form = document.getElementById("thresholdForm");
const resetBtn = document.getElementById("resetDefaults");
const jsonView = document.getElementById("thresholdJsonView");

// Default safe threshold limits
const DEFAULT_THRESHOLDS = {
  temperature: 80.0,
  voltage: 250.0,
  current: 20.0,
  power: 5000.0,
  resistance: 1000.0,
};

/* ============================================================
   1️⃣ Fetch Current Thresholds
   ============================================================ */
async function loadThresholds() {
  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/thresholds`);
    if (!res) return;
    const data = await res.json();
    populateForm(data);
    renderJson(data);
  } catch (err) {
    console.error("Error loading thresholds:", err);
  }
}

/* ============================================================
   2️⃣ Populate Form Inputs
   ============================================================ */
function populateForm(data) {
  for (const key of Object.keys(DEFAULT_THRESHOLDS)) {
    const input = document.getElementById(key);
    if (input) {
      input.value = data[key] ?? DEFAULT_THRESHOLDS[key];
    }
  }
}

/* ============================================================
   3️⃣ Save Thresholds
   ============================================================ */
async function saveThresholds(e) {
  e.preventDefault();

  const newThresholds = {};
  for (const key of Object.keys(DEFAULT_THRESHOLDS)) {
    const input = document.getElementById(key);
    if (input) newThresholds[key] = parseFloat(input.value);
  }

  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/thresholds`, {
      method: "POST",
      headers: BTS.getAuthHeaders(),
      body: JSON.stringify(newThresholds),
    });

    if (res && res.ok) {
      const data = await res.json();
      alert("✅ Thresholds saved successfully!");
      renderJson(newThresholds);
      console.log("Saved thresholds:", data);
    } else {
      alert("⚠️ Failed to save thresholds.");
    }
  } catch (err) {
    console.error("Error saving thresholds:", err);
  }
}

/* ============================================================
   4️⃣ Reset to Default Thresholds
   ============================================================ */
async function resetToDefaults() {
  if (!confirm("Reset to default safe limits?")) return;

  try {
    populateForm(DEFAULT_THRESHOLDS);
    renderJson(DEFAULT_THRESHOLDS);

    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/thresholds`, {
      method: "POST",
      headers: BTS.getAuthHeaders(),
      body: JSON.stringify(DEFAULT_THRESHOLDS),
    });

    if (res && res.ok) {
      alert("✅ Thresholds reset to default values!");
    } else {
      alert("⚠️ Failed to reset thresholds.");
    }
  } catch (err) {
    console.error("Error resetting thresholds:", err);
  }
}

/* ============================================================
   5️⃣ Render JSON View
   ============================================================ */
function renderJson(obj) {
  if (jsonView) {
    jsonView.textContent = JSON.stringify(obj, null, 2);
  }
}

/* ============================================================
   6️⃣ Initialize Admin Page
   ============================================================ */
document.addEventListener("DOMContentLoaded", () => {
  if (!form) return;

  loadThresholds();

  form.addEventListener("submit", saveThresholds);
  resetBtn.addEventListener("click", resetToDefaults);
});
