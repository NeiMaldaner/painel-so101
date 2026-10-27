"""Calibracao sem ENTER: fase 'meio' grava homing; fase 'faixa' grava curso por N segundos.
Torque fica DESLIGADO o tempo todo. Uso: python calib_auto.py seguidor|lider meio|faixa [segundos]"""
import os, sys, json, time
from pathlib import Path
root = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(root / ".cache/huggingface")
os.environ["HF_LEROBOT_HOME"] = str(root / ".dados/lerobot")
os.environ["HF_LEROBOT_CALIBRATION"] = str(root / ".dados/calibracao")
from lerobot.motors import MotorCalibration
from lerobot.motors.feetech import OperatingMode

role, phase = sys.argv[1], sys.argv[2]
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 60
if role == "seguidor":
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    dev = SO101Follower(SO101FollowerConfig(port="COM4", id="seguidor"))
else:
    from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
    dev = SO101Leader(SO101LeaderConfig(port="COM5", id="lider"))
bus = dev.bus
tmp = root / f".dados/homing-{role}.json"
bus.connect()
try:
    bus.disable_torque()
    if phase == "meio":
        for m in bus.motors:
            bus.write("Operating_Mode", m, OperatingMode.POSITION.value)
        h = bus.set_half_turn_homings()
        tmp.write_text(json.dumps(h))
        print("MEIO GRAVADO:", h)
    else:
        if tmp.exists():
            homing = json.loads(tmp.read_text())
        else:  # refazer so a faixa: reaproveita o meio da calibracao salva
            homing = {m: c.homing_offset for m, c in dev.calibration.items()}
        names = [m for m in bus.motors if m != "wrist_roll"]
        print(f"Comecando em 5s, gravando por {secs:.0f}s...", flush=True)
        time.sleep(5)
        pos = bus.sync_read("Present_Position", names, normalize=False, num_retry=5)
        mins, maxs = dict(pos), dict(pos)
        t0 = time.time()
        while time.time() - t0 < secs:
            pos = bus.sync_read("Present_Position", names, normalize=False, num_retry=5)
            for m in names:
                mins[m] = min(mins[m], pos[m]); maxs[m] = max(maxs[m], pos[m])
            time.sleep(0.02)
        mins["wrist_roll"], maxs["wrist_roll"] = 0, 4095
        for m in names:
            print(f"{m:14} min={mins[m]:5} max={maxs[m]:5} curso={maxs[m]-mins[m]:5}")
        ruins = [m for m in names if maxs[m] - mins[m] < 300]
        if ruins:
            print("ERRO: juntas quase sem movimento:", ruins, "- calibracao NAO salva")
            sys.exit(2)
        dev.calibration = {m: MotorCalibration(id=mo.id, drive_mode=0, homing_offset=homing[m],
                           range_min=mins[m], range_max=maxs[m]) for m, mo in bus.motors.items()}
        bus.write_calibration(dev.calibration)
        dev._save_calibration()
        tmp.unlink(missing_ok=True)
        print("CALIBRACAO SALVA em", dev.calibration_fpath)
finally:
    bus.disconnect(disable_torque=False)
