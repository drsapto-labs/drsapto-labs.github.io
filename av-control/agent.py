"""
AV Master Control - Windows 11 Desktop Agent
============================================
Otomasi kendali layar dan audio terpadu:
- Mute/Unmute audio Zoom via Windows Core Audio API (WASAPI)
- Pemutaran video profil perusahaan Fullscreen Kiosk Mode
- Floating Mini-Widget untuk Si C di laptop
- Hotkey Darurat Offline (F9 & F10)
- Anti-Sleep & Anti-Lock Screen Windows 11
- Sinkronisasi Cloud MQTT Realtime Gratis (HiveMQ Broker)
"""

import os
import sys
import time
import json
import threading
import subprocess
import ctypes
from pathlib import Path

# Coba import paho-mqtt
try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[ERROR] Paho-MQTT belum terinstal. Jalankan 'install.bat' terlebih dahulu.")
    sys.exit(1)

# Coba import pycaw untuk kontrol volume spesifik Zoom
HAS_PYCAW = False
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

# Coba import keyboard untuk hotkey global
HAS_KEYBOARD = False
try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False

# Import GUI Tkinter bawaan Python untuk Floating Widget
import tkinter as tk
from tkinter import ttk

# ==========================================
# KONFIGURASI SISTEM
# ==========================================
CHANNEL_ID = "ruang-sidang-utama"
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_COMMAND = f"avcontrol/{CHANNEL_ID}/command"
TOPIC_STATUS = f"avcontrol/{CHANNEL_ID}/status"
TOPIC_HEARTBEAT = f"avcontrol/{CHANNEL_ID}/heartbeat"

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
PLAYER_HTML = BASE_DIR / "player.html"

# Windows API Constants untuk Anti-Sleep
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class WindowsAVAgent:
    def __init__(self):
        self.current_state = "ZOOM"
        self.kiosk_process = None
        self.mqtt_client = None
        self.is_running = True
        self.widget_root = None

        # Aktifkan Anti-Sleep Windows 11
        self.prevent_windows_sleep()

        # Inisialisasi MQTT
        self.setup_mqtt()

        # Mulai background thread untuk Heartbeat
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        # Siapkan Hotkey Darurat Offline
        self.setup_hotkeys()

    def prevent_windows_sleep(self):
        """Mencegah Windows 11 mati layar atau masuk lock screen saat si C tertidur/pergi"""
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            print("[SISTEM] Windows 11 Anti-Sleep Aktif: Layar tidak akan pernah mati.")
        except Exception as e:
            print(f"[WARNING] Gagal mengaktifkan anti-sleep: {e}")

    # ------------------------------------------------------------------
    # MANAJEMEN AUDIO (WASAPI / NIRCMD)
    # ------------------------------------------------------------------
    def set_zoom_audio_mute(self, mute: bool):
        """
        Mematikan atau menghidupkan kembali suara khusus aplikasi Zoom.exe
        tanpa mengganggu suara master Windows.
        """
        state_str = "MUTE (Senyap)" if mute else "UNMUTE (Aktif Normal)"
        print(f"[AUDIO] Mengatur suara Zoom meeting ke: {state_str}")

        # Metode 1: Menggunakan PyCaw (Windows WASAPI murni)
        if HAS_PYCAW:
            try:
                sessions = AudioUtilities.GetAllSessions()
                found = False
                for session in sessions:
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    if session.Process and session.Process.name().lower() in ["zoom.exe", "cpthost.exe", "airhost.exe"]:
                        volume.SetMute(1 if mute else 0, None)
                        found = True
                if found:
                    return
            except Exception as e:
                print(f"[WARNING] PyCaw audio session error: {e}")

        # Metode 2: NirCmd Fallback jika tersedia di folder
        nircmd_path = BASE_DIR / "nircmd.exe"
        if nircmd_path.exists():
            cmd = f'"{nircmd_path}" muteappvolume Zoom.exe {1 if mute else 0}'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return

        # Metode 3: PowerShell Script Fallback
        ps_mute_code = f"""
        $z = Get-Process -Name Zoom -ErrorAction SilentlyContinue
        """
        # (Jika pycaw dan nircmd tidak ada, print notice)
        if not HAS_PYCAW and not nircmd_path.exists():
            print("[INFO] Jalankan 'install.bat' untuk mengaktifkan pycaw audio isolator.")

    # ------------------------------------------------------------------
    # MANAJEMEN TAMPILAN LAYAR (VIDEO PROFIL / ZOOM)
    # ------------------------------------------------------------------
    def show_profile(self, operator_name="Si A / Si B"):
        if self.current_state == "PROFILE":
            return
        
        print(f"\n[AKSI] >>> MENAMPILKAN PROFIL PERUSAHAAN (Dipicu oleh: {operator_name}) <<<")
        self.current_state = "PROFILE"

        # 1. Matikan suara Zoom seketika
        self.set_zoom_audio_mute(True)

        # 2. Buka Pemutar Fullscreen Kiosk Mode (Edge Kiosk - Bawaan Windows 11)
        pdf_file = MEDIA_DIR / "profil_perusahaan.pdf"
        video_file = MEDIA_DIR / "profil_perusahaan.mp4"

        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if not Path(edge_path).exists():
            edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

        try:
            # Tutup proses kiosk lama jika ada
            if self.kiosk_process and self.kiosk_process.poll() is None:
                self.kiosk_process.kill()

            # Prioritas 1: Jika ada file PDF (Slide Deck Canva / Dokumen)
            if pdf_file.exists():
                target_url = f"file:///{pdf_file.as_posix()}"
                cmd = f'"{edge_path}" --kiosk "{target_url}" --edge-kiosk-type=fullscreen --no-first-run'
                self.kiosk_process = subprocess.Popen(cmd, shell=True)
                print(f"[LAYAR] Dokumen PDF Profil ({pdf_file.name}) berhasil dibuka Fullscreen.")
            elif video_file.exists():
                target_url = f"file:///{PLAYER_HTML.as_posix()}"
                cmd = f'"{edge_path}" --kiosk "{target_url}" --edge-kiosk-type=fullscreen --no-first-run --disable-pinch'
                self.kiosk_process = subprocess.Popen(cmd, shell=True)
                print(f"[LAYAR] Video Profil ({video_file.name}) berhasil dibuka Fullscreen.")
            else:
                target_url = f"file:///{PLAYER_HTML.as_posix()}"
                cmd = f'"{edge_path}" --kiosk "{target_url}" --edge-kiosk-type=fullscreen --no-first-run'
                self.kiosk_process = subprocess.Popen(cmd, shell=True)
                print("[LAYAR] Menampilkan slide demo profil bawaan.")
        except Exception as e:
            print(f"[ERROR] Gagal membuka profil: {e}")
            if pdf_file.exists():
                os.startfile(str(pdf_file))
            elif video_file.exists():
                os.startfile(str(video_file))

        # 3. Publikasikan status ke cloud
        self.broadcast_status(operator_name)
        self.update_widget_ui()

    def show_zoom(self, operator_name="Si C"):
        if self.current_state == "ZOOM":
            return
        
        print(f"\n[AKSI] >>> KEMBALI KE ZOOM MEETING (Dipicu oleh: {operator_name}) <<<")
        self.current_state = "ZOOM"

        # 1. Tutup pemutar Kiosk profil
        if self.kiosk_process:
            try:
                # Bunuh proses msedge kiosk yang dibuka
                subprocess.run('taskkill /F /IM msedge.exe', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.kiosk_process = None
            except Exception as e:
                print(f"[WARNING] Gagal menutup pemutar: {e}")

        # 2. Hidupkan kembali suara Zoom meeting
        self.set_zoom_audio_mute(False)

        # 3. Kembalikan fokus ke jendela Zoom
        self.bring_zoom_to_front()

        # 4. Publikasikan status ke cloud
        self.broadcast_status(operator_name)
        self.update_widget_ui()

    def bring_zoom_to_front(self):
        """Membawa jendela Zoom meeting kembali ke tampilan depan teratas"""
        try:
            import win32gui
            import win32con

            def enum_handler(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Zoom Meeting" in title or "Zoom Workplace" in title:
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                        win32gui.SetForegroundWindow(hwnd)

            win32gui.EnumWindows(enum_handler, None)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # JALUR KOMUNIKASI CLOUD MQTT REALTIME
    # ------------------------------------------------------------------
    def setup_mqtt(self):
        client_id = f"agent_laptop_c_{int(time.time())}"
        try:
            if hasattr(mqtt, "CallbackAPIVersion"):
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id, clean_session=True)
            else:
                self.mqtt_client = mqtt.Client(client_id=client_id, clean_session=True)
        except Exception:
            try:
                self.mqtt_client = mqtt.Client(client_id=client_id)
            except Exception as e:
                print(f"[ERROR] Inisialisasi client gagal: {e}")

        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect

        brokers = [
            ("broker.hivemq.com", 1883),
            ("broker.emqx.io", 1883)
        ]
        connected = False
        for host, port in brokers:
            try:
                print(f"[CLOUD] Menghubungkan ke Broker MQTT: {host}:{port}...")
                self.mqtt_client.connect(host, port, keepalive=60)
                self.mqtt_client.loop_start()
                connected = True
                print(f"[CLOUD] Terhubung ke {host}!")
                break
            except Exception as e:
                print(f"[WARNING] Gagal terhubung ke {host}:{port}: {e}")

        if not connected:
            print("[ERROR] Tidak dapat terhubung ke broker MQTT. Periksa koneksi internet Anda.")

    def on_mqtt_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            print(f"[CLOUD] Berhasil Terhubung! Berlangganan ke topik perintah: {TOPIC_COMMAND}")
            client.subscribe(TOPIC_COMMAND, qos=1)
            self.broadcast_status("Inisialisasi Sistem")
        else:
            print(f"[ERROR] Koneksi MQTT ditolak dengan kode: {rc}")

    def on_mqtt_disconnect(self, client, userdata, rc, *args):
        if rc != 0:
            print(f"[CLOUD] Koneksi MQTT terputus (kode: {rc}). Sistem otomatis mencoba menghubungkan ulang...")

    def next_slide(self):
        """Kirim tombol Right Arrow / Page Down ke layar PDF"""
        try:
            # VK_RIGHT = 0x27
            ctypes.windll.user32.keybd_event(0x27, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x27, 0, 2, 0) # KEYEVENTF_KEYUP
            print("[NAVIGASI] Pindah ke Halaman / Slide Berikutnya (Next) ➡️")
        except Exception as e:
            print(f"[WARNING] Gagal navigasi slide: {e}")

    def prev_slide(self):
        """Kirim tombol Left Arrow / Page Up ke layar PDF"""
        try:
            # VK_LEFT = 0x25
            ctypes.windll.user32.keybd_event(0x25, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x25, 0, 2, 0) # KEYEVENTF_KEYUP
            print("[NAVIGASI] Pindah ke Halaman / Slide Sebelumnya (Prev) ⬅️")
        except Exception as e:
            print(f"[WARNING] Gagal navigasi slide: {e}")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            target = payload.get("target")
            operator = payload.get("operator", "Pengendali Remote")

            if target == "PROFILE":
                self.show_profile(operator)
            elif target == "ZOOM":
                self.show_zoom(operator)
            elif target == "NEXT_SLIDE":
                self.next_slide()
            elif target == "PREV_SLIDE":
                self.prev_slide()
        except Exception as e:
            print(f"[ERROR] Format perintah salah: {e}")

    def broadcast_status(self, operator):
        if self.mqtt_client and self.mqtt_client.is_connected():
            data = {
                "state": self.current_state,
                "operator": operator,
                "timestamp": int(time.time() * 1000)
            }
            self.mqtt_client.publish(TOPIC_STATUS, json.dumps(data), qos=1)

    def heartbeat_loop(self):
        """Mengirim detak jantung berkala tiap 3 detik agar Web tahu laptop C aktif"""
        while self.is_running:
            if self.mqtt_client and self.mqtt_client.is_connected():
                hb = {"agent": "Windows 11 Laptop C", "status": "ONLINE", "time": time.time()}
                self.mqtt_client.publish(TOPIC_HEARTBEAT, json.dumps(hb), qos=0)
            time.sleep(3)

    # ------------------------------------------------------------------
    # HOTKEY DARURAT OFFLINE (UNTUK SI C)
    # ------------------------------------------------------------------
    def setup_hotkeys(self):
        if HAS_KEYBOARD:
            try:
                keyboard.add_hotkey('F9', lambda: self.show_profile("Si C (Hotkey F9)"))
                keyboard.add_hotkey('F10', lambda: self.show_zoom("Si C (Hotkey F10)"))
                print("[HOTKEY] Tombol Darurat Keyboard Aktif: F9 = Profil | F10 = Zoom")
            except Exception as e:
                print(f"[WARNING] Gagal mendaftarkan hotkey: {e}")

    # ------------------------------------------------------------------
    # FLOATING MINI WIDGET (TAMPILAN RINGAN UNTUK SI C DI LAPTOP)
    # ------------------------------------------------------------------
    def create_floating_widget(self):
        root = tk.Tk()
        self.widget_root = root
        root.title("AV Bar")
        
        # Posisi di pojok kanan bawah layar laptop
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        w, h = 310, 60
        x = screen_width - w - 20
        y = screen_height - h - 70
        root.geometry(f"{w}x{h}+{x}+{y}")
        
        root.attributes("-topmost", True)
        root.overrideredirect(True) # Hilangkan bingkai jendela agar ramping
        root.configure(bg="#0f172a")

        # Frame Kontainer
        frame = tk.Frame(root, bg="#0f172a", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Status Label Kecil
        self.lbl_status = tk.Label(frame, text="● LIVE ZOOM", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a")
        self.lbl_status.pack(side="top", pady=2)

        # Tombol Bar
        btn_frame = tk.Frame(frame, bg="#0f172a")
        btn_frame.pack(side="bottom", fill="x", padx=4, pady=2)

        btn_prev = tk.Button(btn_frame, text="◀", font=("Segoe UI", 8, "bold"), bg="#334155", fg="white",
                             activebackground="#475569", bd=0, padx=6, pady=2, cursor="hand2",
                             command=self.prev_slide)
        btn_prev.pack(side="left", padx=1)

        btn_prof = tk.Button(btn_frame, text="🏢 Profil", font=("Segoe UI", 9, "bold"), bg="#10b981", fg="white", 
                             activebackground="#059669", bd=0, padx=6, pady=2, cursor="hand2",
                             command=lambda: self.show_profile("Si C (Widget)"))
        btn_prof.pack(side="left", expand=True, fill="x", padx=1)

        btn_zm = tk.Button(btn_frame, text="👥 Zoom", font=("Segoe UI", 9, "bold"), bg="#2563eb", fg="white",
                           activebackground="#1d4ed8", bd=0, padx=6, pady=2, cursor="hand2",
                           command=lambda: self.show_zoom("Si C (Widget)"))
        btn_zm.pack(side="left", expand=True, fill="x", padx=1)

        btn_next = tk.Button(btn_frame, text="▶", font=("Segoe UI", 8, "bold"), bg="#334155", fg="white",
                             activebackground="#475569", bd=0, padx=6, pady=2, cursor="hand2",
                             command=self.next_slide)
        btn_next.pack(side="right", padx=1)

        # Fitur drag widget kemana saja
        def start_move(event):
            root.x = event.x
            root.y = event.y

        def do_move(event):
            deltax = event.x - root.x
            deltay = event.y - root.y
            new_x = root.winfo_x() + deltax
            new_y = root.winfo_y() + deltay
            root.geometry(f"+{new_x}+{new_y}")

        frame.bind("<ButtonPress-1>", start_move)
        frame.bind("<B1-Motion>", do_move)

        root.mainloop()

    def update_widget_ui(self):
        if self.widget_root and hasattr(self, 'lbl_status'):
            if self.current_state == "PROFILE":
                self.lbl_status.config(text="● PROFIL AKTIF (ZOOM MUTE)", fg="#34d399")
            else:
                self.lbl_status.config(text="● LIVE ZOOM MEETING", fg="#38bdf8")

# ==========================================
# ENTRY POINT UTAMA
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("  AV MASTER CONTROL - WINDOWS 11 AGENT BERJALAN")
    print("=" * 60)
    print(f"Channel ID: {CHANNEL_ID}")
    print("Tekan Ctrl+C di terminal ini jika ingin mematikan sistem.\n")

    agent = WindowsAVAgent()
    
    # Jalankan floating widget di main thread
    agent.create_floating_widget()
