// Konfigurasi Default
let channelId = localStorage.getItem('av_channel_id') || 'ruang-sidang-utama';
let deviceId = localStorage.getItem('av_device_id');

if (!deviceId) {
  const roles = ['A', 'B', 'C'];
  const randomRole = roles[Math.floor(Math.random() * roles.length)];
  deviceId = `User-${randomRole}-${Math.floor(Math.random() * 900 + 100)}`;
  localStorage.setItem('av_device_id', deviceId);
}

// Elemen DOM
const connectionBadge = document.getElementById('connection-badge');
const connectionText = document.getElementById('connection-text');
const laptopBadge = document.getElementById('laptop-badge');
const laptopText = document.getElementById('laptop-text');
const activeStateTitle = document.getElementById('active-state-title');
const activeStateDesc = document.getElementById('active-state-desc');
const stateIcon = document.getElementById('state-icon');
const btnProfile = document.getElementById('btn-profile');
const btnZoom = document.getElementById('btn-zoom');
const lastUpdated = document.getElementById('last-updated');
const lastOperator = document.getElementById('last-operator');
const deviceIdentity = document.getElementById('device-identity');
const channelInput = document.getElementById('channel-input');
const transitionOverlay = document.getElementById('transition-overlay');
const slideControls = document.getElementById('slide-controls');

deviceIdentity.textContent = deviceId;
channelInput.value = channelId;

// State Sistem
let currentState = 'ZOOM';
let isTransitioning = false;
let lastHeartbeatTime = 0;
let heartbeatChecker = null;

// MQTT Broker Publik Gratis (Over Secure WebSockets WSS)
// Port 8884 adalah standar WSS HiveMQ Cloud Public
const BROKER_URL = 'wss://broker.hivemq.com:8884/mqtt';
let client = null;

function getTopics() {
  return {
    command: `avcontrol/${channelId}/command`,
    status: `avcontrol/${channelId}/status`,
    heartbeat: `avcontrol/${channelId}/heartbeat`
  };
}

function initMQTT() {
  updateConnectionStatus('connecting', 'Menghubungkan ke Cloud...');

  const clientId = `web_${deviceId}_${Date.now().toString(36)}`;
  client = mqtt.connect(BROKER_URL, {
    clientId: clientId,
    clean: true,
    connectTimeout: 5000,
    reconnectPeriod: 2000
  });

  client.on('connect', () => {
    updateConnectionStatus('online', 'Cloud Terhubung');
    const topics = getTopics();
    client.subscribe([topics.status, topics.heartbeat], (err) => {
      if (!err) {
        console.log(`Subscribed ke channel: ${channelId}`);
      }
    });
  });

  client.on('reconnect', () => {
    updateConnectionStatus('connecting', 'Menghubungkan ulang...');
  });

  client.on('offline', () => {
    updateConnectionStatus('offline', 'Cloud Terputus');
  });

  client.on('error', (err) => {
    console.error('MQTT Error:', err);
    updateConnectionStatus('offline', 'Error Koneksi');
  });

  client.on('message', (topic, message) => {
    try {
      const data = JSON.parse(message.toString());
      const topics = getTopics();

      if (topic === topics.heartbeat) {
        handleHeartbeat(data);
      } else if (topic === topics.status) {
        handleStatusUpdate(data);
      }
    } catch (e) {
      console.error('Gagal membaca pesan MQTT:', e);
    }
  });
}

function updateConnectionStatus(status, text) {
  connectionBadge.className = `badge badge-${status}`;
  connectionText.textContent = text;
}

function handleHeartbeat(data) {
  lastHeartbeatTime = Date.now();
  laptopBadge.className = 'badge badge-online';
  laptopText.textContent = 'Laptop C: ONLINE (Aktif)';
}

// Watchdog memeriksa apakah laptop C mati/putus koneksi
function startHeartbeatWatchdog() {
  if (heartbeatChecker) clearInterval(heartbeatChecker);
  heartbeatChecker = setInterval(() => {
    const now = Date.now();
    // Jika tidak ada detak jantung lebih dari 8 detik
    if (now - lastHeartbeatTime > 8000) {
      laptopBadge.className = 'badge badge-offline';
      laptopText.textContent = 'Laptop C: OFFLINE (Terputus)';
    }
  }, 3000);
}

function handleStatusUpdate(data) {
  currentState = data.state;
  lastOperator.textContent = data.operator || 'Sistem';
  updateTimestamp();

  if (currentState === 'PROFILE') {
    activeStateTitle.textContent = 'PROFIL PERUSAHAAN AKTIF';
    activeStateDesc.textContent = 'Audio Zoom dimatikan, Audio Profil diputar di Speaker';
    stateIcon.textContent = '🏢';
    stateIcon.className = 'state-icon profile-icon';
    btnProfile.classList.add('is-active');
    btnZoom.classList.remove('is-active');
    if (slideControls) slideControls.classList.remove('hidden');
  } else {
    activeStateTitle.textContent = 'LIVE ZOOM MEETING';
    activeStateDesc.textContent = 'Layar Zoom aktif, Audio Zoom keluar di Speaker';
    stateIcon.textContent = '👥';
    stateIcon.className = 'state-icon zoom-icon';
    btnZoom.classList.add('is-active');
    btnProfile.classList.remove('is-active');
    if (slideControls) slideControls.classList.add('hidden');
  }

  // Sembunyikan overlay transisi
  hideTransitionOverlay();
}

function triggerState(targetState) {
  if (isTransitioning) return;
  
  // Haptic feedback di smartphone jika didukung
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
    alert('Koneksi internet/cloud belum siap. Coba beberapa saat lagi.');
    hideTransitionOverlay();
  }
}

function showTransitionOverlay() {
  isTransitioning = true;
  transitionOverlay.classList.remove('hidden');

  // Safety timer: hilangkan overlay otomatis setelah 3 detik jika laptop C tidak merespon
  setTimeout(() => {
    hideTransitionOverlay();
  }, 3000);
}

function hideTransitionOverlay() {
  isTransitioning = false;
  transitionOverlay.classList.add('hidden');
}

function updateTimestamp() {
  const d = new Date();
  lastUpdated.textContent = d.toTimeString().split(' ')[0];
}

function updateChannel() {
  const newChannel = channelInput.value.trim();
  if (!newChannel || newChannel === channelId) return;

  // Unsubscribe channel lama
  if (client && client.connected) {
    const oldTopics = getTopics();
    client.unsubscribe([oldTopics.status, oldTopics.heartbeat]);
  }

  channelId = newChannel;
  localStorage.setItem('av_channel_id', channelId);

  // Subscribe channel baru
  if (client && client.connected) {
    const newTopics = getTopics();
    client.subscribe([newTopics.status, newTopics.heartbeat]);
  }

  laptopBadge.className = 'badge badge-pending';
  laptopText.textContent = 'Laptop C: Mencari Sinyal...';
}

// Inisialisasi Aplikasi
initMQTT();
startHeartbeatWatchdog();


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
  }
}
