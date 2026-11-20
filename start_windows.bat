@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ====================================
echo        ALIGNLY RESUME STUDIO
echo  ====================================
echo.
if not exist ".env" copy ".env.example" ".env" >nul
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    python -m venv .venv
    if errorlevel 1 (echo Please install Python 3.10 or newer.& pause & exit /b 1)
  )
  echo Installing Python dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (echo Dependency install failed.& pause & exit /b 1)
)
echo.
echo Open http://127.0.0.1:8000 in your browser.
echo Press Ctrl+C to stop the app.
echo To use Gemini, add your key to .env and restart.
echo.
".venv\Scripts\python.exe" run.py
pause
