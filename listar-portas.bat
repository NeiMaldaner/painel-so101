@echo off
call "%~dp0ambiente.bat"
python -m serial.tools.list_ports -v
pause
