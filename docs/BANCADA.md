# Roteiro de bancada — fechar o V4

Sessão única, estimada em **2h30 a 3h**. Cada bloco termina com um checkpoint: se ele não
passar, pare ali e anote, porque os blocos seguintes dependem dele.

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

O `src/IFMA-MQTT.pkt` é de **04/07/2026**, anterior aos scripts finais. Ele tem a rede base e as
zonas validadas em julho, mas provavelmente **não tem** Cozinha, Quarto e Jardim.

1. Abrir `src/IFMA-MQTT.pkt`.
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

**Se a segunda linha não aparecer:** o `from http import *` falhou ou o `HTTPServer.start(80)`
retornou erro. Anote a mensagem exata — é a única parte do código de hoje que nunca rodou no
simulador, e a API de HTTP Server é declarada como "SBC only" na documentação do PT.

**Checkpoint:** a Central sobe com as duas linhas e as zonas já existentes reconectam
("Zona conectada: 192.168.1.xx").

---

## Bloco 3 — O teste que pode mudar a arquitetura · 15 min

`Environment.get("Smoke")` é a única incógnita que ainda pode forçar mudança de projeto, e a
Cozinha inteira depende dela.

1. Num SBC qualquer que já esteja montado, abrir **Programming** e rodar `src/diag_environment.py`.
2. Ver o que ele imprime para fumaça.
3. Se `"Smoke"` não existir, testar nas variações: `"Smoke Detector"`, `"smoke"`, `"Fire"`.

**Se nenhuma funcionar:** a Cozinha perde a leitura ambiental de fumaça e passa a depender só de
`"CO"`, que já está confirmado. Nesse caso, anote e **não monte a Cozinha ainda** — é decisão de
projeto, não de bancada.

**Checkpoint:** você tem o nome exato da grandeza, ou a confirmação de que ela não existe.

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
