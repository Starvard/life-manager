@echo off
title Life Manager (HTTPS for phone push)
cd /d "%~dp0"

set LM_USE_SSL=1

:loop
echo.
echo  Life Manager with HTTPS (needed for Android push reminders).
echo  After it starts, the window MUST print lines starting with https://
echo  If it prints http:// instead, SSL is OFF — do not use https:// on the phone.
echo  On your phone use that exact https:// address (accept the cert warning once).
echo  Press Ctrl+C to stop.
echo.
python app.py
echo.
echo  Server stopped. Restarting in 3 seconds...
echo  (Press Ctrl+C again to exit completely)
timeout /t 3 >nul
goto loop
