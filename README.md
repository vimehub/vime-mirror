# VimeMirror — Mirror HP ringan untuk laptop

Mirror HP Android ke laptop, dibuat untuk satu syarat: **ringan, ga gampang
ketutup, ga lag.** Mesin mirror memakai [scrcpy](https://github.com/Genymobile/scrcpy)
(Apache-2.0) — jalur video H.264 yang sama dengan yang dipakai VimeStudio.

## Kenapa ringan & stabil

- **Preset default "Ringan"**: 720p, 2 Mbps, 30 fps, tanpa audio. Decode H.264
  hardware, jadi CPU laptop 4 GB tidak keteteran.
- **Watchdog auto-reconnect**: kalau jendela mirror putus (kabel goyang, HP
  tidur, scrcpy crash), VimeMirror menyambungkan ulang sendiri dalam
  2–10 detik. Aplikasi tidak ikut ketutup.
- **Layar HP tetap nyala** (default aktif): mencegah putus karena HP tidur.
- **USB lebih minim lag** daripada WiFi. WiFi tetap tersedia buat yang
  tidak mau pakai kabel.

## Cara pakai (Windows)

1. Download repo ini (Code → Download ZIP), ekstrak.
2. Jalankan **`setup.bat`** sekali saja — download scrcpy 3.3.4 + adb resmi
   ke folder `tools/` (butuh internet).
3. Di HP: aktifkan **USB debugging** (Setelan → Opsi pengembang).
4. Colok HP via USB, jalankan **`JALANKAN.bat`**.
5. Klik **Refresh**, pilih HP, klik **Mulai Mirror**.

Syarat: Python dari [python.org](https://www.python.org/downloads/)
(saat install, centang **"Add python.exe to PATH"**).

## WiFi (opsional)

1. Colok USB dulu, klik **Aktifkan via USB** (menyalakan mode `adb tcpip`).
2. Isi IP HP (lihat di Setelan → Tentang → Status, atau WiFi → detail
   jaringan), klik **Sambungkan**.
3. Kabel boleh dicabut. Catatan: WiFi selalu lebih lag daripada USB.

## Troubleshooting

| Gejala | Periksa |
|---|---|
| HP tidak muncul di Refresh | Kabel (coba port lain), USB debugging, driver HP, popup "Izinkan USB debugging" di HP |
| Mirror menutup sendiri | Itu yang dijaga watchdog: tunggu 2–10 detik, mirror nyambung lagi. Kalau berulang tiap detik, cek kabel/port USB |
| Lag / patah-patah | Pakai preset Ringan + USB. Jangan WiFi kalau mau minim lag |
| Layar HP mati lalu putus | Pastikan opsi "Layar HP tetap nyala" tercentang |
| `setup.bat` gagal | Internet / antivirus memblokir download. Ulangi setup.bat |

## Versi exe satu file

File `vime_mirror.py` bisa dibangun jadi `VimeMirror.exe` satu file lewat
GitHub Actions (`.github/workflows/build-exe.yml`, jalan manual). Build
memakai menit Actions — jalankan saat kuota tersedia.

## Lisensi

Kode VimeMirror bebas dipakai. scrcpy oleh Genymobile, lisensi Apache-2.0.
