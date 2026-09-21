# Roteiro de bancada — fechar o V4

Sessão única, estimada em **2h30 a 3h**. Cada bloco termina com um checkpoint: se ele não
passar, pare ali e anote, porque os blocos seguintes dependem dele.

Build do simulador nesta sessão: **Packet Tracer 9.0.1.0858**.

Referência de portas e IPs: [MONTAGEM_PACKET_TRACER.md](MONTAGEM_PACKET_TRACER.md).
Estado do projeto e decisões: [RETOMAR.md](RETOMAR.md).

---

## Bloco 0 — Antes de abrir o Packet Tracer · 5 min

**O ponto que mais dá retrabalho:** o script que roda no simulador é uma **cópia** colada dentro
do nó. Editar `src/*.py` no repositório não muda nada lá dentro. Três scripts mudaram em 21/09 e
precisam ser recolados:

| Nó | Arquivo | O que mudou |
|---|---|---|
| Central | `src/broker_central.py` | painel web (`HTTPServer` :80, rotas `/` e `/estado`) |
| Sala | `src/zona_sala.py` | modo viagem corta AC + Fan e pinta o RGB de azul |
| Quarto | `src/zona_quarto.py` | modo viagem corta AC e umidificador e suspende a luz de presença |

O `zona_jardim.py` só ganhou comentário — recolar é opcional.

- [ ] Abrir os três arquivos num editor, prontos para copiar
- [ ] `python3 verificacao/verificar.py` → tem que dizer **TUDO CERTO**

---

## Bloco 1 — Abrir o arquivo e inventariar · 10 min

O arquivo do projeto é o **`src/IFMA-MQTT.pkt`**, aberto pelo Packet Tracer do Windows em:

```
\\wsl.localhost\Ubuntu-26.04\home\ccfernandes\projetos\ifma-smart-home-mqtt\src\IFMA-MQTT.pkt
```

Ele é de **04/07/2026**, anterior aos scripts finais: tem a rede base e as zonas validadas em
julho, mas provavelmente **não tem** Cozinha, Quarto e Jardim. O conteúdo não dá para conferir
fora do simulador — o PT 9 grava o `.pkt` cifrado, então o inventário abaixo é manual mesmo.

1. Abrir o arquivo pelo caminho acima.
2. Conferir quais nós existem e anotar:

| Nó | IP | Existe? |
|---|---|---|
| Switch + PC0 | .10 | ☐ |
| Central (SBC) | .100 | ☐ |
| Perímetro (MCU) | .21 | ☐ |
| Sala (SBC) | .22 | ☐ |
| Cozinha (SBC) | .23 | ☐ |
| Quarto (SBC) | .24 | ☐ |
| Jardim (SBC) | .25 | ☐ |
| Garagem (MCU) | .26 | ☐ |
| RFID Reader | .33 | ☐ |

3. **Salvar uma cópia** antes de mexer: `Arquivo → Salvar como` → `IFMA-MQTT_2026-09-21.pkt`.
   O `.pkt` é binário e versionado no git: sem cópia, um erro de montagem não tem desfazer.

**Checkpoint:** você sabe exatamente o que falta montar.

---

## Bloco 2 — Recolar os três scripts · 10 min

Para cada um dos três nós (Central, Sala, Quarto):

1. Clicar no nó → aba **Programming**.
2. **Stop** no script em execução (se estiver rodando).
3. Abrir o arquivo do projeto, **selecionar tudo e substituir** pelo conteúdo novo.
4. **Run**.
5. Olhar o terminal do próprio nó.

**O que a Central deve imprimir no arranque:**

```
Broker ouvindo na porta 1883
Painel web em http://192.168.1.100:80
```

**O `HTTPServer` foi validado no build 9.0.1.0858 em 21/09** — o painel abriu no navegador do PC0
com as tabelas e a faixa de situação. Se mesmo assim a segunda linha não aparecer no seu arranque,
o problema é local: `from http import *` falhando ou `HTTPServer.start(80)` retornando erro.

**Checkpoint:** a Central sobe com as duas linhas e as zonas já existentes reconectam
("Zona conectada: 192.168.1.xx").

---

## Bloco 3 — ✅ RESPONDIDO em 21/09 · o que sobra são 5 min

**`Environment.get("Smoke")` funciona.** A prova veio de graça: a Cozinha subiu e registrou
`AVISO: sem conexao com o broker -- fumaca nao publicado`. No `verificar_perigo()` a leitura da
fumaça acontece duas linhas antes da tentativa de publicar, então chegar à publicação significa
que o `get("Smoke")` retornou sem erro. A última incógnita capaz de mudar a arquitetura caiu.

O que ainda vale fazer, e é rápido: **ver o valor se mexer**. Saber que o ID existe não é o mesmo
que ver a Cozinha reagir — o limiar é de 20%, e a emissão natural do Old Car é de ~3%/hora
simulada. Rode `src/diag_smoke.py` num SBC avulso, **no mesmo contêiner físico da Cozinha**, e
deixe a injeção ligada: o valor sobe a 30/h e você vê sprinkler, janela, fan e alarme dispararem
dentro da sessão.

1. Arrastar um **SBC-PT avulso**, sem cabo IoT e sem IP — o pacote `environment` não usa rede.
2. Colocá-lo **no mesmo contêiner físico da Cozinha**, no Physical Workspace. Em outro cômodo ele
   lê outro ar e mostra zero para sempre.
3. Programming → New → *Empty — Python* → colar `src/diag_smoke.py` → **Run**.
4. Acompanhar a leitura subindo e a Cozinha reagir ao cruzar 20%.
5. Ao terminar, **Stop** e apagar o SBC de diagnóstico.

> Se preferir não mexer no ambiente simulado, ponha `INJETAR = False` no topo do script: ele só lê.

**Se nenhuma funcionar:** a Cozinha perde a leitura ambiental de fumaça e passa a depender só de
`"CO"`, que já está confirmado. Nesse caso, anote e **não monte a Cozinha ainda** — é decisão de
projeto, não de bancada.

**Checkpoint:** você viu a Cozinha disparar por fumaça, e não só o ID responder.

---

## Bloco 4 — Montar as três zonas que faltam · 45 a 60 min

Para cada zona: arrastar o **SBC-PT**, conectar ao switch, configurar IP, ligar os dispositivos
com **IoT Custom Cable** nas portas exatas e colar o script.

**Cozinha — SBC · 192.168.1.23**
`D0` Temperature · `D1` Humidity · `D2` Fire Sprinkler · `D3` Window · `D4` Fan · `D5` Alarm
⚠️ Não ligar Smoke/CO Detector por cabo: são Smart Things, lidos por `environment`.

**Quarto — SBC · 192.168.1.24**
`D0` Temperature · `D1` Humidity · `D2` Photo · `D3` Motion · `D4` AC · `D5` Humidifier ·
`D6` Smart LED · `D7` Window

**Jardim — SBC · 192.168.1.25**
`D0` Water Level · `D1` Wind · `D2` ATM Pressure · `D3` Photo · `D4` Lawn Sprinkler · `D5` Drain ·
`D6` Light

**Ordem de subida:** Central primeiro, sempre. Depois as zonas, uma de cada vez, conferindo no
terminal da Central a linha "Zona conectada" antes de ir para a próxima.

**Checkpoint:** a Central registrou seis zonas conectadas.

---

## Bloco 5 — O teste que fecha o projeto · 15 min

1. Abrir o **PC0** → *Desktop* → **Web Browser**.
2. Ir para `http://192.168.1.100`.

**O que você deve ver:** faixa verde com "CASA OK", a contagem de zonas conectadas e **seis
tabelas** — cozinha, garagem, jardim, perímetro, quarto e sala — cada uma com os valores atuais.
A página se recarrega sozinha a cada 5 segundos.

3. Conferir dois ou três valores contra o que a zona correspondente loga no terminal dela.
4. Abrir `http://192.168.1.100/estado` e verificar o JSON bruto.

**Se a página não abrir:** confirme IP e máscara do PC0 e se a Central logou a linha do painel no
arranque. O navegador do PT não distingue "sem rota" de "servidor fora do ar".

**Se abrir com menos de seis tabelas:** a zona ausente não publicou nada ainda — olhe o terminal
dela antes de mexer no painel. Zona sem conexão continua automatizando e só loga o aviso, então
silêncio no painel não significa zona parada.

**Checkpoint:** as seis zonas aparecem no painel. É o caminho zona → Central → tela inteiro.

---

## Bloco 6 — Modo viagem e cenários · 30 min

1. **Modo viagem:** apertar o Push Button da Central (`D0`).
   - Painel: faixa azul, "Modo: viagem".
   - Sala: AC e Fan desligam, RGB fica azul.
   - Quarto: AC e umidificador desligam; movimento não acende mais o Smart LED.
   - Cozinha e Jardim: **não mudam** — é o comportamento projetado.
   - Apertar de novo volta ao normal.

2. **Gás:** ligar o **Old Car** perto da Garagem → Fan, porta e alarme locais + faixa vermelha
   "ALERTA DE GAS" no painel e no LCD da Central.

3. **Campainha:** Push Button do Perímetro → Home Speaker na Central e "VISITANTE" no painel.

4. **RFID:** aproximar o Card (ID 1005) do Reader → Central abre a porta do Perímetro por 5s e
   registra "ACESSO LIBERADO".

**Checkpoint:** os quatro cenários se refletem no painel, não só nos LEDs.

---

## Bloco 7 — Fechar · 15 min

- [ ] Salvar o `.pkt`
- [ ] Anotar o que o Bloco 3 devolveu sobre `Smoke`
- [ ] `python3 verificacao/verificar.py`
- [ ] Commitar o `.pkt` atualizado
- [ ] Marcar no README: montagem da topologia e documentação final

Se algum bloco falhar, o que interessa registrar é a **mensagem exata** do terminal do nó — é com
ela que dá para decidir se é erro de montagem, de API ou de código.
