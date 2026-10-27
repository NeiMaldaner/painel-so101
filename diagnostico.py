"""Consulta motores sem escrever registros ou alterar torque."""
import json
from pathlib import Path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

results = {}
for role, port in (("seguidor", "COM4"), ("lider", "COM5")):
    bus = FeetechMotorsBus(port, {str(i): Motor(i, "sts3215", MotorNormMode.DEGREES) for i in range(1, 7)})
    handler = bus.port_handler
    results[role] = {"port": port, "motors": []}
    try:
        if not handler.openPort() or not handler.setBaudRate(1_000_000):
            raise RuntimeError(f"Nao foi possivel abrir {port}")
        for motor_id in range(1, 7):
            model, comm, error = bus.packet_handler.ping(handler, motor_id)
            item = {"id": motor_id, "model": model, "communication": comm, "error": error}
            if comm == 0:
                pos, pos_comm, pos_err = bus.packet_handler.read2ByteTxRx(handler, motor_id, 56)
                torque, torque_comm, torque_err = bus.packet_handler.read1ByteTxRx(handler, motor_id, 40)
                item.update(position=pos, position_comm=pos_comm, position_error=pos_err,
                            torque=torque, torque_comm=torque_comm, torque_error=torque_err)
            results[role]["motors"].append(item)
    finally:
        handler.closePort()
print(json.dumps(results, indent=2))
Path(".dados").mkdir(exist_ok=True)
Path(".dados/diagnostico.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
