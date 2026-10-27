@echo off
call "%~dp0ambiente.bat"
echo === CALIBRACAO DOS DOIS BRACOS ===
echo Backup da calibracao anterior ja foi feito em .dados\backup-calibracao-*
echo.
echo IMPORTANTE: quando aparecer "Press ENTER to use provided calibration file",
echo digite c e aperte ENTER. Senao ele reaproveita a calibracao antiga.
echo.
echo Em cada braco:
echo  1. Coloque o braco na posicao do MEIO do curso e aperte ENTER.
echo  2. Mova CADA junta de um extremo ao outro, devagar, incluindo
echo     a posicao dobrada de repouso. Depois aperte ENTER.
echo     (wrist_roll nao precisa, ele gira 360 graus)
echo.
echo --- PASSO 1: SEGUIDOR (COM4), sem torque ---
pause
python calibrar-seguidor.py
if errorlevel 1 goto fim
echo.
echo --- PASSO 2: LIDER (COM5) ---
pause
lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM5 --teleop.id=lider
:fim
echo.
echo Fim da calibracao.
pause
