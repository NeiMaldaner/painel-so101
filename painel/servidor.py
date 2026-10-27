"""Painel web dos bracos SO-101. Roda so no seu PC: http://127.0.0.1:8101"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / ".dados"
EXERCICIOS = DADOS / "exercicios"
PARAR = DADOS / "parar"
LOG = RAIZ / ".cache" / "painel-tarefa.log"
CONFIG = DADOS / "painel.json"
PY = sys.executable
FPS = 30

AMBIENTE = dict(os.environ,
                HF_HOME=str(RAIZ / ".cache/huggingface"),
                HF_LEROBOT_HOME=str(DADOS / "lerobot"),
                HF_LEROBOT_CALIBRATION=str(DADOS / "calibracao"),
                PYTHONUTF8="1", PYTHONUNBUFFERED="1")

app = FastAPI(title="Painel SO-101")
trava = threading.Lock()
tarefa = {"proc": None, "nome": None, "inicio": None, "fim": None, "codigo": None}

# Linhas de log que so poluem (avisos de limite por passo, dicionarios, etc.).
RUIDO = re.compile(r"^\s|^\{|clamped|Teleop loop|^-+$")


def config():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {"cuidadoso": False}


def ocupado():
    p = tarefa["proc"]
    return p is not None and p.poll() is None


def iniciar(nome, args):
    with trava:
        if ocupado():
            raise HTTPException(409, f"Ja existe uma tarefa rodando: {tarefa['nome']}")
        PARAR.unlink(missing_ok=True)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        f = open(LOG, "w", encoding="utf-8")
        env = dict(AMBIENTE, SO101_CUIDADOSO="1" if config().get("cuidadoso") else "0")
        tarefa.update(nome=nome, inicio=time.time(), fim=None, codigo=None,
                      proc=subprocess.Popen([PY, *args], cwd=RAIZ, env=env, stdout=f,
                                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL))

        def vigiar(p=tarefa["proc"]):
            p.wait()
            f.close()
            tarefa.update(fim=time.time(), codigo=p.returncode)

        threading.Thread(target=vigiar, daemon=True).start()
    return {"ok": True, "tarefa": nome}


def linhas_log(n=40):
    if not LOG.exists():
        return []
    linhas = [l.rstrip() for l in LOG.read_text(encoding="utf-8", errors="replace").splitlines()]
    uteis = [l for l in linhas if l and not RUIDO.search(l)]
    return uteis[-n:]


def nome_valido(nome):
    if not re.fullmatch(r"[\w\-]{1,40}", nome or ""):
        raise HTTPException(400, "Nome invalido: use letras, numeros, - ou _ (ate 40).")
    return nome


@app.get("/")
def pagina():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/estado")
def estado():
    exs = []
    for f in sorted(EXERCICIOS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            n = len(json.loads(f.read_text())["quadros"])
        except Exception:
            n = 0
        exs.append({"nome": f.stem, "segundos": round(n / FPS), "data": time.strftime(
            "%d/%m %H:%M", time.localtime(f.stat().st_mtime))})
    rep = DADOS / "repouso.json"
    return {
        "rodando": ocupado(),
        "tarefa": tarefa["nome"],
        "decorrido": round((tarefa["fim"] or time.time()) - tarefa["inicio"]) if tarefa["inicio"] else 0,
        "codigo": tarefa["codigo"],
        "log": linhas_log(),
        "exercicios": exs,
        "repouso_personalizado": rep.exists(),
        "cuidadoso": config().get("cuidadoso", False),
    }


class Config(BaseModel):
    cuidadoso: bool


@app.post("/api/config")
def salvar_config(c: Config):
    DADOS.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({"cuidadoso": c.cuidadoso}))
    return {"ok": True, "cuidadoso": c.cuidadoso}


@app.get("/api/diagnostico")
def diagnostico():
    if ocupado():
        raise HTTPException(409, "Pare a tarefa atual antes do diagnostico (a porta USB esta em uso).")
    r = subprocess.run([PY, "ferramentas.py", "diagnostico"], cwd=RAIZ, env=AMBIENTE,
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise HTTPException(500, (r.stderr or r.stdout)[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class Acao(BaseModel):
    modo: str
    segundos: float = 60
    nome: str = "ultimo"
    vezes: int = 1
    braco: str = "seguidor"


@app.post("/api/acao")
def acao(a: Acao):
    seg = str(max(5, min(a.segundos, 1800)))
    if a.modo == "seguir":
        return iniciar("Seguir o lider", ["exercicio.py", "seguir", seg])
    if a.modo == "gravar":
        return iniciar(f"Gravar '{nome_valido(a.nome)}'", ["exercicio.py", "gravar", seg, a.nome])
    if a.modo == "reproduzir":
        if not (EXERCICIOS / f"{nome_valido(a.nome)}.json").exists():
            raise HTTPException(404, "Exercicio nao encontrado.")
        vezes = str(max(1, min(a.vezes, 50)))
        titulo = f"Demonstrar '{a.nome}' x{vezes}" if a.vezes > 1 else f"Reproduzir '{a.nome}'"
        return iniciar(titulo, ["exercicio.py", "reproduzir", a.nome, vezes])
    if a.modo == "gesto":
        if a.nome not in ("tchau", "comemorar"):
            raise HTTPException(400, "Gesto desconhecido.")
        return iniciar(f"Gesto: {a.nome}", ["exercicio.py", "gesto", a.nome])
    if a.modo == "repouso":
        return iniciar("Ir para o repouso", ["exercicio.py", "repouso"])
    if a.modo == "salvar-repouso":
        return iniciar("Salvar repouso", ["exercicio.py", "salvar-repouso"])
    if a.modo == "liberar":
        return iniciar("Liberar seguidor", ["ferramentas.py", "liberar"])
    if a.modo in ("calibrar-meio", "calibrar-faixa"):
        if a.braco not in ("seguidor", "lider"):
            raise HTTPException(400, "Braco invalido.")
        fase = "meio" if a.modo == "calibrar-meio" else "faixa"
        args = ["calib_auto.py", a.braco, fase] + ([seg] if fase == "faixa" else [])
        return iniciar(f"Calibrar {a.braco} ({fase})", args)
    raise HTTPException(400, f"Modo desconhecido: {a.modo}")


# ---------- Comando por texto (regras em portugues, sem internet) ----------
NUMEROS = {"uma": 1, "um": 1, "duas": 2, "dois": 2, "tres": 3, "quatro": 4, "cinco": 5,
           "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10}


def _normal(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _vezes(t):
    m = re.search(r"(\d+|" + "|".join(NUMEROS) + r")\s*(vezes|x)\b", t)
    if not m:
        return 1
    v = m.group(1)
    return int(v) if v.isdigit() else NUMEROS[v]


def _segundos(t, padrao):
    m = re.search(r"(\d+)\s*(s|seg|segundos?)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(min|minutos?)\b", t)
    return int(m.group(1)) * 60 if m else padrao


def interpretar(frase):
    """Frase -> (resposta, acao ou None). Acao: dict para /api/acao, ou {'modo': 'parar'|'diagnostico'}."""
    t = _normal(frase).strip()
    nomes = [e.stem for e in EXERCICIOS.glob("*.json")]
    if not t:
        return "Diga o que fazer. Ex.: \"dá tchau\", \"repete o primeiro 3 vezes\".", None
    # "para" so como ordem no inicio ("para!"), nao como preposicao ("vai para o repouso")
    if re.search(r"^(para|pare)\b|\b(pare|parar|chega|stop)\b", t):
        return "Parando. O seguidor volta ao repouso.", {"modo": "parar"}
    if re.search(r"tchau|acen|adeus", t):
        return "Dando tchau!", {"modo": "gesto", "nome": "tchau"}
    if re.search(r"comemor|festa|parabens|uhu|viva", t):
        return "Comemorando!", {"modo": "gesto", "nome": "comemorar"}
    if re.search(r"salva\w* (o )?repouso|guarda\w* (o )?repouso", t):
        return "Guardando a pose atual como repouso.", {"modo": "salvar-repouso"}
    if re.search(r"repous|descans|dorm|guarda o braco|recolh", t):
        return "Indo para o repouso.", {"modo": "repouso"}
    if re.search(r"libera|solta|desliga o torque|relaxa", t):
        return "Liberando o seguidor (torque desligado).", {"modo": "liberar"}
    if re.search(r"diagnost|status|como (voce )?esta|testa os motores|verifica", t):
        return "Rodando o diagnóstico.", {"modo": "diagnostico"}
    if re.search(r"\bgrav", t):
        m = re.search(r"(?:chamad[oa]|nome|como)\s+([\w\-]+)", t)
        nome = m.group(1) if m else "ultimo"
        seg = _segundos(t, 60)
        return f"Gravando \"{nome}\" por {seg} s. Mova o líder.", {"modo": "gravar", "nome": nome, "segundos": seg}
    if re.search(r"segu|copi|o que eu (fizer|faco)|imita|teleop", t):
        seg = _segundos(t, 300)
        return f"Seguindo o líder por até {seg} s.", {"modo": "seguir", "segundos": seg}
    if re.search(r"repet|reproduz|demonstr|faz (o|a) |mostra", t):
        alvo = next((n for n in sorted(nomes, key=len, reverse=True) if _normal(n) in t), None)
        if not alvo:
            if not nomes:
                return "Ainda não há exercício gravado.", None
            alvo = max(EXERCICIOS.glob("*.json"), key=lambda p: p.stat().st_mtime).stem
        v = _vezes(t)
        return (f"Repetindo \"{alvo}\"" + (f" {v} vezes." if v > 1 else "."),
                {"modo": "reproduzir", "nome": alvo, "vezes": v})
    return "Não entendi. Tente: \"dá tchau\", \"comemora\", \"repouso\", \"segue\", \"repete o primeiro 2 vezes\".", None


class Frase(BaseModel):
    texto: str
    executar: bool = True


@app.post("/api/comando")
def comando(f: Frase):
    resposta, a = interpretar(f.texto)
    if a and f.executar:
        if a["modo"] == "parar":
            parar()
        elif a["modo"] == "diagnostico":
            pass  # a pagina chama /api/diagnostico e mostra a tabela
        else:
            acao(Acao(**a))
    return {"resposta": resposta, "acao": a}


@app.post("/api/parar")
def parar():
    """Pede parada suave (o seguidor vai ao repouso). Se nao parar em 25 s, encerra a forca."""
    if not ocupado():
        return {"ok": True, "msg": "Nada rodando."}
    PARAR.touch()
    p = tarefa["proc"]
    if tarefa["nome"].startswith(("Calibrar", "Liberar", "Salvar")):
        p.terminate()  # estes nao usam o arquivo de parada e nao ligam torque

    def forcar():
        try:
            p.wait(timeout=25)
        except subprocess.TimeoutExpired:
            p.kill()
            subprocess.run([PY, "ferramentas.py", "liberar"], cwd=RAIZ, env=AMBIENTE, timeout=60)

    threading.Thread(target=forcar, daemon=True).start()
    return {"ok": True}


@app.delete("/api/exercicios/{nome}")
def apagar(nome: str):
    f = EXERCICIOS / f"{nome_valido(nome)}.json"
    if not f.exists():
        raise HTTPException(404, "Exercicio nao encontrado.")
    f.unlink()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8101)
