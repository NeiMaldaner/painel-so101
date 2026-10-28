# Onde paramos (28/10/2026)

## Já funciona
- Teleoperação (seguir o líder), gravar e reproduzir exercícios, repouso automático, PARAR.
- Painel web (`painel.bat`) com comando por texto e voz, diagnóstico, calibração.
- Calibração dos dois braços salva em `.dados/calibracao` (vale para estes mesmos braços).

## Falta testar no braço real
- Gestos **tchau** e **comemorar** e o **modo cuidadoso**: testar primeiro com o cuidadoso ligado.

## Próximo: câmeras (o kit tem duas)
1. **Pulso:** no suporte da garra do seguidor, olhando para onde a garra pega.
2. **Externa:** fixa, uns 85 cm acima da mesa, olhando reto para baixo.
3. Ligar cada uma direto no USB do PC e rodar `lerobot-find-cameras opencv` para achar os índices.
4. Depois: imagem ao vivo no painel e gravação de dataset LeRobot para treinar a IA (ACT).

## Ao trocar de PC
- Rodar `instalar.bat` uma vez.
- Conferir as portas com `listar-portas.bat`. O padrão é seguidor COM4, líder COM5; se mudarem, ajustar em `exercicio.py`, `ferramentas.py`, `calib_auto.py`, `preparar-seguidor.py` e nos `.bat`.
