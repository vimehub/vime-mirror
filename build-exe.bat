@echo off
REM Build VimeMirror.exe satu file (scrcpy+adb ikut tertanam bila tools/ ada).
REM Syarat: Python + pip. Jalankan setup.bat dulu supaya tools/ terisi.
cd /d "%~dp0"
set ADD=
if exist "tools\scrcpy-win64-v3.3.4\scrcpy.exe" set ADD=%ADD% --add-data "tools\scrcpy-win64-v3.3.4;tools/scrcpy-win64-v3.3.4"
if exist "tools\platform-tools\adb.exe" set ADD=%ADD% --add-data "tools\platform-tools;tools/platform-tools"
py -3 -m pip install --upgrade pyinstaller 2>nul || python -m pip install --upgrade pyinstaller
py -3 -m PyInstaller --onefile --windowed --name VimeMirror %ADD% vime_mirror.py 2>nul || python -m PyInstaller --onefile --windowed --name VimeMirror %ADD% vime_mirror.py
echo.
echo Selesai. File exe ada di dist\VimeMirror.exe
if "%ADD%"=="" echo (PERHATIAN: tools/ kosong, exe ini butuh folder tools\ di sampingnya. Jalankan setup.bat dulu lalu build ulang.)
pause
