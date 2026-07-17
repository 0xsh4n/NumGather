@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [*] Installing NumGather 2.0 dependencies...

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PY=python"
  ) else (
    echo [!] Python not found. Install Python 3 from https://www.python.org/downloads/
    echo     and ensure it is on PATH, then re-run setup.bat
    exit /b 1
  )
)

%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo [!] pip install failed.
  exit /b 1
)

echo.
echo [*] Done. Examples:
echo     python NumGather.py +919876543210
echo     python NumGather.py +14155552671 --ollama
echo     python NumGather.py --list-models
echo.
echo [*] Optional - Ollama (local LLM reasoning):
echo     https://ollama.com  - install, then:
echo     ollama pull llama3.2
echo     rem or a reasoning model: ollama pull deepseek-r1
echo.

if /I "%~1"=="--run" (
  %PY% NumGather.py
)

endlocal
