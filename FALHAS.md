# FALHAS — painel-so101

| data | o que quebrou | menor correção |
|---|---|---|
| 2026-10-27 | posição de repouso fora da faixa calibrada: o seguidor travava no cotovelo e no pulso | recalibrar levando cada junta até o fim do curso |
| 2026-10-27 | líder e seguidor com cursos diferentes: em graus, o mesmo ângulo caía em posições físicas diferentes | `use_degrees=false` (escala por faixa) nos dois braços |
| 2026-10-27 | ombro e cotovelo do seguidor não se mexiam com `max_relative_target=2`: força pequena demais contra a gravidade | `max_relative_target=10.0` |
| 2026-10-27 | `max_relative_target=10` (inteiro) dava `TypeError: 10` no LeRobot 0.6.1 | escrever `10.0` |
| 2026-10-27 | preparar o seguidor falhava: alvo 2049 acima do limite 2047 | limitar o alvo à faixa do motor |
| 2026-10-27 | garra entrou em sobrecarga (status 32) ao fechar até o batente; o seguidor não conectava | garra limitada a 8%; ligar e desligar o torque limpa o alarme |
| 2026-10-27 | ao desligar, o LeRobot falhava em soltar o torque de um motor e o braço ficava travado | desligar o torque motor a motor, com novas tentativas, no fim de cada tarefa |
| 2026-10-27 | comando "vai para o repouso" foi entendido como "parar" | "para" só vale como ordem no início da frase |
