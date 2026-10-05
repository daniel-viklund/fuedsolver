@echo off
setlocal
pushd "%~dp0.." || exit /b 1

if exist "Feudsolver.exe" (
    "Feudsolver.exe"
    goto :finished
)

if not exist ".venv\Scripts\python.exe" (
    echo Python environment not found. Run scripts\setup.bat first.
    popd
    exit /b 1
)

if not defined FEUD_HOST set "FEUD_HOST=0.0.0.0"
if not defined PORT set "PORT=8000"
if not defined FEUD_ENGINE if exist "bin\feudsolver.exe" set "FEUD_ENGINE=%CD%\bin\feudsolver.exe"
if not defined FEUD_ENGINE (
    if exist "build\Release\feudsolver.exe" (
        set "FEUD_ENGINE=%CD%\build\Release\feudsolver.exe"
    ) else (
        set "FEUD_ENGINE=%CD%\build\feudsolver.exe"
    )
)
if not exist "%FEUD_ENGINE%" (
    echo Engine not found. Run scripts\setup.bat or set FEUD_ENGINE to the executable path.
    popd
    exit /b 1
)

set "PYTHONUTF8=1"
echo Open http://localhost:%PORT% on this computer. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn backend.app:app --host "%FEUD_HOST%" --port "%PORT%"
:finished
set "FEUD_EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %FEUD_EXIT_CODE%
