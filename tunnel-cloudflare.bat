@echo off
title Cloudflare Tunnel - Life Manager
cd /d "%~dp0"

where cloudflared >nul 2>&1
if errorlevel 1 (
    echo.
    echo  cloudflared is not installed or not in PATH.
    echo.
    echo  Easiest install ^(Windows^):
    echo    winget install --id Cloudflare.cloudflared -e
    echo.
    echo  Or download the .exe from:
    echo    https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    echo    Put cloudflared.exe somewhere in your PATH or in this folder.
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   Life Manager - Cloudflare quick tunnel
echo  ============================================================
echo.
echo  1. In ANOTHER window, start the app with:  start.bat
echo     ^(plain HTTP on port 5000 is fine — the tunnel adds HTTPS^)
echo.
echo  2. Below you will get a https://....trycloudflare.com link
echo     Open THAT link on your phone ^(same Wi-Fi not required^).
echo.
echo  3. On the phone: Home -^> Enable reminders
echo.
echo  The URL changes each time you run this ^(unless you set up a named tunnel^).
echo  Press Ctrl+C to stop the tunnel.
echo.
echo  ============================================================
echo.

cloudflared tunnel --url http://127.0.0.1:5000

pause
