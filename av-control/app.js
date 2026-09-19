// Konfigurasi Default
let channelId = localStorage.getItem("av_channel_id") || "ruang-sidang-utama";
let deviceId = localStorage.getItem("av_device_id");

if (!deviceId) {
  const roles = ["A", "B", "C"];
  const randomRole = roles[Math.floor(Math.random() * roles.length)];
  deviceId = "User-" + randomRole + "-" + Math.floor(Math.random() * 900 + 100);
  localStorage.setItem("av_device_id", deviceId);
}

// Elemen DOM
const connectionBadge = document.getElementById("connection-badge");
const connectionText = document.getElementById("connection-text");
const laptopBadge = document.getElementById("laptop-badge");
const laptopText = document.getElementById("laptop-text");
const activeStateTitle = document.getElementById("active-state-title");
const activeStateDesc = document.getElementById("active-state-desc");
const stateIcon = document.getElementById("state-icon");
const btnProfile = document.getElementById("btn-profile");
const btnZoom = document.getElementById("btn-zoom");
const lastUpdated = document.getElementById("last-updated");
const lastOperator = document.getElementById("last-operator");
const deviceIdentity = document.getElementById("device-identity");
const channelInput = document.getElementById("channel-input");
const transitionOverlay = document.getElementById("transition-overlay");
const slideControls = document.getElementById("slide-controls");

deviceIdentity.textContent = deviceId;
channelInput.value = channelId;

// State Sistem
let currentState = "ZOOM";
let isTransitioning = false;
let lastHeartbeatTime = 0;
let heartbeatChecker = null;

// Multi-Broker Auto-Failover (HiveMQ + EMQX)
const BROKER_URLS = [
  "wss://broker.emqx.io:8084/mqtt",
  "wss://broker.hivemq.com:8884/mqtt"
];
let currentBrokerIndex = 0;
let client = null;
let connectRetryCount = 0;

function getTopics() {
  return {
    command: "avcontrol/" + channelId + "/command",
    status: "avcontrol/" + channelId + "/status",
    heartbeat: "avcontrol/" + channelId + "/heartbeat"
  };
}

function initMQTT() {
  const currentBroker = BROKER_URLS[currentBrokerIndex];
  updateConnectionStatus("connecting", "Menghubungkan ke Cloud...");

  const clientId = "web_" + deviceId + "_" + Date.now().toString(36);
  
  try {
    if (client) {
      client.end(true);
    }
  } catch(e) {}

  client = mqtt.connect(currentBroker, {
    clientId: clientId,
    clean: true,
    connectTimeout: 6000,
    reconnectPeriod: 3000
  });

  client.on("connect", () => {
    connectRetryCount = 0;
    updateConnectionStatus("online", "Cloud Terhubung (EMQX)");
    const topics = getTopics();
    client.subscribe([topics.status, topics.heartbeat], (err) => {
      if (!err) {
        console.log("Subscribed ke channel: " + channelId + " via " + currentBroker);
      }
    });
  });

  client.on("reconnect", () => {
    updateConnectionStatus("connecting", "Menghubungkan ulang...");
  });

  client.on("offline", () => {
    updateConnectionStatus("offline", "Cloud Terputus");
  });

  client.on("error", (err) => {
    console.error("MQTT Error pada broker:", currentBroker, err);
    connectRetryCount++;
    if (connectRetryCount > 2) {
      connectRetryCount = 0;
      currentBrokerIndex = (currentBrokerIndex + 1) % BROKER_URLS.length;
      console.log("Beralih ke broker cadangan:", BROKER_URLS[currentBrokerIndex]);
      setTimeout(initMQTT, 1000);
    } else {
      updateConnectionStatus("offline", "Error Koneksi");
    }
  });

  client.on("message", (topic, message) => {
    try {
      const data = JSON.parse(message.toString());
      const topics = getTopics();

      if (topic === topics.heartbeat) {
        handleHeartbeat(data);
      } else if (topic === topics.status) {
        handleStatusUpdate(data);
      }
    } catch (e) {
      console.error("Gagal membaca pesan MQTT:", e);
    }
  });
}

function updateConnectionStatus(status, text) {
  connectionBadge.className = "badge badge-" + status;
  connectionText.textContent = text;
}

function handleHeartbeat(data) {
  lastHeartbeatTime = Date.now();
  laptopBadge.className = "badge badge-online";
  const agentName = data.agent || data.device || "Laptop C";
  laptopText.textContent = `${agentName}: ONLINE (Aktif)`;
}

// Watchdog memeriksa apakah laptop C mati/putus koneksi
function startHeartbeatWatchdog() {
  if (heartbeatChecker) clearInterval(heartbeatChecker);
  heartbeatChecker = setInterval(() => {
    const now = Date.now();
    if (now - lastHeartbeatTime > 8000) {
      laptopBadge.className = "badge badge-offline";
      laptopText.textContent = "Laptop C: OFFLINE (Terputus)";
    }
  }, 3000);
}

function handleStatusUpdate(data) {
  currentState = data.state;
  lastOperator.textContent = data.operator || "Sistem";
  updateTimestamp();

  if (currentState === "PROFILE") {
    activeStateTitle.textContent = "PROFIL PERUSAHAAN AKTIF";
    activeStateDesc.textContent = "Audio Zoom dimatikan, Dokumen Profil tampil di Layar";
    stateIcon.textContent = "🏢";
    stateIcon.className = "state-icon profile-icon";
    btnProfile.classList.add("is-active");
    btnZoom.classList.remove("is-active");
    if (slideControls) slideControls.classList.remove("hidden");
  } else {
    activeStateTitle.textContent = "LIVE ZOOM MEETING";
    activeStateDesc.textContent = "Layar Zoom aktif, Audio Zoom keluar di Speaker";
    stateIcon.textContent = "👥";
    stateIcon.className = "state-icon zoom-icon";
    btnZoom.classList.add("is-active");
    btnProfile.classList.remove("is-active");
    if (slideControls) slideControls.classList.add("hidden");
  }

  hideTransitionOverlay();
}

function triggerState(targetState) {
  if (isTransitioning) return;
  
  if (navigator.vibrate) {
    navigator.vibrate(50);
  }

  showTransitionOverlay();

  const payload = {
    target: targetState,
    operator: deviceId,
    timestamp: Date.now()
  };

  const topics = getTopics();
  if (client && client.connected) {
    client.publish(topics.command, JSON.stringify(payload), { qos: 1 });
  } else {
    alert("Koneksi internet/cloud belum siap. Coba beberapa saat lagi.");
    hideTransitionOverlay();
  }
}

function triggerSlideNav(direction) {
  if (navigator.vibrate) {
    navigator.vibrate(30);
  }
  const payload = {
    target: direction,
    operator: deviceId,
    timestamp: Date.now()
  };
  const topics = getTopics();
  if (client && client.connected) {
    client.publish(topics.command, JSON.stringify(payload), { qos: 1 });
    console.log("Kirim perintah navigasi slide:", direction);
  }
}

function showTransitionOverlay() {
  isTransitioning = true;
  transitionOverlay.classList.remove("hidden");

  setTimeout(() => {
    hideTransitionOverlay();
  }, 3000);
}

function hideTransitionOverlay() {
  isTransitioning = false;
  transitionOverlay.classList.add("hidden");
}

function updateTimestamp() {
  const d = new Date();
  lastUpdated.textContent = d.toTimeString().split(" ")[0];
}

function updateChannel() {
  const newChannel = channelInput.value.trim();
  if (!newChannel || newChannel === channelId) return;

  if (client && client.connected) {
    const oldTopics = getTopics();
    client.unsubscribe([oldTopics.status, oldTopics.heartbeat]);
  }

  channelId = newChannel;
  localStorage.setItem("av_channel_id", channelId);

  if (client && client.connected) {
    const newTopics = getTopics();
    client.subscribe([newTopics.status, newTopics.heartbeat]);
  }

  laptopBadge.className = "badge badge-pending";
  laptopText.textContent = "Laptop C: Mencari Sinyal...";
}

// Inisialisasi Aplikasi
initMQTT();
startHeartbeatWatchdog();
