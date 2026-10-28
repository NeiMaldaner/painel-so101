@echo off
rem Prepara o ambiente num PC novo (uma vez so). Precisa de Python 3.12 instalado.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto deps
where py >nul 2>nul && (py -3.12 -m venv .venv) || (python -m venv .venv)
if not exist ".venv\Scripts\python.exe" (
  echo Nao achei o Python 3.12. Instale em https://www.python.org/downloads/ e rode de novo.
  pause & exit /b 1
)
:deps
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Pronto. Ligue os bracos e de dois cliques em painel.bat
pause
