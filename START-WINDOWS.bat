@echo off
setlocal
cd /d "%~dp0"
echo BridgeLab is starting...
echo Please keep this window open until the main window appears.
echo.
if exist "%~dp0BridgeLab.exe" (
    "%~dp0BridgeLab.exe"
    goto done
)
if not exist "%~dp0launch_bridge.py" (
    echo Startup files are missing. Extract the complete package into a new folder.
    pause
    exit /b 1
)
set "BRIDGE_RUNTIME=%LOCALAPPDATA%\BridgeLab\runtime\Python312\python.exe"
if exist "%BRIDGE_RUNTIME%" (
    echo Using the existing BridgeLab runtime.
    "%BRIDGE_RUNTIME%" -u "%~dp0launch_bridge.py"
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    echo Using Python installed on this PC.
    py -3 -u "%~dp0launch_bridge.py"
    goto done
)
where python >nul 2>&1
if not errorlevel 1 (
    echo Using Python installed on this PC.
    python -u "%~dp0launch_bridge.py"
    goto done
)
echo No runtime was found. Opening first-run setup...
powershell.exe -NoLogo -NoProfile -File "%~dp0FIRST-RUN-WINDOWS.ps1"
:done
if errorlevel 1 (
    echo.
    echo BridgeLab stopped with an error. Details are printed above.
    echo Startup log: %LOCALAPPDATA%\BridgeLab\startup.log
    pause
    exit /b 1
)
exit /b 0
