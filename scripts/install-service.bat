@echo off
REM Direct Windows service installation script
REM Run this as Administrator if the Python approach fails

echo Installing Image Transfer Daemon Service...
echo.

REM Navigate to the services directory
cd /d "%~dp0..\src\image_transfer\services"

REM Run the service wrapper directly with Python
python windows_service_wrapper.py install

if %ERRORLEVEL% == 0 (
    echo.
    echo Service installed successfully!
    echo.
    echo Commands:
    echo   Start:   net start ImageTransferDaemon
    echo   Stop:    net stop ImageTransferDaemon
    echo   Status:  sc query ImageTransferDaemon
    echo   Remove:  python windows_service_wrapper.py remove
) else (
    echo.
    echo Installation failed. Make sure you are running as Administrator.
    echo You may also need to install pywin32: pip install pywin32
)

pause