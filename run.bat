@echo off
setlocal

cd /d "%~dp0autostream-agent"

if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Please ensure Python is installed and added to PATH.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

if not exist .env (
    echo.
    echo Copying .env.example to .env...
    copy .env.example .env
    echo.
    echo ====================================================================
    echo SETUP REQUIRED:
    echo An .env file has been created in the autostream-agent directory.
    echo Please open autostream-agent\.env and add your GOOGLE_API_KEY.
    echo Once you have added the key, run this script again.
    echo ====================================================================
    pause
    exit /b 0
)

echo.
echo Starting AutoStream Agent...
python agent.py

pause
