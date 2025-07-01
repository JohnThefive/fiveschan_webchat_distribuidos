@echo off
cd /d "C:\Users\Lara Letittja\Documents\GitHub\fiveschan_webchat_distribuidos"

if exist ".\.venv\Scripts\activate.ps1" (
    call .\.venv\Scripts\activate.ps1
) else (
    echo Ambiente virtual não encontrado.
    pause
    exit /b
)

start cmd /k "python server.py && exit"
start cmd /k "python web_gateway.py && exit"

echo.
echo Servidores iniciados.
pause
