@echo off
call "%~dp0ambiente.bat"
echo Teleoperacao: lider COM5, seguidor COM4.
echo As bases devem estar fixadas e o espaco do seguidor livre.
echo Posicione os dois bracos de forma semelhante antes de iniciar.
echo O seguidor sera energizado. Afaste as maos dele.
echo Para encerrar: Ctrl+C. Ao encerrar, o braco fica sem torque.
pause
python preparar-seguidor.py
if errorlevel 1 goto fim
lerobot-teleoperate --robot.type=so101_follower --robot.port=COM4 --robot.id=seguidor --robot.max_relative_target=10 --teleop.type=so101_leader --teleop.port=COM5 --teleop.id=lider --robot.use_degrees=false --teleop.use_degrees=false --display_data=false --fps=30
:fim
pause
