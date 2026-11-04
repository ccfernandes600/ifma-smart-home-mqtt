# Roteiro de bancada — validar o V4 no simulador

Refeito em 03/11/2026, depois da [revisão estática](REVISAO_ESTATICA_2026-11-03.md). Cada bloco
termina com um checkpoint: se não passar, pare ali e registre, porque os blocos seguintes dependem
dele. Dá para dividir em duas sessões: a primeira até o Bloco 4, a segunda a partir do Bloco 5.

**Na bancada:** o Claudio opera o Packet Tracer e cola os logs; o Claude Code interpreta e corrige.
O que interessa registrar é a **mensagem exata** do terminal do nó, no formato da ficha de falha do
[TESTE_ISOLADO.md](TESTE_ISOLADO.md).

Referência de portas e IPs: [MONTAGEM_PACKET_TRACER.md](MONTAGEM_PACKET_TRACER.md).

---

## Bloco 0 — Antes de abrir o Packet Tracer

- [ ] `python3 verificacao/verificar.py` diz **TUDO CERTO**
- [ ] `git status` limpo, e o ramo é o `main`

**O código mudou em 03/11, e nada disso rodou no simulador ainda.** O script que roda é uma **cópia**
colada dentro do nó: editar `src/*.py` não muda nada lá dentro. Por isso, todos os nós são recolados:

| Nó | IP | Arquivo |
|---|---|---|
| Central | .100 | `src/broker_central.py` |
| Perímetro | .21 | `src/zona_perimetro.py` |
| Sala | .22 | `src/zona_sala.py` |
| Cozinha | .23 | `src/zona_cozinha.py` |
| Quarto | .24 | `src/zona_quarto.py` |
| Jardim | .25 | `src/zona_jardim.py` |
| Garagem | .26 | `src/zona_garagem.py` |
| RFID Reader | .33 | `src/thing_rfid_reader.py` (mudou em 23/09; recole por garantia) |

---

## Bloco 1 — Abrir e inventariar

O arquivo é o **`src/IFMA-MQTT.pkt`**, de 23/09, aberto pelo Packet Tracer do Windows em:

```
\\wsl.localhost\Dell\home\ccfernandes\projetos\ifma-smart-home-mqtt\src\IFMA-MQTT.pkt
```

1. Conferir o build (a última bancada usou o **9.0.1.0858**).
2. **Salvar uma cópia antes de mexer:** `Arquivo → Salvar como` → `IFMA-MQTT_antes-de-2026-11.pkt`.
   O `.pkt` é binário: sem cópia, erro de montagem não tem desfazer.
3. Conferir se todos os nós da tabela acima existem. Cozinha, Quarto e Jardim foram montados em 21/09,
   e o arquivo deve tê-los; o conteúdo não dá para conferir fora do simulador.

**Checkpoint:** você sabe exatamente o que falta montar.

---

## Bloco 2 — Recolar os scripts

Para cada nó: **Stop** → selecionar tudo → colar → **Run**, sempre a Central primeiro.

> **Feche e reabra a aba do editor antes de copiar.** A aba aberta não recarrega quando o arquivo
> muda no disco, e o sintoma é a correção "não ter funcionado". Custou uma rodada em 23/09.

> **Salve o `.pkt` a cada dois ou três nós, e feche o PT a cada 45 min.** A memória dele cresce de 64 a
> 100 MB/min, mesmo sem script rodando, e reabrir o arquivo não a devolve. Travou em 23/09, depois de ~2 h,
> e em 03/11, com 3,7 GB (medições no `RETOMAR.md`).

**Checkpoint:** a Central imprime as duas linhas abaixo, sem zona no ar:

```
Broker ouvindo na porta 1883
Painel web em http://192.168.1.100:80
```

Depois, faça a **Etapa 1 do TESTE_ISOLADO** (Central sozinha, seis passos). Mudou código nela.

---

## Bloco 3 — A temperatura: fechar o diagnóstico

É onde paramos em 23/09. Há quatro hipóteses, e `src/diag_temperatura.py` loga sensor, ambiente e taxa.
**Uma variável por vez, e sem o AC por perto na primeira rodada.**

**Rodada 1 — sem atuadores.** Um SBC avulso, com um Temperature Sensor em D0, num contêiner sem AC nem
Fan. Confira o campo `NOTES` em `Environments`: se a Location do SBC mostra a descrição do perfil, ela
está com o clima de São Luís. Rode 3 minutos e copie a tabela.

**Rodada 2 — na Sala.** Stop na `zona_sala.py`, rode o diagnóstico no mesmo nó e copie 3 minutos.
Depois, com a temperatura acima de 30 °C, volte à zona, deixe o AC trabalhar até desligar e rode o
diagnóstico de novo.

| Resultado | Conclusão |
|---|---|
| Colunas SENSOR e AMBIENTE divergem | **H3:** o problema é o caminho da leitura |
| Rodada 1 com `C/h` perto de 0, num valor que a curva não produz | **H2:** contêiner com clima de fábrica |
| Rodada 1 com `C/h` em +5 até alcançar a curva, e depois acompanhando | **H1:** rampa normal; basta esperar |
| Rodada 1 correta, e valor abaixo da curva só depois de o AC funcionar | **H4:** efeito residual do AC |

A medição de 23/09 pesa a favor de H4: o AC derrubou o ambiente a 3,31 °C/min, acima do limite da
curva. **Não é conclusão:** é o que esta rodada decide.

**Se confirmar H4,** olhe a recuperação: o ambiente volta para a curva depois que o AC desliga? Se não
voltar, é decisão de projeto, e paramos para discutir antes de seguir.

**Checkpoint:** a causa está escrita no `RETOMAR.md`, e o aviso "Diagnóstico em aberto" do
`simulacao/README.md` foi atualizado, porque esse README é para publicar.

---

## Bloco 4 — Três perguntas que só o simulador responde

1. **O TCP junta mensagens?** Com Sala e Jardim publicando, procure no terminal da Central por
   `Mensagem descartada`. Se aparecer, a falha é real e precisa de delimitador no protocolo. Se não
   aparecer em alguns minutos com várias zonas no ar, registre: "não observado nesta carga".
2. **A saída de um pino sobrevive ao Stop?** Na Cozinha, dispare o alarme e dê Stop com ele ligado. O
   atuador continua ligado? Dê Run: a correção de 03/11 tem de desligá-lo.
3. **A injeção de fumaça funciona?** Rode o `src/diag_smoke.py`, reescrito em 03/11, num SBC avulso **no
   mesmo contêiner da Cozinha**. Era para subir cerca de 0,25 %/s. Se não subir, anote os valores: o
   formato vem do Heating Element, mas nunca foi testado com fumaça.

**Checkpoint:** as três respostas registradas no `RETOMAR.md`.

---

## Bloco 5 — Zona por zona

Siga as Etapas 2 e 3 do **TESTE_ISOLADO** na ordem combinada: Perímetro → Sala → Cozinha → Quarto →
Jardim → Garagem. Perímetro e Sala já passaram parte disso, mas o código mudou: é regressão, e é rápido.

**A API de cada atuador foi conferida na doc do device em 03/11/2026.** Três estavam erradas, e foram corrigidas
com regra no verificador: Lawn Sprinkler, Water Drain e Light usam `customWrite`; Smart LED usa `analogWrite`.
Water Level e Wind não têm GPIO, e a pressão leu 0: as três vêm de `Environment.get()`.

**Técnica de bancada para mexer no ambiente:** num SBC do mesmo contêiner, chame
`Environment.setContribution(id, taxa, 1.0e6, True)` a cada segundo. O valor vai para perfil + taxa × 30, e taxa 0
devolve ao perfil. Vale para `Smoke` e `Water Level`; em `Humidity` não teve efeito visível.

**Calibração:** o Photo Sensor lê quase só 0 ou 1023 (medido em 03/11/2026), então os limiares de luz não são críticos.
Na Cozinha e na Garagem, observe se o exaustor fica ligando e desligando perto de 20 %. Só nesse caso entra histerese no gás.

**Checkpoint:** cada zona aprovada nas camadas A e B, com a ficha de falha de quem não passou.

---

## Bloco 6 — Os comportamentos novos de 03/11

| Cenário | O que fazer | Esperado |
|---|---|---|
| Intrusão interna | Modo viagem + movimento na **Sala** e depois no **Quarto** | LCD `INTRUSAO!` / `Na sala` ou `No quarto`; Speaker liga; painel vermelho |
| Em casa | Modo normal + movimento na Sala | **Nada muda:** `CASA OK`, Speaker desligado |
| Intrusão externa | Modo viagem + movimento na Garagem | `INTRUSAO!` / `Na garagem`; Speaker liga |
| Cartão válido | Card 1005 | `ACESSO OK` por 5 s, mesmo com zonas publicando; a porta fecha; o LCD volta |
| Cartão inválido | Outro ID | `CARTAO NEGADO` por 5 s; o LCD volta sozinho |
| Alerta vence o aviso | Fumaça durante o `ACESSO OK` | `ALERTA DE GAS` aparece na hora |
| Porta sem Perímetro | Card 1005 e Stop no Perímetro antes de 5 s; depois Run | Log `Comando nao entregue` a cada 5 s; a porta fecha quando o Perímetro volta |
| Umidificador em viagem | Forçar ar seco no Quarto + modo viagem | Fica desligado; volta ao sair do modo |

> Na porta sem Perímetro, dê o Stop **depois** do `ACESSO OK`: antes dele, a porta nem abre. Medido em 03/11:
> falhas a cada ~6 s e fechamento no mesmo segundo em que o Perímetro voltou.

**Checkpoint:** a tabela inteira conferida no LCD, no painel e no terminal.

---

## Bloco 7 — O teste que fecha o projeto

**Etapa 4 do TESTE_ISOLADO**, com todas as zonas juntas, e `http://192.168.1.100` aberto no PC0.

**O que você deve ver:** `conectados: 7 · publicando: 6`, seis tabelas e, em `/estado`, os valores que
as zonas logam. Rode o modo viagem pelo botão: quatro zonas reagem, Cozinha e Jardim seguem iguais.

**Checkpoint:** o caminho zona → Central → tela está inteiro, com as seis zonas.

---

## Bloco 8 — Fechar

- [ ] Salvar o `.pkt` em `src/IFMA-MQTT.pkt`
- [ ] Atualizar o `RETOMAR.md`: o que passou, o que falhou, a causa da temperatura
- [ ] `python3 verificacao/verificar.py`
- [ ] Commit com o `.pkt` e push

**Depois de tudo validado**, nesta ordem: heartbeat, que também resolve o estado preso de zona que
some (C4 da revisão), e alarme por e-mail. Detalhes no `RETOMAR.md`.
