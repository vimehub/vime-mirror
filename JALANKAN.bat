@echo off
REM VimeMirror - jalankan aplikasi (butuh Python dari python.org).
REM Kalau Python belum terinstal, download di https://www.python.org/downloads/
REM (centang "Add python.exe to PATH" saat install).
cd /d "%~dp0"
py -3 vime_mirror.py 2>nul
if errorlevel 1 python vime_mirror.py 2>nul
if errorlevel 1 (
  echo.
  echo Python tidak ditemukan. Install dulu dari https://www.python.org/downloads/
  echo (saat install, centang "Add python.exe to PATH").
  pause
)
