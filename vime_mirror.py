#!/usr/bin/env python3
"""VimeMirror - mirror HP Android ringan untuk laptop Windows.

Mesin mirror: scrcpy (Apache-2.0, https://github.com/Genymobile/scrcpy).
Dua hal yang dijaga sesuai permintaan:
  1. RINGAN  -> preset default 720p / 2 Mbps / 30 fps, decode H.264
               hardware, tanpa audio. Cocok untuk laptop 4 GB RAM.
  2. GA CLOSE -> watchdog: kalau jendela mirror putus (kabel goyang,
               HP tidur, scrcpy crash), VimeMirror menyambungkan ulang
               sendiri dengan backoff, tanpa menutup aplikasi.
  3. GA LAG  -> jalur USB + bitrate rendah + H.264. WiFi tersedia tapi
               latensinya selalu lebih tinggi dari USB.

Stdlib only. Tidak perlu pip install.
Jalankan:  JALANKAN.bat  (Windows)  atau  python vime_mirror.py
Setup pertama (download scrcpy + adb resmi):  setup.bat
"""

import os
import queue
import re
import subprocess
import sys
import threading
import time

APP_NAME = "VimeMirror"
SCRCPY_VERSION = "3.3.4"

# Preset kualitas. "Ringan" adalah default untuk laptop spek rendah.
PRESETS = {
    "Ringan": {"max_size": 1280, "bit_rate": "2M", "fps": 30},
    "Seimbang": {"max_size": 1920, "bit_rate": "4M", "fps": 30},
    "Tajam": {"max_size": 1920, "bit_rate": "8M", "fps": 60},
}
PRESET_ORDER = ["Ringan", "Seimbang", "Tajam"]

# Jeda reconnect watchdog (detik): 2, 3, 5, lalu 10 terus.
BACKOFF = [2, 3, 5, 10]


def app_dir():
    if getattr(sys, "frozen", False):
        # Onefile PyInstaller: data bundling (--add-data) ada di _MEIPASS.
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def find_tool(names, subdirs):
    """Cari binary di folder tools/ dulu, fallback ke PATH sistem."""
    base = app_dir()
    ext = ".exe" if os.name == "nt" else ""
    for d in subdirs:
        for n in names:
            p = os.path.join(base, d, n + ext)
            if os.path.isfile(p):
                return p
    return names[0] + ext


def adb_path():
    return find_tool(["adb"], ["tools/platform-tools", "tools"])


def scrcpy_path():
    return find_tool(
        ["scrcpy"],
        ["tools/scrcpy-win64-v3.3.4", "tools/scrcpy-win64", "tools"],
    )


def parse_adb_devices(text):
    """Ambil serial HP yang statusnya 'device' dari output `adb devices`."""
    devs = []
    for line in text.splitlines():
        m = re.match(r"^(\S+)\s+device\s*$", line.strip())
        if m:
            devs.append(m.group(1))
    return devs


def list_devices(adb):
    try:
        out = subprocess.run(
            [adb, "devices"], capture_output=True, text=True, timeout=15
        )
        return parse_adb_devices(out.stdout)
    except Exception:
        return []


def build_scrcpy_args(preset, stay_awake=True, control=True, audio=False):
    """Argumen scrcpy. Hanya flag stabil lintas versi yang dipakai."""
    p = PRESETS[preset]
    args = [
        "--max-size=%d" % p["max_size"],
        "--video-bit-rate=%s" % p["bit_rate"],
        "--max-fps=%d" % p["fps"],
        "--video-codec=h264",
        "--window-title=%s" % APP_NAME,
    ]
    if stay_awake:
        args.append("--stay-awake")
    if not control:
        args.append("--no-control")
    if not audio:
        args.append("--no-audio")
    return args


class MirrorController:
    """Menjalankan scrcpy + watchdog reconnect. Tanpa dependensi GUI."""

    def __init__(self, binary, args, serial, on_event):
        self.binary = binary
        self.args = args
        self.serial = serial
        self.on_event = on_event
        self.running = False
        self.proc = None
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        proc = self.proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.proc = None

    def _loop(self):
        attempt = 0
        while self.running:
            env = dict(os.environ)
            if self.serial:
                # Cara resmi memilih device di scrcpy lintas versi.
                env["ANDROID_SERIAL"] = self.serial
            try:
                proc = subprocess.Popen(
                    [self.binary] + self.args,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as e:
                self.on_event(
                    "error",
                    "Gagal menjalankan mirror (%s). Jalankan setup.bat dulu."
                    % e,
                )
                self.running = False
                return
            self.proc = proc
            if attempt == 0:
                self.on_event("started", "Mirror jalan.")
            else:
                self.on_event("reconnected", "Mirror tersambung lagi.")
            proc.wait()
            self.proc = None
            if not self.running:
                break
            attempt += 1
            wait = BACKOFF[min(attempt - 1, len(BACKOFF) - 1)]
            self.on_event(
                "dropped",
                "Mirror putus, sambung ulang #%d dalam %ds..."
                % (attempt, wait),
            )
            # Tidur per 0.1 detik supaya stop() langsung responsif.
            for _ in range(wait * 10):
                if not self.running:
                    break
                time.sleep(0.1)


# ---------------------------------------------------------------- GUI ------
# GUI dipisah dari controller supaya logika bisa diuji tanpa jendela.


def run_gui():
    import tkinter as tk
    from tkinter import ttk

    events = queue.Queue()
    state = {"controller": None, "devices": []}

    root = tk.Tk()
    root.title(APP_NAME + " - Mirror HP ringan")
    root.geometry("470x580")
    root.resizable(False, False)

    def log(msg):
        log_box.configure(state="normal")
        log_box.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
        lines = log_box.get("1.0", "end").splitlines()
        if len(lines) > 300:
            log_box.delete("1.0", "%d.0" % (len(lines) - 300))
        log_box.configure(state="disabled")
        log_box.see("end")

    def set_status(msg):
        status_var.set(msg)

    def refresh_devices():
        def work():
            devs = list_devices(adb_path())
            events.put(("devices", devs))

        threading.Thread(target=work, daemon=True).start()

    def on_devices(devs):
        state["devices"] = devs
        device_combo["values"] = devs if devs else ["(tidak ada HP terdeteksi)"]
        if devs:
            device_combo.current(0)
            set_status("%d HP terdeteksi" % len(devs))
            log("HP terdeteksi: " + ", ".join(devs))
        else:
            device_combo.current(0)
            set_status("Tidak ada HP. Colok USB + aktifkan USB debugging.")
            log("Tidak ada HP terdeteksi. Cek kabel, port USB, dan USB debugging.")

    def start_mirror():
        serial = device_combo.get()
        if not serial or serial.startswith("("):
            set_status("Pilih HP dulu (tombol Refresh).")
            return
        args = build_scrcpy_args(
            preset_var.get(),
            stay_awake=stay_var.get(),
            control=control_var.get(),
            audio=audio_var.get(),
        )
        ctl = MirrorController(
            scrcpy_path(), args, serial,
            lambda kind, msg: events.put((kind, msg)),
        )
        state["controller"] = ctl
        log("Mulai mirror: %s (preset %s)" % (serial, preset_var.get()))
        set_status("Menghubungkan...")
        start_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        ctl.start()

    def stop_mirror():
        ctl = state["controller"]
        if ctl is not None:
            ctl.stop()
            state["controller"] = None
        start_btn.configure(state="normal")
        stop_btn.configure(state="disabled")
        set_status("Mirror berhenti.")
        log("Mirror dihentikan.")

    def wifi_connect():
        ip = wifi_entry.get().strip()
        if not ip:
            set_status("Isi IP HP dulu (contoh: 192.168.1.5).")
            return

        def work():
            try:
                out = subprocess.run(
                    [adb_path(), "connect", ip + ":5555"],
                    capture_output=True, text=True, timeout=20,
                )
                events.put(("log", (out.stdout + out.stderr).strip()))
            except Exception as e:
                events.put(("log", "Gagal sambung WiFi: %s" % e))

        threading.Thread(target=work, daemon=True).start()
        set_status("Menghubungkan WiFi ke %s..." % ip)

    def wifi_enable_usb():
        serial = device_combo.get()
        if not serial or serial.startswith("("):
            set_status("Pilih HP dulu (tombol Refresh).")
            return

        def work():
            try:
                out = subprocess.run(
                    [adb_path(), "-s", serial, "tcpip", "5555"],
                    capture_output=True, text=True, timeout=20,
                )
                events.put(("log", (out.stdout + out.stderr).strip()))
                events.put(("log", "Sekarang isi IP HP lalu Sambungkan WiFi."))
            except Exception as e:
                events.put(("log", "Gagal aktifkan WiFi: %s" % e))

        threading.Thread(target=work, daemon=True).start()
        set_status("Mengaktifkan mode WiFi via USB...")

    def on_close():
        stop_mirror()
        root.destroy()

    # -- layout --
    pad = {"padx": 10, "pady": 4}
    ttk.Label(root, text=APP_NAME, font=("", 16, "bold")).pack(**pad)
    ttk.Label(
        root,
        text="Mirror HP ringan: putus = sambung otomatis, tanpa lag.",
    ).pack(**pad)

    frame = ttk.LabelFrame(root, text="HP")
    frame.pack(fill="x", **pad)
    device_combo = ttk.Combobox(frame, state="readonly", width=40)
    device_combo.pack(side="left", padx=6, pady=6)
    ttk.Button(frame, text="Refresh", command=refresh_devices).pack(
        side="left", padx=6, pady=6
    )

    frame = ttk.LabelFrame(root, text="Kualitas (default: Ringan, buat laptop 4 GB)")
    frame.pack(fill="x", **pad)
    preset_var = tk.StringVar(value="Ringan")
    for name in PRESET_ORDER:
        p = PRESETS[name]
        ttk.Radiobutton(
            frame,
            text="%s - %dp, %s, %d fps"
            % (name, p["max_size"], p["bit_rate"], p["fps"]),
            variable=preset_var, value=name,
        ).pack(anchor="w", padx=6)

    frame = ttk.LabelFrame(root, text="Opsi")
    frame.pack(fill="x", **pad)
    stay_var = tk.BooleanVar(value=True)
    control_var = tk.BooleanVar(value=True)
    audio_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        frame, text="Layar HP tetap nyala saat mirror (cegah putus)",
        variable=stay_var).pack(anchor="w", padx=6)
    ttk.Checkbutton(
        frame, text="Kontrol mouse + keyboard dari laptop",
        variable=control_var).pack(anchor="w", padx=6)
    ttk.Checkbutton(frame, text="Suara HP ikut ke laptop",
                     variable=audio_var).pack(anchor="w", padx=6)

    frame = ttk.LabelFrame(root, text="WiFi (opsional, USB lebih minim lag)")
    frame.pack(fill="x", **pad)
    wifi_entry = ttk.Entry(frame, width=20)
    wifi_entry.pack(side="left", padx=6, pady=6)
    wifi_entry.insert(0, "192.168.1.5")
    ttk.Button(frame, text="Sambungkan", command=wifi_connect).pack(
        side="left", padx=6, pady=6
    )
    ttk.Button(frame, text="Aktifkan via USB", command=wifi_enable_usb).pack(
        side="left", padx=6, pady=6
    )

    btn_row = ttk.Frame(root)
    btn_row.pack(**pad)
    start_btn = ttk.Button(btn_row, text="Mulai Mirror", command=start_mirror)
    start_btn.pack(side="left", padx=6)
    stop_btn = ttk.Button(btn_row, text="Berhenti", command=stop_mirror,
                          state="disabled")
    stop_btn.pack(side="left", padx=6)

    status_var = tk.StringVar(value="Klik Refresh untuk mencari HP.")
    ttk.Label(root, textvariable=status_var, wraplength=440).pack(**pad)

    log_box = tk.Text(root, height=9, state="disabled")
    log_box.pack(fill="both", expand=True, padx=10, pady=6)
    ttk.Label(
        root,
        text="Mesin: scrcpy %s (Apache-2.0) | Watchdog aktif" % SCRCPY_VERSION,
        font=("", 8),
    ).pack(pady=2)

    # Satu loop pompa event untuk semua pesan antar-thread.
    def pump_single():
        try:
            while True:
                kind, msg = events.get_nowait()
                if kind == "devices":
                    on_devices(msg)
                elif kind == "log":
                    log(msg)
                elif kind == "started":
                    set_status("Mirror jalan")
                    start_btn.configure(state="disabled")
                    stop_btn.configure(state="normal")
                    log(msg)
                elif kind == "reconnected":
                    set_status("Mirror tersambung lagi")
                    log(msg)
                elif kind == "dropped":
                    set_status(msg)
                    log(msg)
                elif kind == "error":
                    set_status(msg)
                    start_btn.configure(state="normal")
                    stop_btn.configure(state="disabled")
                    log(msg)
        except queue.Empty:
            pass
        root.after(200, pump_single)

    root.protocol("WM_DELETE_WINDOW", on_close)
    refresh_devices()
    root.after(200, pump_single)
    root.mainloop()


def main():
    run_gui()


if __name__ == "__main__":
    main()
