@echo off
setlocal enabledelayedexpansion
title JARVIS — One-Click Installer
color 0B

echo.
echo  ============================================================
echo     J A R V I S  —  Automatic Installer
echo     Local AI Voice Assistant
echo  ============================================================
echo.
echo  This script will install everything JARVIS needs:
echo    [1] Python 3.12+
echo    [2] Python virtual environment + packages
echo    [3] Ollama (Local LLM server)
echo    [4] Phi-4 Mini AI model
echo    [5] Desktop shortcut
echo.
echo  ============================================================
echo  REQUIREMENTS:
echo    - Windows 10/11
echo    - NVIDIA GPU (GTX 1060 or better recommended)
echo    - ~10 GB free disk space
echo    - Internet connection (for downloading)
echo  ============================================================
echo.
pause

:: ─── Step 0: Set install directory ─────────────────────────────
set "INSTALL_DIR=%~dp0"
:: Remove trailing backslash
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"
echo [INFO] Install directory: %INSTALL_DIR%
echo.

:: ─── Step 1: Check Python ──────────────────────────────────────
echo [STEP 1/6] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] Python is NOT installed.
    echo [>>] Installing Python via winget...
    echo.
    winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Could not install Python automatically.
        echo [>>] Please download and install Python 3.12 manually from:
        echo     https://www.python.org/downloads/
        echo [>>] IMPORTANT: Check "Add Python to PATH" during installation!
        echo.
        pause
        exit /b 1
    )
    echo [OK] Python installed! You may need to restart this script.
    echo     Close this window, open a NEW command prompt, and re-run this installer.
    pause
    exit /b 0
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [OK] Python %%v found!
)
echo.

:: ─── Step 2: Check/Install Ollama ──────────────────────────────
echo [STEP 2/6] Checking for Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] Ollama is NOT installed.
    echo [>>] Installing Ollama via winget...
    echo.
    winget install --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Could not install Ollama automatically.
        echo [>>] Please download and install Ollama manually from:
        echo     https://ollama.com/download
        echo.
        pause
        exit /b 1
    )
    echo [OK] Ollama installed!
    echo [>>] Starting Ollama service...
    start "" ollama serve
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] Ollama is already installed!
)
echo.

:: ─── Step 3: Pull AI Model ─────────────────────────────────────
echo [STEP 3/6] Downloading Phi-4 Mini AI model (~2.5 GB)...
echo           This may take a few minutes on first run...
echo.
ollama pull phi4-mini
if %errorlevel% neq 0 (
    echo [!!] Failed to pull model. Make sure Ollama is running.
    echo [>>] Try running "ollama serve" in a separate window, then re-run this installer.
    pause
    exit /b 1
)
echo [OK] Phi-4 Mini model ready!
echo.

:: ─── Step 4: Create Python virtual environment ─────────────────
echo [STEP 4/6] Creating Python virtual environment...
if not exist "%INSTALL_DIR%\venv" (
    python -m venv "%INSTALL_DIR%\venv"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created!
) else (
    echo [OK] Virtual environment already exists!
)
echo.

:: ─── Step 5: Install Python packages ───────────────────────────
echo [STEP 5/6] Installing Python packages (this takes 5-10 minutes)...
echo           Installing: FastAPI, Whisper, Kokoro TTS, PyTorch, etc.
echo.
call "%INSTALL_DIR%\venv\Scripts\activate.bat"

:: Install PyTorch with CUDA support first
echo [>>] Installing PyTorch with CUDA support...
pip install torch --index-url https://download.pytorch.org/whl/cu124 --quiet
if %errorlevel% neq 0 (
    echo [!!] CUDA PyTorch failed, trying CPU version...
    pip install torch --quiet
)

:: Install remaining packages
echo [>>] Installing JARVIS dependencies...
pip install -r "%INSTALL_DIR%\backend\requirements.txt" --quiet
if %errorlevel% neq 0 (
    echo [!!] Some packages failed. Trying one by one...
    pip install fastapi --quiet
    pip install "uvicorn[standard]" --quiet
    pip install websockets --quiet
    pip install httpx --quiet
    pip install "numpy<3" --quiet
    pip install soundfile --quiet
    pip install sounddevice --quiet
    pip install pyttsx3 --quiet
    pip install faster-whisper --quiet
    pip install kokoro --quiet
)
echo.
echo [OK] All Python packages installed!
echo.

:: ─── Step 6: Create Desktop shortcut ───────────────────────────
echo [STEP 6/6] Creating desktop shortcut...

:: Create Start_JARVIS.bat in the install directory
(
echo @echo off
echo title JARVIS — Starting Up...
echo color 0B
echo echo.
echo echo  ============================================================
echo echo    J A R V I S  —  Starting Up...
echo echo  ============================================================
echo echo.
echo echo  [1/2] Starting Ollama in background...
echo start /min "" ollama serve
echo timeout /t 3 /nobreak ^>nul
echo echo  [2/2] Launching JARVIS server...
echo echo.
echo cd /d "%INSTALL_DIR%"
echo call venv\Scripts\activate.bat
echo python backend\main.py
echo pause
) > "%INSTALL_DIR%\Start_JARVIS.bat"

:: Copy shortcut to Desktop
copy "%INSTALL_DIR%\Start_JARVIS.bat" "%USERPROFILE%\Desktop\Start_JARVIS.bat" >nul 2>&1
echo [OK] Desktop shortcut created: Start_JARVIS.bat
echo.

:: ─── Done! ─────────────────────────────────────────────────────
echo.
echo  ============================================================
echo     INSTALLATION COMPLETE!
echo  ============================================================
echo.
echo  To launch JARVIS:
echo    1. Double-click "Start_JARVIS.bat" on your Desktop
echo    2. Wait for models to load (~15-30 seconds first time)
echo    3. Open http://127.0.0.1:8000 in your browser
echo.
echo  ============================================================
echo.
echo  Do you want to launch JARVIS now? (Y/N)
set /p LAUNCH_NOW="> "
if /i "%LAUNCH_NOW%"=="Y" (
    echo.
    echo [>>] Launching JARVIS...
    call "%INSTALL_DIR%\Start_JARVIS.bat"
)

pause
