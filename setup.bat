@echo off
REM ============================================================
REM  VimeMirror - setup pertama (sekali saja)
REM  Download scrcpy 3.3.4 + Android platform-tools RESMI,
REM  lalu ekstrak ke folder tools/.
REM  Sumber:
REM   - https://github.com/Genymobile/scrcpy/releases/tag/v3.3.4
REM   - https://developer.android.com/tools/releases/platform-tools
REM ============================================================
setlocal
cd /d "%~dp0"
if not exist tools mkdir tools

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
  "Invoke-WebRequest -Uri 'https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-win64-v3.3.4.zip' -OutFile 'tools\scrcpy.zip'; " ^
  "Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile 'tools\platform-tools.zip'; " ^
  "Expand-Archive -Force 'tools\scrcpy.zip' -DestinationPath 'tools'; " ^
  "Expand-Archive -Force 'tools\platform-tools.zip' -DestinationPath 'tools'; " ^
  "Remove-Item 'tools\scrcpy.zip','tools\platform-tools.zip'"

if exist "tools\scrcpy-win64-v3.3.4\scrcpy.exe" (
  echo [OK] scrcpy terpasang.
) else (
  echo [GAGAL] scrcpy tidak ditemukan. Cek koneksi internet lalu jalankan setup.bat lagi.
  pause
  exit /b 1
)
if exist "tools\platform-tools\adb.exe" (
  echo [OK] adb terpasang.
) else (
  echo [GAGAL] adb tidak ditemukan. Cek koneksi internet lalu jalankan setup.bat lagi.
  pause
  exit /b 1
)
echo.
echo Setup selesai. Jalankan JALANKAN.bat untuk membuka VimeMirror.
pause
