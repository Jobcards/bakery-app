@echo off
title Macadams Job Cards server
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed on this PC yet.
  echo Install the LTS version from https://nodejs.org and then run this file again.
  start https://nodejs.org
  pause
  exit /b
)
node server.js
echo.
echo The server has stopped.
pause
