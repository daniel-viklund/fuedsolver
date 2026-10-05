@echo off
setlocal
pushd "%~dp0.." || exit /b 1
set "PYTHONUTF8=1"

where cmake >nul 2>&1
if errorlevel 1 (
    echo CMake not found. Install CMake and add it to PATH.
    goto :failed
)

where py >nul 2>&1
if errorlevel 1 (
    python -m venv .venv
) else (
    py -3 -m venv .venv
)
if errorlevel 1 goto :failed

".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 'Python 3.12 or newer is required.')"
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 goto :failed
cmake --build build --config Release --parallel
if errorlevel 1 goto :failed
if not exist "data\swedish.txt" (
    ".venv\Scripts\python.exe" scripts\download_dictionary.py
    if errorlevel 1 goto :failed
)

echo Ready. Start the website with scripts\run.bat
popd
exit /b 0

:failed
echo Setup failed. Check the error above. Python 3.12+, CMake, and a C++17 compiler are required.
popd
exit /b 1
