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
    socket = io.connect(window.location.origin);

    window.BTSWebSocket.socket = socket;

    console.log("🔌 Connecting to live data stream...");

    socket.on("connect", () => {
      console.log("✅ Connected to live data WebSocket");
    });

    socket.on("disconnect", () => {
      console.warn("⚠️ Disconnected from WebSocket");
    });

    // Receive periodic live updates from backend
    socket.on("live_data", (payload) => {
      try {
        if (!payload) return;
        const data = typeof payload === "string" ? JSON.parse(payload) : payload;
        // Forward to dashboard handler if available
        if (window.BTSWebSocket.onData) {
          window.BTSWebSocket.onData(data);
        }
      } catch (err) {
        console.error("Error parsing live_data:", err);
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
