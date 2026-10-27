@echo off
call "%~dp0ambiente.bat"
echo Painel SO-101 em http://127.0.0.1:8101  (feche esta janela para desligar)
start "" http://127.0.0.1:8101
python painel\servidor.py
pause
