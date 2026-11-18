@echo off
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
echo CV booth: http://127.0.0.1:8765
echo Close this window to stop.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8765"
uv run --frozen python booth/server.py
pause
