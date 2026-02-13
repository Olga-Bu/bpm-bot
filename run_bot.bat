@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Запуск бота...
echo.

set "PY="

rem Лаунчер py (если есть)
where py >nul 2>&1 && set "PY=py"

rem Ищем python.exe в стандартных папках установки
if not defined PY if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PY=%LocalAppData%\Programs\Python\Python310\python.exe"
if not defined PY if exist "%ProgramFiles%\Python313\python.exe" set "PY=%ProgramFiles%\Python313\python.exe"
if not defined PY if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
if not defined PY if exist "%ProgramFiles%\Python311\python.exe" set "PY=%ProgramFiles%\Python311\python.exe"
if not defined PY if exist "%ProgramFiles%\Python310\python.exe" set "PY=%ProgramFiles%\Python310\python.exe"

if defined PY (
    "%PY%" -m pip install -r requirements.txt -q 2>nul
    "%PY%" bot.py
    goto :end
)

echo Python не найден.
echo Установите с https://www.python.org/downloads/ (галочка "Add to PATH").

:end
echo.
echo Нажмите любую клавишу, чтобы закрыть окно...
pause >nul
