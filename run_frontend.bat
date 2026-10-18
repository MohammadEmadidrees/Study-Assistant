@echo off
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64;%PATH%"
cd /d "%~dp0frontend"
echo Starting Study Assistant Frontend on http://localhost:3000 ...
npm run dev
pause
