/* ============================================================
   BTS Monitoring System — Dashboard JS
   Handles: Device + Circuit UI, Actions, Data Rendering
   ============================================================ */

const gallery = document.getElementById("gallery");
// const deviceList = document.getElementById("deviceList");
// const circuitList = document.getElementById("circuitList");
const globalCollectStatus = document.getElementById("globalCollectStatus");

let selectedDeviceId = null;
let circuits = [];
let devices = [];

/* ============================================================
   1️⃣ Load Devices
   ============================================================ */
async function loadDevices() {
  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}/api/devices`);
    if (!res) return;
    const data = await res.json();
    devices = data.devices || [];

    // deviceList.innerHTML = "";
    // devices.forEach((dev) => {
    //   const li = document.createElement("li");
    //   li.classList.add("device");
    //   li.textContent = `Device ${dev.deviceId || dev.id}`;
    //   li.dataset.deviceId = dev.deviceId || dev.id;
    //   li.addEventListener("click", () => selectDevice(li.dataset.deviceId));
    //   deviceList.appendChild(li);
    // });

    if (devices.length > 0 && !selectedDeviceId) {
      selectDevice(devices[0].deviceId || devices[0].id);
    }
  } catch (err) {
    console.error("Error loading devices:", err);
  }
}

/* ============================================================
   2️⃣ Select Device → Load Circuits
   ============================================================ */
async function selectDevice(deviceId) {
  selectedDeviceId = deviceId;
  console.log("Selected device:", deviceId);

  // Demo: 16 circuits for now
  circuits = Array.from({ length: 16 }, (_, i) => ({
    circuitId: i + 1,
    deviceId,
    name: `Circuit ${i + 1}`,
    running: false,
    collecting: false,
    data: {}
  }));

//   renderCircuitList();
  renderGallery();
}

/* ============================================================
   3️⃣ Render Sidebar Circuits
   ============================================================ */
// function renderCircuitList() {
//   circuitList.innerHTML = "";
//   circuits.forEach((c) => {
//     const li = document.createElement("li");
//     li.classList.add("circuit");
//     li.textContent = c.name;
//     li.dataset.circuitId = c.circuitId;
//     li.addEventListener("click", () => scrollToCircuit(c.circuitId));
//     circuitList.appendChild(li);
//   });
// }

/* ============================================================
   4️⃣ Render Gallery Cards
   ============================================================ */
function renderGallery() {
  gallery.innerHTML = "";
  circuits.forEach((circuit) => {
    const card = document.createElement("article");
    card.classList.add("circuit-card");
    card.dataset.deviceId = circuit.deviceId;
    card.dataset.circuitId = circuit.circuitId;

    card.innerHTML = `
      <header class="card-header">
        <h3 class="circuit-name">${circuit.name}</h3>
        <div class="card-controls">
          <div class="action-controls">
            <button class="btn-maximize" data-action="open" title="Open Details">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
              </svg>
            </button>
            <div class="dropdown-menu">
              <button class="btn-menu" title="Actions">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                </svg>
              </button>
              <div class="dropdown-content">
                <div class="dropdown-item" data-action="collect">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                  </svg>
                  Start Collect
                </div>
                <div class="dropdown-item" data-action="pause">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                  </svg>
                  Pause
                </div>
                <div class="dropdown-item" data-action="continue">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  Continue
                </div>
                <div class="dropdown-item" data-action="stop">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 6h12v12H6z"/>
                  </svg>
                  Stop
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>
          <div class="badges">
            <span class="badge status ${circuit.running ? "running" : "stopped"}" id="status-${circuit.deviceId}-${circuit.circuitId}">
              ${circuit.running ? "Running" : "Stopped"}
            </span>
            <span class="badge collect ${circuit.collecting ? "started" : "stopped"}" id="collect-${circuit.deviceId}-${circuit.circuitId}">
              Collect: ${circuit.collecting ? "Started" : "Stopped"}
            </span>
            <span class="badge">
                Battery ID: ${circuit.batteryId}
            </span>
          </div>


      <div class="metrics">
        ${["temperature", "voltage", "current", "power", "resistance"].map(
          (m) => `
          <div class="metric">
            <span class="label">${m.charAt(0).toUpperCase() + m.slice(1)}</span>
            <span class="value" id="${m}-${circuit.deviceId}-${circuit.circuitId}">--</span>
          </div>
        `
        ).join("")}
      </div>
    `;

    // Add event listeners for maximize button
    const maximizeBtn = card.querySelector(".btn-maximize");
    maximizeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openCircuitModal(circuit);
    });

    // Add event listeners for dropdown menu
    const menuBtn = card.querySelector(".btn-menu");
    const dropdownContent = card.querySelector(".dropdown-content");
    
    menuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      // Close other open dropdowns
      document.querySelectorAll(".dropdown-content.show").forEach(dd => {
        if (dd !== dropdownContent) dd.classList.remove("show");
      });
      dropdownContent.classList.toggle("show");
    });

    // Add event listeners for dropdown items
    card.querySelectorAll(".dropdown-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdownContent.classList.remove("show");
        handleCircuitAction(e, circuit);
      });
    });

    gallery.appendChild(card);
  });

  // Close dropdowns when clicking outside
  document.addEventListener("click", () => {
    document.querySelectorAll(".dropdown-content.show").forEach(dd => {
      dd.classList.remove("show");
    });
  });
}

/* ============================================================
   5️⃣ Circuit Action Handlers
   ============================================================ */
async function handleCircuitAction(e, circuit) {
  const action = e.target.dataset.action;
  console.log(`Action: ${action} on Circuit ${circuit.circuitId}`);

  if (action === "open") {
    openCircuitModal(circuit);
    return;
  }

  let endpoint = "";
  switch (action) {
    case "collect":
      endpoint = "/api/DBCUpload/create-db-files";
      break;
    case "pause":
      endpoint = "/api/command/pause";
      break;
    case "continue":
      endpoint = "/api/command/continue";
      break;
    case "stop":
      endpoint = "/api/command/stop";
      break;
  }

  if (!endpoint) return;

  try {
    const res = await BTS.apiFetch(`${BTS.API_BASE}${endpoint}`, {
      method: "POST",
      headers: BTS.getAuthHeaders(),
      body: JSON.stringify({
        deviceId: circuit.deviceId,
        circuitId: circuit.circuitId,
        circuitNo: circuit.circuitId,
      }),
    });
    if (res) {
      const data = await res.json();
      console.log(`${action} response:`, data);
    }
  } catch (err) {
    console.error("Action error:", err);
  }
}

/* ============================================================
   6️⃣ Live Data Updates (from websocket.js)
   ============================================================ */
function updateLiveCircuitData(payload) {
  if (!payload || !payload.circuits) return;

  payload.circuits.forEach((circuitData) => {
    const { circuit_id, file_name, ...metrics } = circuitData;
    const deviceId = selectedDeviceId;

    // Update metrics
    Object.entries(metrics).forEach(([key, value]) => {
      const el = document.getElementById(`${key}-${deviceId}-${circuit_id}`);
      if (el) el.textContent = value.toFixed ? value.toFixed(2) : value;
    });

    // Update status badges
    const statusEl = document.getElementById(`status-${deviceId}-${circuit_id}`);
    const collectEl = document.getElementById(`collect-${deviceId}-${circuit_id}`);
    if (statusEl) statusEl.textContent = "Running";
    if (collectEl) collectEl.textContent = "Collect: Started";
  });
}

/* ============================================================
   7️⃣ Circuit Modal (Popup)
   ============================================================ */
const modal = document.getElementById("circuitModal");
const modalClose = document.getElementById("modalClose");
const modalBackdrop = document.getElementById("modalBackdrop");

function openCircuitModal(circuit) {
  modal.setAttribute("aria-hidden", "false");
  document.getElementById("detailDeviceId").textContent = circuit.deviceId;
  document.getElementById("detailCircuitId").textContent = circuit.circuitId;
  document.getElementById("detailCollectStatus").textContent = circuit.collecting ? "Started" : "Stopped";
  document.getElementById("detailRunStatus").textContent = circuit.running ? "Running" : "Stopped";
  document.getElementById("detailDbFile").textContent = circuit.dbFile || "--";
  
  // Initialize the default tab (Charts)
  const defaultTab = document.querySelector('.tab[data-tab="liveChart"]');
  if (defaultTab) {
    defaultTab.click();
  }
}

function closeModal() {
  modal.setAttribute("aria-hidden", "true");
}

if (modalClose) modalClose.addEventListener("click", closeModal);
if (modalBackdrop) modalBackdrop.addEventListener("click", closeModal);
document.getElementById("modalCloseBottom")?.addEventListener("click", closeModal);

/* ============================================================
   🔄 Tab Functionality for Modal
   ============================================================ */
function initializeTabs() {
  const tabs = document.querySelectorAll('.tab');
  const tabPanels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      
      const targetTab = tab.getAttribute('data-tab');
      
      // Remove active class from all tabs
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      
      // Hide all tab panels
      tabPanels.forEach(panel => {
        panel.classList.remove('active');
      });
      
      // Add active class to clicked tab
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      
      // Show corresponding panel
      const targetPanel = document.getElementById(targetTab);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
      
      // Handle specific tab activation logic
      switch(targetTab) {
        case 'liveChart':
          initializeCharts();
          break;
        case 'liveTable':
          updateDataTable();
          break;
        case 'controls':
          updateControlsPanel();
          break;
      }
      
      console.log(`Switched to tab: ${targetTab}`);
    });
  });
}

/* ============================================================
   📊 Tab Content Handlers
   ============================================================ */
function initializeCharts() {
  // Initialize or refresh charts when the Charts tab is activated
  console.log("Initializing charts...");
  
  // You can add chart library initialization here
  // Example: Chart.js, D3.js, or any other charting library
  
  // For now, we'll add placeholder functionality
  const chartContainers = document.querySelectorAll('.chart-area');
  chartContainers.forEach((container, index) => {
    if (!container.dataset.initialized) {
      container.innerHTML = `
        <div style="
          height: 150px; 
          background: var(--bg-secondary); 
          border: 2px solid var(--border-color); 
          border-radius: var(--radius);
          display: flex; 
          align-items: center; 
          justify-content: center;
          color: var(--text-secondary);
          font-weight: 600;
        ">
          📈 Chart ${index + 1} - Live Data Visualization
        </div>
      `;
      container.dataset.initialized = 'true';
    }
  });
}

function updateDataTable() {
  // Update data table when the Table tab is activated
  console.log("Updating data table...");
  
  const tableBody = document.querySelector('#readingTable tbody');
  if (tableBody) {
    // Clear existing data
    tableBody.innerHTML = '';
    
    // Add sample data rows (replace with real data)
    const sampleData = [
      { timestamp: new Date().toLocaleString(), temperature: '25.4°C', voltage: '12.5V', current: '2.1A', power: '26.25W', resistance: '5.95Ω' },
      { timestamp: new Date(Date.now() - 60000).toLocaleString(), temperature: '25.2°C', voltage: '12.4V', current: '2.0A', power: '24.8W', resistance: '6.2Ω' },
      { timestamp: new Date(Date.now() - 120000).toLocaleString(), temperature: '25.1°C', voltage: '12.3V', current: '1.9A', power: '23.37W', resistance: '6.47Ω' }
    ];
    
    sampleData.forEach(row => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${row.timestamp}</td>
        <td>${row.temperature}</td>
        <td>${row.voltage}</td>
        <td>${row.current}</td>
        <td>${row.power}</td>
        <td>${row.resistance}</td>
      `;
      tableBody.appendChild(tr);
    });
  }
}

function updateControlsPanel() {
  // Update controls panel when the Controls tab is activated
  console.log("Updating controls panel...");
  
  // Add event listeners to modal control buttons if not already added
  const modalCollect = document.getElementById('modalCollect');
  const modalPause = document.getElementById('modalPause');
  const modalContinue = document.getElementById('modalContinue');
  const modalStop = document.getElementById('modalStop');
  
  if (modalCollect && !modalCollect.dataset.listenerAdded) {
    modalCollect.addEventListener('click', () => {
      console.log('Modal Collect clicked');
      // Add collect functionality here
    });
    modalCollect.dataset.listenerAdded = 'true';
  }
  
  if (modalPause && !modalPause.dataset.listenerAdded) {
    modalPause.addEventListener('click', () => {
      console.log('Modal Pause clicked');
      // Add pause functionality here
    });
    modalPause.dataset.listenerAdded = 'true';
  }
  
  if (modalContinue && !modalContinue.dataset.listenerAdded) {
    modalContinue.addEventListener('click', () => {
      console.log('Modal Continue clicked');
      // Add continue functionality here
    });
    modalContinue.dataset.listenerAdded = 'true';
  }
  
  if (modalStop && !modalStop.dataset.listenerAdded) {
    modalStop.addEventListener('click', () => {
      console.log('Modal Stop clicked');
      // Add stop functionality here
    });
    modalStop.dataset.listenerAdded = 'true';
  }
}

/* ============================================================
   8️⃣ Graph Navigation
   ============================================================ */
function initializeGraphNavigation() {
  const graphButtons = document.querySelectorAll('.btn-graph');
  const chartContainers = document.querySelectorAll('.chart-container');

  if (graphButtons.length === 0) return;

  graphButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetGraph = button.dataset.graph;
      
      // Remove active class from all buttons
      graphButtons.forEach(btn => btn.classList.remove('active'));
      
      // Add active class to clicked button
      button.classList.add('active');
      
      // Hide all chart containers
      chartContainers.forEach(container => container.classList.remove('active'));
      
      // Show target chart container
      const targetContainer = document.getElementById(`container-${targetGraph}`);
      if (targetContainer) {
        targetContainer.classList.add('active');
        
        // Trigger chart resize/redraw if needed
        setTimeout(() => {
          // This timeout allows the container to become visible before chart operations
          const chartElement = targetContainer.querySelector('.chart-area-large');
          if (chartElement && window.charts && window.charts[targetGraph]) {
            // If you're using a charting library, trigger resize here
            // Example for Chart.js: window.charts[targetGraph].resize();
            // Example for other libraries: window.charts[targetGraph].reflow();
          }
        }, 100);
      }
    });
  });
}

/* ============================================================
   9️⃣ Utility
   ============================================================ */
function scrollToCircuit(circuitId) {
  const card = document.querySelector(`[data-circuit-id="${circuitId}"]`);
  if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ============================================================
   Initialize Dashboard
   ============================================================ */
document.addEventListener("DOMContentLoaded", async () => {
  await loadDevices();

  // Initialize tab functionality
  initializeTabs();

  // Initialize graph navigation
  initializeGraphNavigation();

  // Start listening to live data
  if (window.BTSWebSocket) {
    window.BTSWebSocket.onData = updateLiveCircuitData;
  }

  // Refresh button
  const refreshBtn = document.getElementById("refreshDevices");
  if (refreshBtn) refreshBtn.addEventListener("click", loadDevices);
});
