"""Ferramentas rapidas dos bracos (nao movem nada).
  python ferramentas.py diagnostico  -> JSON com estado dos 12 motores
  python ferramentas.py liberar      -> desliga o torque do seguidor"""
import json
import sys

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

NOMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
PORTAS = {"seguidor": "COM4", "lider": "COM5"}
STATUS_BITS = {1: "tensao", 2: "sensor", 4: "temperatura", 8: "corrente", 32: "sobrecarga"}


def abrir(porta):
    bus = FeetechMotorsBus(porta, {str(i): Motor(i, "sts3215", MotorNormMode.DEGREES) for i in range(1, 7)})
    h = bus.port_handler
    if not h.openPort() or not h.setBaudRate(1_000_000):
        raise RuntimeError(f"Nao foi possivel abrir {porta}")
    return h, bus.packet_handler


def diagnostico():
    saida = {}
    for braco, porta in PORTAS.items():
        motores = []
        try:
            h, ph = abrir(porta)
        except Exception as e:
            saida[braco] = {"porta": porta, "erro": str(e), "motores": []}
            continue
        try:
            for i in range(1, 7):
                _, comm, _ = ph.ping(h, i)
                m = {"id": i, "nome": NOMES[i - 1], "ok": comm == 0}
                if comm == 0:
                    st = ph.read1ByteTxRx(h, i, 65)[0]
                    m.update(
                        posicao=ph.read2ByteTxRx(h, i, 56)[0],
                        tensao=ph.read1ByteTxRx(h, i, 62)[0] / 10,
                        temperatura=ph.read1ByteTxRx(h, i, 63)[0],
                        torque=ph.read1ByteTxRx(h, i, 40)[0],
                        status=st,
                        alarmes=[n for b, n in STATUS_BITS.items() if st & b],
                    )
                motores.append(m)
        finally:
            h.closePort()
        saida[braco] = {"porta": porta, "motores": motores}
    print(json.dumps(saida))


def liberar():
    h, ph = abrir(PORTAS["seguidor"])
    try:
        for i in range(1, 7):
            for _ in range(5):
                ph.write1ByteTxRx(h, i, 40, 0)
                if ph.read1ByteTxRx(h, i, 40)[0] == 0:
                    break
        # Liga e desliga o torque limpa alarmes de sobrecarga sem mover (alvo = posicao atual).
        for i in range(1, 7):
            if ph.read1ByteTxRx(h, i, 65)[0] & 32:
                lo, hi = ph.read2ByteTxRx(h, i, 9)[0], ph.read2ByteTxRx(h, i, 11)[0]
                pos = ph.read2ByteTxRx(h, i, 56)[0]
                ph.write2ByteTxRx(h, i, 42, min(max(pos, lo), hi) if hi > lo else pos)
                ph.write1ByteTxRx(h, i, 40, 1)
                ph.write1ByteTxRx(h, i, 40, 0)
        torque = [ph.read1ByteTxRx(h, i, 40)[0] for i in range(1, 7)]
        status = [ph.read1ByteTxRx(h, i, 65)[0] for i in range(1, 7)]
    finally:
        h.closePort()
    print(f"SEGUIDOR LIBERADO. torque={torque} status={status}")


if __name__ == "__main__":
    {"diagnostico": diagnostico, "liberar": liberar}[sys.argv[1]]()
