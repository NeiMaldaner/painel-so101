"""Controle do seguidor SO-101.
  python exercicio.py seguir [segundos]   -> copia o lider ao vivo
  python exercicio.py gravar [segundos] [nome]   -> copia o lider e salva em .dados/exercicios/<nome>.json
  python exercicio.py reproduzir [nome] [vezes]  -> seguidor repete sozinho o exercicio gravado
  python exercicio.py repouso             -> seguidor vai sozinho para a posicao de repouso
  python exercicio.py salvar-repouso      -> guarda a pose atual (posta a mao) como repouso
  python exercicio.py gesto tchau|comemorar
Todos terminam levando o seguidor ao repouso e soltando o torque.
Criar o arquivo .dados/parar interrompe na hora (a gravacao e salva ate ali)."""
import os, sys, json, time, subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(root / ".cache/huggingface")
os.environ["HF_LEROBOT_HOME"] = str(root / ".dados/lerobot")
os.environ["HF_LEROBOT_CALIBRATION"] = str(root / ".dados/calibracao")
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

FPS = 30
# Modo cuidadoso (SO101_CUIDADOSO=1): mais devagar, passo menor e torque limitado a 60%.
CUIDADOSO = os.environ.get("SO101_CUIDADOSO") == "1"
VELOCIDADE = 20.0 if CUIDADOSO else 40.0  # % do curso por segundo nos movimentos automaticos
PASSO_MAX = 5.0 if CUIDADOSO else 10.0     # maior salto por quadro (30 por segundo)
TORQUE = 600 if CUIDADOSO else 1000        # Torque_Limit (0-1000), volta ao normal ao religar
GARRA_MIN = 8.0    # garra nao fecha 100%: apertar o batente dispara a protecao
EXERCICIOS = root / ".dados/exercicios"
EXERCICIOS.mkdir(parents=True, exist_ok=True)
PARAR = root / ".dados/parar"
# Braco dobrado, com folga dos batentes para os motores nao ficarem forcando.
REPOUSO = {"shoulder_pan.pos": -9.0, "shoulder_lift.pos": -96.0, "elbow_flex.pos": 96.0,
           "wrist_flex.pos": 69.0, "wrist_roll.pos": 0.0, "gripper.pos": GARRA_MIN}
# Ordem segura: pulso/garra/base, depois dobra o cotovelo, por ultimo abaixa o ombro.
ETAPAS_REPOUSO = [["shoulder_pan.pos", "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"],
                  ["elbow_flex.pos"], ["shoulder_lift.pos"]]

# Gestos: poses no meio do curso de cada junta, longe dos batentes.
ALTO = {"shoulder_pan.pos": 0.0, "shoulder_lift.pos": 0.0, "elbow_flex.pos": 0.0,
        "wrist_flex.pos": 0.0, "wrist_roll.pos": 0.0, "gripper.pos": 30.0}

REPOUSO_ARQ = root / ".dados/repouso.json"
if REPOUSO_ARQ.exists():
    REPOUSO.update(json.loads(REPOUSO_ARQ.read_text()))

modo = sys.argv[1]
PARAR.unlink(missing_ok=True)
if modo == "salvar-repouso":
    # Le a pose atual sem ligar o torque (o braco foi posicionado a mao).
    r = SO101Follower(SO101FollowerConfig(port="COM4", id="seguidor", use_degrees=False))
    r.bus.connect()
    try:
        pose = {f"{m}.pos": round(v, 1) for m, v in r.bus.sync_read("Present_Position").items()}
    finally:
        r.bus.disconnect(disable_torque=True)
    pose["gripper.pos"] = max(pose["gripper.pos"], GARRA_MIN)
    REPOUSO_ARQ.write_text(json.dumps(pose, indent=2))
    print("REPOUSO SALVO:", pose)
    sys.exit(0)
subprocess.run([sys.executable, str(root / "preparar-seguidor.py")], check=True)
robot = SO101Follower(SO101FollowerConfig(port="COM4", id="seguidor",
                      max_relative_target=PASSO_MAX, use_degrees=False))


def pose_atual():
    obs = robot.bus.sync_read("Present_Position")
    return {f"{m}.pos": v for m, v in obs.items()}


def ir_para(alvo, juntas=None, vel=None):
    """Move suave e em linha reta ate o alvo, so nas juntas indicadas."""
    ini = pose_atual()
    fim = dict(ini)
    for k in (juntas or alvo):
        fim[k] = alvo[k]
    dist = max(abs(fim[k] - ini[k]) for k in fim)
    passos = max(1, int(dist / min(vel or VELOCIDADE, VELOCIDADE * 2) * FPS))
    for n in range(1, passos + 1):
        if PARAR.exists():
            return False
        f = n / passos
        robot.send_action({k: ini[k] + (fim[k] - ini[k]) * f for k in fim})
        time.sleep(1 / FPS)
    for _ in range(FPS // 2):  # meio segundo para assentar
        robot.send_action(fim); time.sleep(1 / FPS)
    return True


def gesto(nome):
    """tchau: levanta e acena com o pulso. comemorar: levanta e abre/fecha a garra."""
    print(f"GESTO: {nome}", flush=True)
    ir_para(ALTO)
    if nome == "tchau":
        for _ in range(3):
            for lado in (1, -1):
                a = dict(ALTO, **{"wrist_flex.pos": 35.0 * lado, "shoulder_pan.pos": 12.0 * lado})
                if not ir_para(a, vel=VELOCIDADE * 2):
                    return
    elif nome == "comemorar":
        for _ in range(3):
            for g in (70.0, GARRA_MIN + 7):
                if not ir_para(dict(ALTO, **{"gripper.pos": g}), ["gripper.pos"], vel=VELOCIDADE * 2):
                    return
        for lado in (1, -1, 0):
            ir_para(dict(ALTO, **{"wrist_roll.pos": 40.0 * lado}), ["wrist_roll.pos"], vel=VELOCIDADE * 2)
    else:
        raise SystemExit(f"Gesto desconhecido: {nome}")
    ir_para(ALTO)


def ir_repouso():
    PARAR.unlink(missing_ok=True)
    print("Indo para o repouso...", flush=True)
    for juntas in ETAPAS_REPOUSO:
        ir_para(REPOUSO, juntas)


def copiar_lider(secs):
    from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
    leader = SO101Leader(SO101LeaderConfig(port="COM5", id="lider", use_degrees=False))
    leader.connect()
    quadros = []
    print(f"SEGUINDO O LIDER por ate {secs:.0f}s", flush=True)
    t0 = time.perf_counter()
    try:
        while time.perf_counter() - t0 < secs and not PARAR.exists():
            t = time.perf_counter()
            a = leader.get_action()
            a["gripper.pos"] = max(a["gripper.pos"], GARRA_MIN)
            robot.send_action(a)
            quadros.append(a)
            time.sleep(max(0, 1 / FPS - (time.perf_counter() - t)))
    finally:
        leader.disconnect()
    return quadros


robot.connect()
for _m in robot.bus.motors:
    robot.bus.write("Torque_Limit", _m, TORQUE)
if CUIDADOSO:
    print("MODO CUIDADOSO: velocidade menor e torque a 60%", flush=True)
try:
    if modo in ("seguir", "gravar"):
        secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60
        quadros = copiar_lider(secs)
        if modo == "gravar":
            ARQ = EXERCICIOS / f"{sys.argv[3] if len(sys.argv) > 3 else 'ultimo'}.json"
            ARQ.write_text(json.dumps({"fps": FPS, "quadros": quadros}))
            print(f"SALVO: {len(quadros)} quadros ({len(quadros)/FPS:.0f}s) em {ARQ}")
    elif modo == "gesto":
        gesto(sys.argv[2])
    elif modo == "reproduzir":
        nome = sys.argv[2] if len(sys.argv) > 2 else "ultimo"
        vezes = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        q = json.loads((EXERCICIOS / f"{nome}.json").read_text())["quadros"]
        for a in q:
            a["gripper.pos"] = max(a["gripper.pos"], GARRA_MIN)
        print("Indo para a pose inicial...", flush=True)
        ir_para(q[0])
        for rodada in range(1, vezes + 1):
            if PARAR.exists():
                break
            if rodada > 1:
                ir_para(q[0])
            print(f"REPRODUZINDO '{nome}' {len(q)/FPS:.0f}s (rodada {rodada}/{vezes})", flush=True)
            for a in q:
                if PARAR.exists():
                    print("Parado pelo usuario"); break
                t = time.perf_counter()
                robot.send_action(a)
                time.sleep(max(0, 1 / FPS - (time.perf_counter() - t)))
    ir_repouso()
    print("FIM - no repouso")
finally:
    try:
        robot.disconnect()
    except Exception as e:
        print("Falha ao desconectar, desligando torque direto:", e)
        h, ph = robot.bus.port_handler, robot.bus.packet_handler
        for _ in range(3):
            for i in range(1, 7):
                ph.write1ByteTxRx(h, i, 40, 0)
