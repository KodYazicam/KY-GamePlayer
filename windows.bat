@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul
title KodYazar Client

if not exist "run.py" (
  echo run.py yok. Bu dosyayi KY-GamePlayer klasorunde calistir.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Ilk calistirma: kurulum...
  call "%~dp0kurulum.bat"
  if errorlevel 1 exit /b 1
  if not exist ".venv\Scripts\python.exe" (
    echo .venv olusmadi.
    pause
    exit /b 1
  )
)

set "PYW=%~dp0.venv\Scripts\pythonw.exe"
set "PY=%~dp0.venv\Scripts\python.exe"

if exist "%PYW%" (
  start "KodYazar Client" /D "%~dp0" "%PYW%" "%~dp0run.py"
  exit /b 0
)

echo pythonw yok, konsolla aciliyor.
"%PY%" "%~dp0run.py"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo Cikis kodu %ERR%
  pause
)
exit /b %ERR%
