# Painel SO-101

Painel web para operar um par de braços **SO-ARM101** (líder + seguidor) com o [LeRobot](https://github.com/huggingface/lerobot) 0.6.1 e motores Feetech STS3215, no Windows.

Roda **no seu PC** (precisa do USB dos braços) e abre no navegador em `http://127.0.0.1:8101`.

## O que dá para fazer

| Serviço | O que faz |
|---|---|
| **Testar · Diagnóstico** | Lê os 12 motores sem mover nada: posição, tensão, temperatura, torque e alarmes (ex.: sobrecarga). |
| **Seguir o líder** | Teleoperação: o seguidor copia o líder ao vivo. |
| **Gravar exercício** | Grava os movimentos do líder com um nome. |
| **Demonstrar** | O seguidor repete sozinho um exercício gravado, uma vez ou N vezes seguidas, com contagem regressiva falada. |
| **Repouso** | Leva o seguidor devagar até a posição dobrada, em etapas (pulso → cotovelo → ombro). A pose pode ser redefinida à mão. |
| **Liberar** | Desliga o torque do seguidor e limpa alarmes de sobrecarga. |
| **Calibrar** | Calibração sem teclado: grava o meio e depois o curso de cada junta durante 90 s. |
| **Treinar IA** | *Em breve*: treino de política (ACT) com câmera. |

O botão **PARAR** fica sempre visível: interrompe a tarefa e o seguidor volta sozinho ao repouso.

## Como usar

1. Ambiente: Python 3.12 em `.venv` com `pip install -r requirements.txt`.
2. Ajuste as portas se precisar (padrão: seguidor `COM4`, líder `COM5`).
3. Calibre os dois braços (pelo painel ou `calibrar.bat`).
4. Dê dois cliques em **`painel.bat`**.

## Arquivos

| Arquivo | Função |
|---|---|
| `painel/servidor.py` | Servidor do painel (FastAPI, só em 127.0.0.1). |
| `painel/index.html` | Interface. |
| `exercicio.py` | Seguir, gravar, reproduzir, repouso e salvar repouso (linha de comando). |
| `ferramentas.py` | Diagnóstico e liberar torque. |
| `calib_auto.py` | Calibração sem ENTER (meio + curso temporizado). |
| `preparar-seguidor.py` | Faz o seguidor segurar a posição atual antes de ligar o torque, sem pulos. |
| `teleoperar.bat`, `calibrar.bat` | Atalhos de linha de comando. |

Os dados ficam em `.dados/` (calibração, exercícios, pose de repouso) e não vão para o git.

## Lições aprendidas (vale para outros SO-101)

- **Calibre levando cada junta até o fim do curso.** Se a posição de repouso ficar fora da faixa gravada, o seguidor trava naquele ponto.
- **Use a escala por faixa (`use_degrees=false`)** quando os cursos do líder e do seguidor forem diferentes. Em graus, o mesmo ângulo cai em posições físicas diferentes.
- **`max_relative_target` muito baixo (ex.: 2) impede o ombro e o cotovelo de vencer a gravidade.** Use 10 (e escreva `10.0`, porque o LeRobot recusa inteiro).
- **Não feche a garra 100%:** apertar o batente dispara a proteção de sobrecarga (status 32). O painel limita a garra a 8%.

## Segurança

- Mantenha as mãos longe do seguidor quando ele estiver com torque.
- Em qualquer comportamento estranho: **PARAR** no painel ou desligue a fonte do seguidor.
- Confira a tensão da fonte do líder: motores de 7,4 V não devem receber 12 V.
