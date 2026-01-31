/* ============================================================
   BTS Monitoring System — WebSocket (Socket.IO)
   Handles real-time data updates from Flask backend
   ============================================================ */

let socket = null;

// Optional external handler
window.BTSWebSocket = {
  socket: null,
  onData: null,
};

/**
 * Initialize WebSocket connection to Flask-SocketIO backend.
 */
function initWebSocket() {
  try {
    // Connect to current origin (Flask server)
    socket = io.connect("http://127.0.0.1:5001");

    window.BTSWebSocket.socket = socket;

    console.log("🔌 Connecting to live data stream...");

    socket.on("connect", () => {
      console.log("✅ Connected to live data WebSocket");
    });

    socket.on("disconnect", () => {
      console.warn("⚠️ Disconnected from WebSocket");
    });

    socket.on("connect_error", (error) => {
      console.error("❌ WebSocket connection error:", error);
    });

    // Receive periodic live updates from backend
    socket.on("live_data", (payload) => {
      try {
        // Debug: Log the incoming data for debugging
        console.log("📊 Live Data Received:", payload);
        
        if (!payload) {
          console.warn("⚠️ Empty payload received");
          return;
        }
        
        const data = typeof payload === "string" ? JSON.parse(payload) : payload;
        
        // Debug: Log parsed data structure
        // console.log("🔄 Parsed Data:", {
        //   timestamp: data.timestamp,
        //   circuitCount: data.circuits ? data.circuits.length : 0,
        //   circuits: data.circuits
        // });
        
        // Log individual circuit data for debugging
        // if (data.circuits && data.circuits.length > 0) {
        //   data.circuits.forEach((circuit, index) => {
        //   //   console.log(`🔋 Circuit ${index + 1} Data:`, {
        //   //     circuit_id: circuit.circuit_id,
        //   //     file_name: circuit.file_name,
        //   //     temperature: circuit.temperature || circuit.MaxTemp,
        //   //     voltage: circuit.voltage || circuit.PackVol || circuit.avgcellvol,
        //   //     current: circuit.current || circuit.PackCurr,
        //   //     power: circuit.power || circuit.ressocprot,
        //   //     resistance: circuit.resistance || circuit.resstatus,
        //   //     soc: circuit.soc || circuit.SOC,
        //   //     batteryId: circuit.battery_id || circuit.batteryId || 'Unknown',
        //   //     timestamp: circuit.timestamp
        //   //   });
        //   // });
        // }
        
        // Forward to dashboard handler if available
        if (window.BTSWebSocket.onData) {
          window.BTSWebSocket.onData(data);
        } else {
          console.warn("⚠️ No dashboard handler registered");
        }
        
      } catch (err) {
        console.error("❌ Error parsing live_data:", err);
        console.error("Raw payload:", payload);
      }
    });

    socket.on("message", (msg) => {
      console.log("ℹ️ WS message:", msg);
    });

  } catch (err) {
    console.error("WebSocket init error:", err);
  }
}

/**
 * Graceful disconnect (optional for page unload)
 */
function closeWebSocket() {
  if (socket && socket.connected) {
    socket.disconnect();
    console.log("🔌 WebSocket disconnected");
  }
}

window.addEventListener("beforeunload", closeWebSocket);

// Auto-init after page load
document.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
});
