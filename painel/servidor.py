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
        tarefa.update(nome=nome, inicio=time.time(), fim=None, codigo=None,
                      proc=subprocess.Popen([PY, *args], cwd=RAIZ, env=AMBIENTE, stdout=f,
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
    }


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
