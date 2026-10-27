"""Define como alvo a posicao atual, com torque desligado, antes da conexao."""
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

bus = FeetechMotorsBus("COM4", {
    str(i): Motor(i, "sts3215", MotorNormMode.DEGREES) for i in range(1, 7)
})
bus.connect()
try:
    for motor in bus.motors:
        bus.write("Torque_Enable", motor, 0, num_retry=3)
        if bus.read("Torque_Enable", motor, num_retry=3) != 0:
            raise RuntimeError(f"Torque continua ativo no motor {motor}")
    for motor in bus.motors:
        position = bus.read("Present_Position", motor, normalize=False, num_retry=3)
        # O motor recusa alvo fora dos limites gravados; ajusta para dentro.
        lo = bus.read("Min_Position_Limit", motor, normalize=False, num_retry=3)
        hi = bus.read("Max_Position_Limit", motor, normalize=False, num_retry=3)
        if hi > lo:
            position = min(max(position, lo), hi)
        bus.write("Goal_Position", motor, position, normalize=False, num_retry=3)
finally:
    bus.disconnect(disable_torque=False)
