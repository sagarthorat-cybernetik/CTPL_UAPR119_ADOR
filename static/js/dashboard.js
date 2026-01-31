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
let currentModalCircuit = null;
let modalUpdateInterval = null;
let circuitChartData = {}; // Store chart data for each circuit


/* ============================================================
   2️⃣ Select Device → Load Circuits
   ============================================================ */
async function selectDevice(deviceId) {
  selectedDeviceId = deviceId;
  // console.log("Selected device:", deviceId);

  // Demo: 16 circuits for now
  circuits = Array.from({ length: 16 }, (_, i) => ({
    deviceId: deviceId,
    circuitId: i + 1,
    name: `Circuit ${i + 1}`,
    Status: "Stopped",
    batteryId: "--", // Generate battery ID
    startTime: null, // Will be set when collecting starts
    StopTime: null,
    CycleTime: null,
    data: {}
  }));

//   renderCircuitList();
  renderGallery();
}


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
    
    const units = ["mV","Ah", "V", "V", "V", "˚C", "˚C", "%" , "˚C"];
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
            
          </div>
        </div>
      </header>
          <div class="badges">           
            <span class="badge battery-id" id="battery-id-${circuit.deviceId}-${circuit.circuitId}">
               ${circuit.batteryId}
            </span>
          </div>


      <div class="metrics">
        ${["Cell Deviation", "Capacity", "Pack Voltage", "Max cell Voltage ", "Min cell Voltage", "Max cell Temperature ", "Min Cell Temperature", "SOC" , "Temp Difference ∆T(Manual)"].map(
          (m,i) => `
          <div class="metric">
            <span class="label">${m.charAt(0).toUpperCase() + m.slice(1)}</span>
            <span class="value" id="${m}-${circuit.deviceId}-${circuit.circuitId}">--${units[i]}</span>
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

    gallery.appendChild(card);
  });

  // Close dropdowns when clicking outside
  document.addEventListener("click", () => {
    document.querySelectorAll(".dropdown-content.show").forEach(dd => {
      dd.classList.remove("show");
    });
  });
}

function loadmachine1(){
  current_machine="Machine 1";
  selectDevice(1);
  document.getElementById("current-machine").innerText=current_machine;
  // hide machine 1 button and show others

}

function loadmachine2(){
  current_machine="Machine 2";
  selectDevice(2);
  document.getElementById("current-machine").innerText=current_machine;
  // hide machine 2 button and show others
}

function loadmachine3(){
  current_machine="Machine 3";
  selectDevice(3);
  document.getElementById("current-machine").innerText="HRD/HRC";
  // hide machine 3 button and show others
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
      endpoint = "/api/command/collect";
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
      
      // Update circuit state based on action
      const circuitIndex = circuits.findIndex(c => c.circuitId === circuit.circuitId);
      if (circuitIndex !== -1) {
        switch (action) {
          case "collect":
            circuits[circuitIndex].collecting = true;
            circuits[circuitIndex].running = true;
            circuits[circuitIndex].startTime = new Date().toISOString();
            
            // Update UI immediately
            const startTimeEl = document.getElementById(`start-time-${circuit.deviceId}-${circuit.circuitId}`);
            if (startTimeEl) {
              startTimeEl.textContent = `Started: ${new Date().toLocaleTimeString()}`;
            }
            
            const collectEl = document.getElementById(`collect-${circuit.deviceId}-${circuit.circuitId}`);
            if (collectEl) {
              collectEl.textContent = "Collect: Started";
              collectEl.className = "badge collect started";
            }
            
            const statusEl = document.getElementById(`status-${circuit.deviceId}-${circuit.circuitId}`);
            if (statusEl) {
              statusEl.textContent = "Running";
              statusEl.className = "badge status running";
            }
            break;
            
          case "stop":
            circuits[circuitIndex].collecting = false;
            circuits[circuitIndex].running = false;
            circuits[circuitIndex].startTime = null;
            
            // Update UI immediately
            const stopStartTimeEl = document.getElementById(`start-time-${circuit.deviceId}-${circuit.circuitId}`);
            if (stopStartTimeEl) {
              stopStartTimeEl.textContent = "Not Started";
            }
            
            const stopCollectEl = document.getElementById(`collect-${circuit.deviceId}-${circuit.circuitId}`);
            if (stopCollectEl) {
              stopCollectEl.textContent = "Collect: Stopped";
              stopCollectEl.className = "badge collect stopped";
            }
            
            const stopStatusEl = document.getElementById(`status-${circuit.deviceId}-${circuit.circuitId}`);
            if (stopStatusEl) {
              stopStatusEl.textContent = "Stopped";
              stopStatusEl.className = "badge status stopped";
            }
            break;
            
          case "pause":
            circuits[circuitIndex].running = false;
            circuits[circuitIndex].paused = true;


            // update UI immediately
            const pauseStatusEl = document.getElementById(`status-${circuit.deviceId}-${circuit.circuitId}`);
            const pauseCollectEl = document.getElementById(`collect-${circuit.deviceId}-${circuit.circuitId}`);
            if (pauseStatusEl) {
              pauseStatusEl.textContent = "Paused";
              pauseStatusEl.className = "badge status paused";
            }
            if (pauseCollectEl) {
              pauseCollectEl.textContent = "Collect: Paused";
              pauseCollectEl.className = "badge collect paused";
            }

            break;
            
          case "continue":
            circuits[circuitIndex].running = true;
            circuits[circuitIndex].paused = false;
            break;
        }
        
        console.log(`🔄 Updated circuit ${circuit.circuitId} state:`, circuits[circuitIndex]);
      }
    }
  } catch (err) {
    console.error("Action error:", err);
  }
}

/* ============================================================
   6️⃣ Live Data Updates (from websocket.js)
   ============================================================ */
function updateLiveCircuitData(payload) {
  // console.log("🎯 Dashboard updating with payload:", payload);
  
  if (!payload || !payload.circuits) {
    console.warn("⚠️ No circuits data in payload");
    return;
  }

  payload.circuits.forEach((circuitData) => {
    // console.log("🔄 Processing circuit data:", circuitData);
    
    const circuit_id = circuitData.circuit_id || circuitData.circuitId;
    const deviceId = selectedDeviceId || 2; // Fallback to device 2
    
    if (!circuit_id) {
      console.warn("⚠️ No circuit_id found in data:", circuitData);
      return;
    }

    // Update the circuit in our local array
    const circuitIndex = circuits.findIndex(c => c.circuitId == circuit_id);
    if (circuitIndex !== -1) {
      circuits[circuitIndex].running = true;
      circuits[circuitIndex].collecting = true;
      circuits[circuitIndex].lastUpdated = circuitData.timestamp || new Date().toISOString();
      
      // Set start time if not already set
      if (!circuits[circuitIndex].startTime) {
        circuits[circuitIndex].startTime = circuitData.timestamp || new Date().toISOString();
      }
    }
    // console.log(circuitData);
    
    // Extract metrics with fallbacks
    const metrics = {
      temperature: circuitData.temperature || circuitData.MaxTemp || circuitData.maxtemp || '--',
      voltage: circuitData.avgcellvol || circuitData.PackVol || circuitData.packvol || '--',
      current: circuitData.current || circuitData.PackCurr || circuitData.packcurr || '--',
      power: circuitData.ressocprot || circuitData.Power || '--',
      resistance: circuitData.resstatus || circuitData.Resistance || '--'
    };

    // console.log(`📊 Circuit ${circuit_id} metrics:`, metrics);

    // Update metric displays
    Object.entries(metrics).forEach(([key, value]) => {
      const el = document.getElementById(`${key}-${deviceId}-${circuit_id}`);
      if (el) {
        if (value !== '--' && typeof value === 'number') {
          // Format numbers appropriately
          if (key === 'temperature') {
            el.textContent = `${value.toFixed(1)}°C`;
          } else if (key === 'voltage') {
            el.textContent = `${value.toFixed(2)}V`;
          } else if (key === 'current') {
            el.textContent = `${value.toFixed(2)}A`;
          } else if (key === 'power') {
            el.textContent = `${value.toFixed(2)}W`;
          } else if (key === 'resistance') {
            el.textContent = `${value.toFixed(2)}Ω`;
          } else {
            el.textContent = value.toFixed ? value.toFixed(2) : value;
          }
        } else {
          el.textContent = value;
        }
        // console.log(`✅ Updated ${key} for circuit ${circuit_id}: ${el.textContent}`);
      } else {
        console.warn(`⚠️ Element not found: ${key}-${deviceId}-${circuit_id}`);
      }
    });

    // Update status badges
    const statusEl = document.getElementById(`status-${deviceId}-${circuit_id}`);
    const collectEl = document.getElementById(`collect-${deviceId}-${circuit_id}`);
    const batteryIdEl = document.getElementById(`battery-id-${deviceId}-${circuit_id}`);
    const startTimeEl = document.getElementById(`start-time-${deviceId}-${circuit_id}`);
    
    if (statusEl) {
      // Update status text based on circuit state or data
      let statusText = "Stopped";
      // console.log(circuitData.status);
      
      if (circuitData.status) {
        switch(circuitData.status) {
          case 1:
            statusText = "Rest";
            break;
          case 2:
            statusText = "Charging";
            break;
          case 3:
            statusText = "Discharging";
            break;
          case 4:
            statusText = "Stop";
            break;
          case 5:
            statusText = "Paused";
            break;
          default:
            statusText = "Running";
        }
      } else if (circuits[circuitIndex] && circuits[circuitIndex].running) {
        statusText = "Running";
      }
      statusEl.textContent = statusText;
      statusEl.className = `badge status ${statusText.toLowerCase()}`;
      // console.log(`✅ Updated status for circuit ${circuit_id}: Running`);
    }
    
    if (collectEl) {
      collectEl.textContent = "Collect: Started";
      collectEl.className = "badge collect started";
      // console.log(`✅ Updated collect status for circuit ${circuit_id}: Started`);
    }

    // Update battery ID if provided in data
    if (batteryIdEl && circuitData.battery_id) {
      batteryIdEl.textContent = `Battery ID: ${circuitData.battery_id}`;
      // console.log(`✅ Updated battery ID for circuit ${circuit_id}: ${circuitData.battery_id}`);
    }

    // Update start time
    if (startTimeEl && circuitIndex !== -1 && circuits[circuitIndex].startTime) {
      const startTime = new Date(circuits[circuitIndex].startTime);
      startTimeEl.textContent = `Started: ${startTime.toLocaleTimeString()}`;
      // console.log(`✅ Updated start time for circuit ${circuit_id}: ${startTime.toLocaleTimeString()}`);
    }

    // Update last updated time in modal if open
    const detailUpdatedEl = document.getElementById("detailUpdated");
    if (detailUpdatedEl) {
      detailUpdatedEl.textContent = new Date().toLocaleString();
    }
  });

  // Log summary
  // console.log(`🎯 Dashboard update complete. Updated ${payload.circuits.length} circuits`);
}

/* ============================================================
   7️⃣ Circuit Modal (Popup)
   ============================================================ */
const modal = document.getElementById("circuitModal");
const modalClose = document.getElementById("modalClose");
const modalBackdrop = document.getElementById("modalBackdrop");

function openCircuitModal(circuit) {
  console.log("🔍 Opening modal for circuit:", circuit);
  
  // Set current modal circuit and start data fetching
  currentModalCircuit = circuit;
  
  // Clear any previous chart data for this circuit to prevent contamination
  const circuitKey = `${circuit.deviceId}-${circuit.circuitId}`;
  circuitChartData[circuitKey] = [];
  
  modal.setAttribute("aria-hidden", "false");

  
  // Update last updated time
  const detailUpdatedEl = document.getElementById("detailUpdated");
  if (detailUpdatedEl) {
    detailUpdatedEl.textContent = circuit.lastUpdated ? 
      new Date(circuit.lastUpdated).toLocaleString() : 
      'Never';
  }
  
  // Add battery ID and start time if elements exist in modal
  const detailBatteryId = document.getElementById("detailBatteryId");
  if (detailBatteryId) {
    detailBatteryId.textContent = circuit.batteryId || 'Unknown';
  }
  
  const detailStartTime = document.getElementById("detailStartTime");
  if (detailStartTime) {
    detailStartTime.textContent = circuit.startTime ? 
      new Date(circuit.startTime).toLocaleString() : 
      'Not Started';
  }
  
  // Initialize the default tab (Charts)
  const defaultTab = document.querySelector('.tab[data-tab="liveChart"]');
  if (defaultTab) {
    defaultTab.click();
  }
  
  // Start fetching circuit data and updating modal
  startModalDataUpdates(circuit);
}

function closeModal() {
  modal.setAttribute("aria-hidden", "true");
  
  // Stop modal data updates
  stopModalDataUpdates();
  
  // Clear current modal circuit
  currentModalCircuit = null;
  
  // Clear all chart containers to prevent data contamination
  const chartContainers = document.querySelectorAll('.chart-area-large');
  chartContainers.forEach((container) => {
    container.innerHTML = '';
    delete container.dataset.initialized;
  });
}

async function startModalDataUpdates(circuit) {
  console.log(`🔄 Starting modal data updates for circuit ${circuit.circuitId}`);
  
  // Initial data fetch
  await fetchCircuitData(circuit);
  
  // Start interval for updates every second
  modalUpdateInterval = setInterval(async () => {
    if (currentModalCircuit && currentModalCircuit.circuitId === circuit.circuitId) {
      await fetchCircuitData(circuit);
    }
  }, 1000);
}

function stopModalDataUpdates() {
  if (modalUpdateInterval) {
    clearInterval(modalUpdateInterval);
    modalUpdateInterval = null;
    console.log("⏹️ Stopped modal data updates");
  }
}

async function fetchCircuitData(circuit) {
  try {
    const response = await BTS.apiFetch(`${BTS.API_BASE}/api/circuit-data/${circuit.deviceId}/${circuit.circuitId}?limit=50`);
    
    if (!response || !response.ok) {
      console.warn(`⚠️ Failed to fetch data for circuit ${circuit.circuitId}`);
      return;
    }
    
    const data = await response.json();
    
    if (data.error) {
      console.warn(`⚠️ Error fetching circuit data: ${data.error}`);
      return;
    }
    
    // Store chart data for this circuit
    const circuitKey = `${circuit.deviceId}-${circuit.circuitId}`;
    circuitChartData[circuitKey] = data.data;
    
    // Update modal with latest data
    updateModalContent(circuit, data);
    
  } catch (error) {
    console.error(`❌ Error fetching circuit data:`, error);
  }
}

if (modalClose) modalClose.addEventListener("click", closeModal);
if (modalBackdrop) modalBackdrop.addEventListener("click", closeModal);
document.getElementById("modalCloseBottom")?.addEventListener("click", closeModal);

function updateModalContent(circuit, circuitData) {
  if (!currentModalCircuit || currentModalCircuit.circuitId !== circuit.circuitId) {
    return; // Modal closed or different circuit
  }
  
  const data = circuitData.data;
  if (!data || data.length === 0) {
    return;
  }
  
  // Get latest data point
  const latestData = data[data.length - 1];
  
  // Update last updated time
  const detailUpdatedEl = document.getElementById("detailUpdated");
  if (detailUpdatedEl) {
    detailUpdatedEl.textContent = new Date().toLocaleString();
  }
  
  // Update charts if charts tab is active
  const chartsTab = document.getElementById("liveChart");
  if (chartsTab && chartsTab.classList.contains("active")) {
    updateModalCharts(circuit, data);
  }
  
  // Update data table if table tab is active
  const tableTab = document.getElementById("liveTable");
  if (tableTab && tableTab.classList.contains("active")) {
    updateModalDataTable(circuit, data);
  }
  
  // console.log(`📊 Updated modal content for circuit ${circuit.circuitId} with ${data.length} records`);
}

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
  
  if (currentModalCircuit) {
    const circuitKey = `${currentModalCircuit.deviceId}-${currentModalCircuit.circuitId}`;
    const data = circuitChartData[circuitKey] || [];
    updateModalCharts(currentModalCircuit, data);
  } else {
    // Show completely empty charts without any placeholder text
    const chartContainers = document.querySelectorAll('.chart-area-large');
    chartContainers.forEach((container, index) => {
      container.innerHTML = '';
      container.dataset.initialized = 'true';
    });
  }
}

function updateModalCharts(circuit, data) {
  if (!data || data.length === 0) {
    // Clear all charts and show "No Data Available" for this specific circuit
    const chartConfigs = {
      temperature: { containerId: 'chart-temperature', title: 'Temperature (°C)' },
      voltage: { containerId: 'chart-voltage', title: 'Voltage (V)' },
      current: { containerId: 'chart-current', title: 'Current (A)' },
      power: { containerId: 'chart-power', title: 'Power (W)' },
      resistance: { containerId: 'chart-resistance', title: 'Resistance (Ω)' }
    };
    
    Object.entries(chartConfigs).forEach(([chartType, config]) => {
      const container = document.getElementById(config.containerId);
      if (container) {
        container.innerHTML = '';
      }
    });
    
    // Also clear overview chart
    updateOverviewChart([], []);
    return;
  }
  
  // Extract time series data
  const timestamps = data.map(d => {
    try {
      return new Date(d.timestamp || d.time).toLocaleTimeString();
    } catch {
      return new Date().toLocaleTimeString();
    }
  });
  
  // Chart configurations
  const chartConfigs = {
    temperature: {
      containerId: 'chart-temperature',
      title: 'Temperature (°C)',
      dataKey: ['temperature', 'MaxTemp', 'maxtemp'],
      color: '#ff6b6b',
      unit: '°C'
    },
    voltage: {
      containerId: 'chart-voltage', 
      title: 'Voltage (V)',
      dataKey: ['voltage', 'PackVol', 'packvol', 'avgcellvol'],
      color: '#4ecdc4',
      unit: 'V'
    },
    current: {
      containerId: 'chart-current',
      title: 'Current (A)',
      dataKey: ['current', 'PackCurr', 'packcurr'],
      color: '#45b7d1',
      unit: 'A'
    },
    power: {
      containerId: 'chart-power',
      title: 'Power (W)',
      dataKey: ['power', 'Power', 'ressocprot'],
      color: '#96ceb4',
      unit: 'W'
    },
    resistance: {
      containerId: 'chart-resistance',
      title: 'Resistance (Ω)',
      dataKey: ['resistance', 'Resistance', 'resstatus'],
      color: '#feca57',
      unit: 'Ω'
    }
  };
  
  // Update each chart
  Object.entries(chartConfigs).forEach(([chartType, config]) => {
    updateSingleChart(config, data, timestamps);
  });
  
  // Update overview chart with all metrics
  updateOverviewChart(data, timestamps);
}

function updateSingleChart(config, data, timestamps) {
  const container = document.getElementById(config.containerId);
  if (!container) return;
  
  // Extract values for this metric
  const values = data.map(d => {
    for (let key of config.dataKey) {
      if (d[key] !== undefined && d[key] !== null) {
        return parseFloat(d[key]) || 0;
      }
    }
    return 0;
  });
  
  // Create simple line chart using Canvas
  const canvasId = `canvas-${config.containerId}`;
  let canvas = document.getElementById(canvasId);
  
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = canvasId;
    canvas.width = 800;
    canvas.height = 300;
    canvas.style.width = '100%';
    canvas.style.height = '300px';
    container.innerHTML = '';
    container.appendChild(canvas);
  }
  
  const ctx = canvas.getContext('2d');
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  if (values.length === 0) {
    // Just return without showing any message
    return;
  }
  
  // Chart margins
  const margin = { top: 30, right: 30, bottom: 50, left: 60 };
  const chartWidth = canvas.width - margin.left - margin.right;
  const chartHeight = canvas.height - margin.top - margin.bottom;
  
  // Find min/max values
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;
  
  // Draw background
  ctx.fillStyle = '#f8f9fa';
  ctx.fillRect(margin.left, margin.top, chartWidth, chartHeight);
  
  // Draw grid lines
  ctx.strokeStyle = '#e9ecef';
  ctx.lineWidth = 1;
  
  // Horizontal grid lines
  for (let i = 0; i <= 5; i++) {
    const y = margin.top + (chartHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + chartWidth, y);
    ctx.stroke();
    
    // Y-axis labels
    const value = maxVal - (range / 5) * i;
    ctx.fillStyle = '#666';
    ctx.font = '12px Arial';
    ctx.textAlign = 'right';
    ctx.fillText(value.toFixed(1) + config.unit, margin.left - 10, y + 4);
  }
  
  // Vertical grid lines
  const timeStep = Math.max(1, Math.floor(values.length / 10));
  for (let i = 0; i < values.length; i += timeStep) {
    const x = margin.left + (chartWidth / (values.length - 1)) * i;
    ctx.beginPath();
    ctx.moveTo(x, margin.top);
    ctx.lineTo(x, margin.top + chartHeight);
    ctx.stroke();
  }
  
  // Draw data line
  ctx.strokeStyle = config.color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  
  for (let i = 0; i < values.length; i++) {
    const x = margin.left + (chartWidth / (values.length - 1)) * i;
    const y = margin.top + chartHeight - ((values[i] - minVal) / range) * chartHeight;
    
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();
  
  // Draw data points
  ctx.fillStyle = config.color;
  for (let i = 0; i < values.length; i++) {
    const x = margin.left + (chartWidth / (values.length - 1)) * i;
    const y = margin.top + chartHeight - ((values[i] - minVal) / range) * chartHeight;
    
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
  }
  
  // Draw title
  ctx.fillStyle = '#333';
  ctx.font = 'bold 16px Arial';
  ctx.textAlign = 'center';
  ctx.fillText(config.title, canvas.width / 2, 20);
  
  // Draw X-axis labels (timestamps)
  ctx.fillStyle = '#666';
  ctx.font = '10px Arial';
  ctx.textAlign = 'center';
  for (let i = 0; i < timestamps.length; i += timeStep) {
    const x = margin.left + (chartWidth / (values.length - 1)) * i;
    ctx.save();
    ctx.translate(x, canvas.height - 10);
    ctx.rotate(-Math.PI / 4);
    ctx.fillText(timestamps[i], 0, 0);
    ctx.restore();
  }
}

function updateOverviewChart(data, timestamps) {
  const container = document.getElementById('chart-overview');
  if (!container) return;
  
  if (data.length === 0) {
    // Clear the overview chart completely when no data
    container.innerHTML = '';
    return;
  }
  
  container.innerHTML = `
    <div class="chart-overview" >
      <h3 style="margin: 0 0 20px 0;">Overview - Latest Values</h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
        ${(() => {
          const latest = data[data.length - 1];
          console.log(latest);
          
          return `
            <div class="metric-card">
              <div class="metric-label">Temperature</div>
              <div class="metric-value">${(() => {
                const temp = latest.temperature || latest.MaxTemp;
                return temp ? parseFloat(temp).toFixed(4) : '--';
              })()} °C</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Voltage</div>
              <div class="metric-value">${(() => {
                const volt = latest.voltage || latest.PackVol || latest.avgcellvol;
                return volt ? parseFloat(volt).toFixed(4) : '--';
              })()} V</div>
            </div>
            
            <div class="metric-card">
              <div class="metric-label">Current</div>
              <div class="metric-value">${(() => {
                const curr = latest.current || latest.PackCurr;
                return curr ? parseFloat(curr).toFixed(4) : '--';
              })()} A</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Power</div>
              <div class="metric-value">${(() => {
                const power = latest.ResSocProt || latest.ressocprot;
                return power ? parseFloat(power).toFixed(4) : '--';
              })()} W</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Resistance</div>
              <div class="metric-value">${(() => {
                const resistance = latest.ResStatus || latest.resstatus;
                return resistance ? parseFloat(resistance).toFixed(4) : '--';
              })()} Ω</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Timestamp</div>
              <div class="metric-value">${new Date(latest.timestamp || Date.now()).toLocaleString()}</div>
            </div>
          `;
        })()}
      </div>
    </div>
  `;
}

function updateDataTable() {
  // Update data table when the Table tab is activated
  console.log("Updating data table...");
  
  if (currentModalCircuit) {
    const circuitKey = `${currentModalCircuit.deviceId}-${currentModalCircuit.circuitId}`;
    const data = circuitChartData[circuitKey] || [];
    updateModalDataTable(currentModalCircuit, data);
  } else {
    // Show placeholder data
    updateModalDataTablePlaceholder();
  }
}

function updateModalDataTable(circuit, data) {
  const tableBody = document.querySelector('#readingTable tbody');
  if (!tableBody) return;
  
  // Clear existing data
  tableBody.innerHTML = '';
  
  if (!data || data.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="6" style="text-align: center; padding: 20px;">No data available</td>';
    tableBody.appendChild(tr);
    return;
  }
  
  // Show latest 20 records, reverse order (newest first)
  const recentData = data.slice(-20).reverse();
  
  recentData.forEach(row => {
    const tr = document.createElement('tr');
    
    // Format timestamp
    const timestamp = row.timestamp ? 
      new Date(row.timestamp).toLocaleString() : 
      '--';
    
    // Extract values with fallbacks
    const temperature = formatValue(row.temperature || row.MaxTemp || row.maxtemp, '°C');
    const voltage = formatValue(row.voltage || row.PackVol || row.packvol || row.avgcellvol, 'V');
    const current = formatValue(row.current || row.PackCurr || row.packcurr, 'A');
    const power = formatValue(row.power || row.Power || row.ressocprot, 'W');
    const resistance = formatValue(row.resistance || row.Resistance || row.resstatus, 'Ω');
    
    tr.innerHTML = `
      <td>${timestamp}</td>
      <td>${temperature}</td>
      <td>${voltage}</td>
      <td>${current}</td>
      <td>${power}</td>
      <td>${resistance}</td>
    `;
    tableBody.appendChild(tr);
  });
  
  console.log(`📊 Updated data table with ${recentData.length} records`);
}

function updateModalDataTablePlaceholder() {
  const tableBody = document.querySelector('#readingTable tbody');
  if (!tableBody) return;
  
  // Clear existing data
  tableBody.innerHTML = '';
  
  // Add sample data rows
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

function formatValue(value, unit) {
  if (value === undefined || value === null || value === '') {
    return '--';
  }
  
  const numValue = parseFloat(value);
  if (isNaN(numValue)) {
    return '--';
  }
  
  return `${numValue.toFixed(2)}${unit}`;
}

function updateControlsPanel() {
  
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
  loadmachine1(); // Default to device 1

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
  
  // Demo controls
  const machine1Btn = document.getElementById("Machine1");
  const Machine2Btn = document.getElementById("Machine2");
  const Machine3Btn = document.getElementById("Machine3");
  
  if (machine1Btn) {
    machine1Btn.addEventListener("click", async () => {
      try {
        loadmachine1();
      } catch (error) {
        console.error("❌ Error starting Machine 1 demo:", error);
        alert("Failed to start Machine 1 demo");
      }
    });
  }

  if (Machine2Btn) {
    Machine2Btn.addEventListener("click", async () => {
      try {
        loadmachine2();
      } catch (error) {
        console.error("❌ Error starting Machine 2 demo:", error);
        alert("Failed to start Machine 2 demo");
      }
    });
  }
  
  if (Machine3Btn) {
    Machine3Btn.addEventListener("click", async () => {
      try {
        loadmachine3();
      } catch (error) {
        console.error("❌ Error starting Machine 3 demo:", error);
        alert("Failed to start Machine 3 demo");
      }
    });
  }
});
