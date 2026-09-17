@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul
title KodYazar — kurulum

echo.
echo  KodYazar Client kurulum
echo  Klasor: %CD%
echo.

if not exist "run.py" (
  echo run.py yok. Bu dosyayi KY-GamePlayer klasorunde calistir.
  goto :fail
)
if not exist "requirements.txt" (
  echo requirements.txt yok.
  goto :fail
)
if not exist "games.json" (
  echo games.json yok.
  goto :fail
)

set "PY="
call :find_python
if not defined PY (
  echo Python 3.11+ bulunamadi.
  echo https://www.python.org/downloads/
  echo Kurarken "Add python.exe to PATH" ve py launcher isaretli olsun.
  goto :fail
)

echo Python: %PY%
"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Bu Python 3.11 altinda. 3.11 veya ustu lazim.
  goto :fail
)

if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam olusturuluyor...
  "%PY%" -m venv .venv
  if errorlevel 1 goto :fail
)

echo pip / PySide6 / cryptography...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo  Kurulum tamam. windows.bat ile ac.
echo.
pause
exit /b 0

:fail
echo.
echo  Kurulum basarisiz.
pause
exit /b 1

:find_python
where py >nul 2>&1
if not errorlevel 1 (
  py -3.14 -c "import sys" >nul 2>&1 && set "PY=py -3.14" && exit /b 0
  py -3.13 -c "import sys" >nul 2>&1 && set "PY=py -3.13" && exit /b 0
  py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12" && exit /b 0
  py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11" && exit /b 0
  py -3 -c "import sys" >nul 2>&1 && set "PY=py -3" && exit /b 0
)
where python >nul 2>&1
if not errorlevel 1 (
  set "PY=python"
  exit /b 0
)
where python3 >nul 2>&1
if not errorlevel 1 (
  set "PY=python3"
  exit /b 0
)
exit /b 1
