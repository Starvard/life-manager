@echo off
title Life Manager
cd /d "%~dp0"
rem For Android push reminders over HTTPS, run start-with-push.bat instead.
rem On THIS PC, Chrome push works best at http://127.0.0.1:5000 (this file—no SSL).

:loop
echo.
echo  Starting Life Manager...
echo  For push on this computer: open http://127.0.0.1:5000 in Chrome (not https://192.168...).
echo  Press Ctrl+C to stop.
echo.
python app.py
echo.
echo  Server stopped. Restarting in 3 seconds...
echo  (Press Ctrl+C again to exit completely)
timeout /t 3 >nul
goto loop
