# Levantamento de Dispositivos IoT — Cisco Packet Tracer 9.0.0

**Objetivo:** Catalogar todos os sensores, atuadores e componentes IoT do Packet Tracer 9.0.0 compatíveis com SBC-PT + Python, para definir a arquitetura do projeto V4 (MQTT).

**Data:** 29/06/2026  
**Método:** Pesquisa online na documentação oficial e comunidade. Pendente: verificação manual no simulador.

---

> ### ⚠️ Gotcha confirmado no PT (03/07/2026): "Direct Control" exige ALT+clique, não clique normal
>
> Testando o Rocker Switch (usado para ligar o Heating Element), o `digitalRead()` do lado receptor ficava travado em `0` mesmo com o interruptor "ligado" na tela. Depois de descartar I/O Config, slot errado e polaridade, a causa era o **gesto de clique**: a doc do device é internamente contraditória (`"Usage: Click"` vs `"Direct Control: ALT+Click"`), e é o **ALT+clique** que de fato alterna o estado digital de saída — um clique normal só seleciona o dispositivo (abre o painel dele), sem mudar o sinal.
>
> **Regra geral:** qualquer dispositivo cuja doc diga `Direct Control: ALT-click to interact` (Fan, Old Car, Switch, e provavelmente outros "instrumentos de teste" do palette) precisa de **ALT+clique**, não clique normal, para realmente alternar o estado. Vale a pena testar isso primeiro, antes de suspeitar de fiação ou I/O Config, quando um `digitalRead`/`analogRead` voltar sempre o mesmo valor num device controlado manualmente.
>
> De quebra, esse teste confirmou de novo que **`HIGH = 1023`** (não `1`) também no motor de script dos Smart Things — mesma convenção já vista no SBC/MCU.

## 1. Componentes via SBC-PT (conexão por IoT Custom Cable)

Estes dispositivos conectam-se diretamente às portas D0–D9 do SBC via cabo IoT customizado. Não possuem interface de rede própria — dependem do SBC para lógica e comunicação.

### 1.0 Controladores: SBC vs MCU (portas físicas) — VERIFICADO NO PT 9.0.0

| Controlador | Analogia | Portas físicas | Diretivas por porta | Rede |
|---|---|---|---|---|
| **SBC-PT** | Raspberry Pi | **10 portas D0–D9** (flexíveis) | cada porta faz `digital` / `analog` / `custom` (Read+Write) | robusta (TCP/MQTT) |
| **MCU-PT** | Arduino | **6 usáveis D0–D5** + **4 analógicas A0–A3** | **D0–D5 são flexíveis: `digital`/`analog`/`custom` (Read+Write)**; o bug do V3 é só nas portas analógicas dedicadas **A0–A3** → evitá-las | enxuta (verificar `tcp`) |

**Consequências de projeto:**
- No SBC as 10 portas são intercambiáveis: a mesma porta faz `analogRead`, `digitalWrite` ou `customWrite` (foi assim que o V3 usou `analogWrite` no LED RGB numa porta "digital"). Sensores analógicos no SBC não precisam de portas dedicadas.
- Na MCU, as **6 portas D0–D5 são flexíveis** e aceitam inclusive `analogRead`/`analogWrite` (igual às do SBC, só que em menor número). O bug do V3 é **exclusivo das portas analógicas dedicadas A0–A3** → evitá-las por completo. Portanto o limite real da MCU é **6 portas usáveis (D0–D5)**, e uma zona cabe em MCU se tiver **≤ 6 dispositivos** — com ou sem sensor analógico, desde que ligados a D0–D5.

### 1.1 SENSORES (Entrada)

| # | Dispositivo | Tipo de Porta | API de Leitura | O que Detecta |
|---|-------------|:---:|---|---|
| 1 | **Motion Sensor** | Digital | `digitalRead()` → HIGH/LOW | Presença/movimento (PIR) |
| 2 | **Smoke Detector** ⚠️ | ~~Digital~~ **Smart Thing (assumido)** | `Environment.get("Smoke")` — **inferido, não testado**, ver nota abaixo | Fumaça no ambiente |
| 3 | **Carbon Dioxide Detector** ⚠️ | ~~Digital~~ **Smart Thing** | ver nota abaixo | Nível de CO₂ |
| 4 | **Carbon Monoxide Detector** ⚠️ | ~~Digital~~ **Smart Thing** | ver nota abaixo | Nível de CO |
| 5 | **Push Button** | Digital | `digitalRead()` → HIGH/LOW | Interação manual (pressão) |
| 6 | **Temperature Sensor** ✅ | Analógico | `analogRead()` → 0–1023 = **−100 °C a +100 °C** (linear; doc do device confirmada 03/07/2026) | Temperatura ambiente |
| 6b | ~~**Temperature Monitor**~~ ⚠️ | **Smart Thing** | **NENHUMA API** (`Direct/Local/Remote Control: N/A`, sem Data Specifications) — só exibe a temperatura visualmente p/ Registration Server. **Não confundir com o Temperature Sensor** (nomes parecidos, palette próximo): cabeado num controlador, daria o clássico "sempre 0". | Display de temperatura |
| 7 | **Humidity Sensor** | Analógico | `analogRead()` → 0–1023 | Umidade do ar |
| 8 | **Photo Sensor** | Analógico | `analogRead()` → 0–1023 | Luminosidade (luz visível) |
| 9 | **Water Level Monitor** | Analógico | `analogRead()` → 0–1023 | Nível de água |
| 10 | **Wind Sensor** | Analógico | `analogRead()` → 0–1023 | Velocidade do vento |
| 11 | **ATM Pressure Sensor** | Analógico | `analogRead()` → 0–1023 | Pressão atmosférica |
| 12 | **Humiture Sensor** | Analógico | `analogRead()` → 0–1023 | Temperatura + umidade (combo) |
| 13 | **Sound Frequency Detector** | Analógico | `analogRead()` → 0–1023 | Frequência sonora (pitch) |
| 14 | **Potentiometer** | Analógico | `analogRead()` → 0–1023 | Interação manual (giro) |
| 15 | **RFID Reader** ⚠️ | ~~Custom~~ **Smart Thing** | script embutido + `tcp` — ver nota abaixo | Cartões/tags RFID |
| 16 | **Metal Detector** ⚠️ | Custom? | `customRead()` — **não confirmado, checar doc do device** | Presença de metais |

**Totais:** 5 digitais, 9 analógicos, 2 custom = **16 tipos de sensores**

> ### ⚠️ Gotcha confirmado no PT (02/07/2026): CO/CO₂ Detector NÃO são GPIO
>
> A pesquisa online original catalogou o Carbon Monoxide/Dioxide Detector como componente digital comum. **Isso estava errado.** Testando no simulador, `digitalRead()` e `analogRead()` sempre retornam `0` nesses dispositivos, mesmo com um Old Car ligado ao lado. A própria janela de documentação do dispositivo dentro do PT explica por quê:
>
> ```
> Carbon Monoxide Detector
> Features: Registration Server Compatible
> Alarm will go off when it detects a Carbon Monoxide level of 20%
> Direct Control: N/A   Local Control: N/A   Remote Control: N/A
> Message Format: [state],[level]
> ```
>
> `Direct/Local/Remote Control: N/A` significa que o dispositivo **não tem nenhuma API programável** — ele só se registra visualmente num *Registration Server* (um painel/dashboard), não expõe nada que um script Python consiga ler. Na prática, é um sensor "decorativo" para quem só quer ver um dashboard, inútil para automação via código.
>
> **A leitura real do gás usa o pacote `environment`**, que lê a concentração *ambiente* simulada diretamente — sem precisar do dispositivo detector nem de porta física:
>
> ```python
> from environment import *
> nivel_co  = Environment.get("CO")   # retorna float em % (ex.: 0.06)
> nivel_co2 = Environment.get("CO2")  # retorna float em %
> ```
>
> Confirmado empiricamente no PT 9.0.0 (`Environment.get('CO') = 0.0606...`, `getValueWithUnit → "0.06 %"`). O Old Car contribui ~1%/hora de CO e ~2%/hora de CO₂ (doc oficial Cisco) — **é lento**: em um teste curto o valor sobe pouco. Usar o mesmo limiar do dispositivo oficial (**20%**) para disparar o alarme na lógica.
>
> **Lição:** nem todo "sensor" do palette de Components é GPIO. Sempre que um `digitalRead`/`analogRead` voltar zero fixo, olhar a doc do próprio dispositivo (aba de ajuda no PT) antes de suspeitar do código — ela costuma dizer explicitamente se é `Direct Control` (GPIO) ou só `Registration Server Compatible` (rede/Smart Thing). O mesmo problema é suspeito no Smoke Detector da Cozinha — a confirmar.

> ### ⚠️ Gotcha confirmado no PT (02/07/2026): RFID Reader não tem NENHUMA API — nem via rede
>
> Mesmo padrão do CO/CO₂ Detector, mas **sem workaround**. A doc oficial do dispositivo no PT:
>
> ```
> RFID Reader
> Features: Registration Server compatible
> Direct Control: N/A   Local Control: N/A   Remote Control: N/A
> Message Format: [Card Id],[status]   status: 0=Valid, 1=Invalid, 2=Waiting
> ```
>
> Assim como o CO Detector, `Local Control: N/A` confirma que não há `customRead()`/`customWrite()` — não é um Component GPIO. A diferença: para o gás existia o pacote `environment` como rota alternativa de leitura; **para RFID não existe equivalente** — não há um "Environment.get" para crachás. O RFID Reader só existe para alimentar visualmente um Registration Server (dashboard), sem nenhum caminho de leitura por script, nem local nem por rede.
>
> **REVIRAVOLTA (02/07/2026): RFID Reader REABILITADO como nó MQTT independente.** A conclusão acima ("sem nenhum caminho de leitura") valia para *acessar o Reader de fora*. Mas todo Smart Thing tem um **script Python próprio, editável** (aba Programming do device) — e testamos: **esse motor de script tem `tcp` e `json`**. Ou seja, em vez de outro nó tentar ler o Reader, **o próprio Reader publica no broker**: `src/thing_rfid_reader.py` substitui o script padrão (que falava com o Registration Server via `ioeclient`) por um cliente TCP que detecta o cartão por proximidade física e publica `casa/perimetro/rfid`. Testado de ponta a ponta: tag `1005` lida e publicada.
>
> **Descobertas sobre o motor de script dos Things** (diferente do SBC/MCU):
> - Os exemplos da Cisco são **Python 2** (`xrange`, `delay()`/`idle()` em vez de `sleep()`) — modernizar ao adaptar.
> - `devicesAt(x, y, dx, dy)` retorna um **dict** `{'0': 'NomeDevice', '1': ...}` (chave = índice em string, valor = nome). Indexar como lista (`devices[0]`) dá `KeyError: 0`.
> - `getDeviceProperty(nome, "CardID")` funciona — a propriedade é `"CardID"` (o `var CARD_ID` do script JS do Card vira essa propriedade).
> - ⚠️ **I/O Config:** o RFID Reader vem de fábrica com **0 Digital Slots e 0 Analog Slots** — é preciso abrir a aba **Advanced → I/O Config** e mudar **Digital Slots para 1** (e conferir o Network Adapter) para o setup funcionar.
>
> **Lição (a mais importante do projeto):** `Direct/Local/Remote Control: N/A` significa que o device não é controlável *de fora* — mas o script *interno* dele é programável e tem acesso à rede. **Qualquer Smart Thing pode virar um nó pub/sub** rodando nosso protocolo. O RFID Card continua sendo só um prop (ID em JavaScript, sem rede), mas o Reader é um nó de pleno direito (IP 192.168.1.33). Ver o passo a passo no [MONTAGEM_PACKET_TRACER.md](MONTAGEM_PACKET_TRACER.md).

### 1.2 ATUADORES (Saída)

| # | Dispositivo | Tipo de Porta | API de Escrita | O que Faz | Impacto Ambiental |
|---|-------------|:---:|---|---|---|
| 1 | **LED** | Digital | `digitalWrite()` | Luz indicadora (1% max) | Luz visível |
| 2 | **Smart LED / Dimmable LED** | Digital | `digitalWrite()` | Luz ajustável (3% max) | Luz visível |
| 3 | **RGB LED** | Digital* | `analogWrite()` PWM | Luz colorida (2% max) | Luz visível |
| 4 | **Light** | Digital | `digitalWrite()` | Iluminação forte (20% max) | Luz visível |
| 5 | **Fan** ⚠️ | ~~Digital~~ **Custom** | `customWrite()` — ver nota abaixo | Ventilação | Vento, temp, umidade |
| 6 | **AC / Air Conditioner** ✅ | Digital | `digitalWrite()` HIGH/LOW — **CONFIRMADO** (doc do device, 03/07/2026) | Refrigeração (−10°C/h, −2% umid/h) | Temp, umidade |
| 7 | **Furnace / Heating Element** ⚠️ | Digital? | `digitalWrite()` — **não confirmado, checar doc do device** | Aquecimento (+10°C/h, −2% umid/h) | Temp, umidade |
| 8 | **Humidifier** | Digital | `digitalWrite()` | Umidificação (+1% umid/h) | Umidade |
| 9 | **Fire/Ceiling Sprinkler** | Digital | `digitalWrite()` | Sprinkler de teto (0.1 cm/s) | Nível água |
| 10 | **Lawn/Floor Sprinkler** | Digital | `digitalWrite()` | Sprinkler de chão (0.1 cm/s) | Nível água |
| 11 | **Drain Actuator** | Digital | `digitalWrite()` | Drenagem (−0.5 cm/s) | Nível água |
| 12 | **Home Speaker** | Digital | `digitalWrite()` | Som (65 dB, 20–60 CPS) | Som |
| 13 | **Piezo Speaker** | Digital | `digitalWrite()` | Som baixo (10 dB, 20 CPS) | Som |
| 14 | **Servo** | Digital | `digitalWrite()` | Motor servo | Movimento mecânico |
| 15 | **Door** | Custom | `customWrite()` | Porta de entrada | Dispersão de gás |
| 16 | **Garage Door** | Custom | `customWrite()` | Porta de garagem | Gás, umidade, temp |
| 17 | **Window** | Custom | `customWrite()` | Janela | Dispersão mínima |
| 18 | **LCD Display** | Custom | `customWrite()` | Painel texto 2 linhas | — |
| 19 | **Webcam / Camera** | Custom | `customWrite()` | Câmera de vigilância | — |
| 20 | **Siren** | Custom | `customWrite()` | Sirene de alarme | Som |

> *RGB LED usa `analogWrite()` em portas **digitais** do SBC que suportam PWM.

**Totais:** 14 digitais, 6 custom = **20 tipos de atuadores**

> ### ⚠️ Gotcha confirmado no PT (02/07/2026): Fan é Custom, não Digital
>
> Esta tabela de atuadores vem de pesquisa online, **não verificada dispositivo por dispositivo**. Já confirmamos que o **Fan** estava classificado errado: a doc oficial do dispositivo (aba de ajuda, dentro do PT) diz:
>
> ```
> Fan — Ceiling Fan
> Local Control: Connect device to MCU/Thing/SBC. Use the "customWrite" API
> Message Format: [state]   state: 0 = off, 1 = low speed, 2 = high speed
> ```
>
> Ou seja, `digitalWrite()` nunca funcionaria nele — é preciso `customWrite(porta, "0"/"1"/"2")`. Corrigido em `src/zona_garagem.py`.
>
> **Antes de programar qualquer atuador desta lista, verifique a doc do próprio dispositivo no PT** (clique nele e procure a aba/painel de ajuda) para confirmar o `Message Format` real — principalmente os que têm **múltiplos estados** (AC, Furnace, Humidifier, Servo, Speakers), que são os candidatos mais prováveis a serem `Custom` como o Fan, não `Digital`. O dispositivo **Alarm** usado na Garagem também não está claro se é o mesmo que "Siren" nesta tabela (Custom) — checar antes de confiar no `digitalWrite()` atual do `zona_garagem.py`.

### 1.3 OBJETOS AMBIENTAIS (não conectam ao SBC)

Afetam o ambiente simulado do PT. Úteis para criar cenários de teste para os sensores.

| Dispositivo | Função |
|-------------|--------|
| **Old Car** | Emissões: CO, CO₂, fumaça, temperatura |
| **Solar Panel** | Geração de eletricidade a partir de luz |
| **Wind Turbine** | Geração de eletricidade a partir de vento |

### 1.4 SMART THINGS (conectam via rede — NÃO via SBC)

Possuem interface de rede própria. Registram-se via Home Gateway ou Registration Server. Controlados por JavaScript/Blockly, não Python.

- Smart Light/Lamp, Smart Fan, Smart Door, Smart Window, Smart AC
- Coffee Maker, Thermostat, Smoke Alarm (Thing)
- Bluetooth Speaker

**Decisão do projeto:** Foco nos COMPONENTES via SBC + Python. Smart Things ficam como opção secundária.

---

## 2. Python API Completa do SBC-PT

Fonte: [Python API Reference (PT 7.3.1+)](https://tutorials.ptnetacad.net/help/default/iot_python_api.htm)

### 2.1 Pacotes Disponíveis

| Pacote | Import | Função Principal |
|--------|--------|-----------------|
| **gpio** | `from gpio import *` | Portas digitais/analógicas/custom + eventos |
| **time** | `from time import *` | sleep, delay, ctime, uptime, strftime, etc. |
| **networking** | `from networking import *` | localIP(), subnetMask(), gatewayIP() |
| **tcp** | `from tcp import *` | TCPClient, TCPServer |
| **udp** | `from udp import *` | UDPSocket |
| **http** | `from http import *` | HTTPClient, HTTPServer (interno PT) |
| **realhttp** | `from realhttp import *` | RealHTTPServer, RealHTTPClient, **WebSocket** |
| **realtcp** | `from realtcp import *` | RealTCPClient, RealTCPServer (rede real) |
| **realudp** | `from realudp import *` | RealUDPSocket (multicast) |
| **email** | `from email import *` | EmailClient (SMTP) |
| **json** | `from json import *` | dumps(), loads() |
| **ioeclient** | `from ioeclient import *` | Integração com Registration Server |
| **os / file** | `import os` | Arquivos: open, exists, mkdir, listdir |
| **usb** | `from usb import *` | USB serial + PTmata (SBC↔MCU) |
| **physical** | `from physical import *` | Posição, visual, som, propriedades |
| **environment** | `from environment import *` | Leitura do ambiente simulado |

### 2.2 Funções GPIO

```
pinMode(slot, mode)                 # mode: INPUT ou OUTPUT
digitalRead(slot) → int             # HIGH ou LOW
digitalWrite(slot, value)           # HIGH ou LOW
analogRead(slot) → int              # 0–1023
analogWrite(slot, value)            # aceita 0–1023, mas resolução real = 256 níveis (slots 0–255); 1023↔255, 0↔0
customRead(slot) → str              # Lê string
customWrite(slot, value)            # Escreve string
add_event_detect(slot, callback)    # Interrupção ao mudar estado
remove_event_detect(slot)           # Remove interrupção
```

### 2.3 Constantes

```
HIGH, LOW        # Estados digitais
INPUT, OUTPUT    # Modos de porta
```

### 2.4 TCP (base para pub/sub) — CONFIRMADO no PT 9.0.0 (02/07/2026)

```
# Cliente
client = TCPClient()
client.connect(ip, port) → bool
client.connected() → bool
client.send(data)
client.close()
client.onReceive(callback)             # CONFIRMADO: callback(data) -- UM argumento so
client.onConnectionChange(callback)
client.state() → int
client.remoteIP() → str
client.localIP() → str

# Servidor
server = TCPServer()
server.listen(port)                    # CONFIRMADO: funciona, inclusive na MCU-PT
server.stop()
server.onNewClient(callback)           # CONFIRMADO: callback(client)
```

> ⚠️ **Gotcha confirmado:** `onReceive(callback)` chama o callback com **um único argumento** (`data`), não `(client, data)` — mesmo no lado do servidor, onde `client.onReceive()` é registrado por conexão individual (o objeto `client` já fica "amarrado" ao callback, não precisa ser passado de novo). Erro visto no PT: `TypeError: ao_receber() missing 1 required argument: data`.

### 2.5 HTTP Server

```
HTTPServer.route(path, callback)
HTTPServer.start(port) → bool
HTTPServer.stop()

# Response
response.send(content)
response.setContentType(type)
response.sendFile(filePath)
response.sendNotFound()
```

### 2.6 Email

```
EmailClient.setup(email, server, username, password)
EmailClient.send(address, subject, body)
EmailClient.receive()
EmailClient.onSend(callback)
EmailClient.onReceive(callback)
```

### 2.7 RealHTTP + WebSocket

```
server = RealHTTPServer()
server.start(port)
server.route(url_pattern, request_types, callback)
server.websocket(url_pattern, callback)    # WebSocket!
server.isListening() → bool

client = RealHTTPClient()
client.get(url)
client.post(url, data)
client.onDone(callback)

ws = RealWSClient()
ws.connect(url)
ws.send(data)
ws.onReceive(callback)
```

### 2.8 JSON

```
dumps(obj) → str        # Objeto → string JSON
loads(string) → object  # String JSON → objeto
```

### 2.9 Environment — CONFIRMADO no PT 9.0.0 (02/07/2026)

```
Environment.get(envID) → float                # CONFIRMADO: envID "CO"=0.0606, "CO2"=0.157
Environment.getMetricValue(envID) → float      # CONFIRMADO: mesmo valor que .get()
Environment.getValueWithUnit(envID) → string   # CONFIRMADO: "0.06 %"
Environment.getUnit(envID) → string            # CONFIRMADO: "%"
Environment.getTimeInSeconds() → int           # CONFIRMADO: funciona (hora do dia, 0-86400)
Environment.getVolume() → float                # CONFIRMADO: usado pelo script embutido do Heating Element
Environment.setContribution(envID, rate, limit, cumulative)  # CONFIRMADO: é a API de ESCRITA no ambiente (ver nota)
Environment.setGlobalProperty(name, value)                    # não testado
Environment.getGlobalProperty(name) → string                  # não testado
Environment.setTimeMultiplier(float)           # existe na API C++; não testado (ficou desnecessário)
```

**envIDs oficiais confirmados até agora:** `"CO"`, `"CO2"` (testados na Garagem), `"Ambient Temperature"`, `"Humidity"` (confirmados no código embutido do Heating Element).

**Como os devices ambientais funcionam por dentro (lido do script embutido do Heating Element, 03/07/2026):** o device chama `Environment.setContribution(envID, taxa, limite, True)` a cada segundo, com a **taxa em unidades/segundo** (ex.: `10./3600` = 10 °C/hora) **escalada pelo volume do contêiner**: `taxa × VOLUME_AT_RATE / Environment.getVolume()` (referência `VOLUME_AT_RATE = 100000` cm³ = "escritório típico"). Aquecer um ambiente pequeno é mais rápido que um galpão.

> 💡 **Técnica de demo (a mais limpa):** como o script embutido dos devices é editável (mesma descoberta do RFID Reader), dá para **acelerar uma demonstração editando a constante de taxa no script do próprio device** — ex.: `TEMPERATURE_RATE = 10./60` faz o Heating Element aquecer 10 °C por *minuto* em vez de por hora. O ambiente esquenta DE VERDADE (sensores leem o valor real, AC combate de verdade) — mais honesto que rampa sintética em software, e sem tocar no código das zonas.

**Uso real (Garagem, CO/CO₂):** ver gotcha na seção 1.1 acima e o código em `src/zona_garagem.py`.

---

## 3. MQTT no Packet Tracer — Como Funciona

### Descoberta Importante

O PT **NÃO tem** pacote Python `mqtt` nativo. O MQTT existe como:

1. **Template de projeto Python** na aba "Programming" do SBC:
   - "MQTT Broker - (Python)" → instala como app Desktop
   - "MQTT Client - (Python)" → instala como app Desktop
2. **Protocolo de rede** suportado desde PT 7.1 — aparece como "MQTT packets" no modo simulação

### Opções de Arquitetura

| Opção | Descrição | Prós | Contras |
|-------|-----------|------|---------|
| **A** | MQTT via Desktop Apps | Protocolo real; visible no modo simulação | GPIO e MQTT desktop são processos separados |
| **B** | Pub/Sub sobre TCP em Python | Controle total; GPIO + rede integrados | Não é MQTT "puro" |
| **C** | Híbrido (TCP + MQTT Desktop) | Demonstra ambos os conceitos | Mais complexo de configurar |

### DECISÃO (30/06/2026): Opção B como backbone, evoluindo para C

Motivo técnico decisivo: **não há pacote Python `mqtt` nativo** → é impossível publicar MQTT de dentro do mesmo script que lê o GPIO. Isso inviabiliza a Opção A pura para automação integrada. Já `tcp` e `json` são nativos, permitindo um único script por nó que lê sensores E fala na rede.

- **Backbone (B):** Central roda `TCPServer.listen(1883)` (porta oficial MQTT) como broker. Zonas usam `TCPClient` e publicam JSON `{"topic":"casa/<zona>/<grandeza>","payload":...,"ts":...}`. Reproduz fielmente o padrão pub/sub (broker, topics, publish/subscribe).
- **Vitrine (C, evolução):** habilitar o serviço MQTT Broker real no IoT Server do PT para mostrar pacotes MQTT reais no modo simulação, sem que a automação dependa disso.
- **Alinha com IFMA:** tudo em funções `def`, sem classes.

---

## 4. Itens para Verificação Manual no PT 9.0.0

- [x] `analogWrite()` escala: **RESOLVIDO** — aceita 0–1023, quantizado em 256 níveis (slots 0–255); 1023↔255, 0↔0. Usar 0–1023 no código (como o V3).
- [x] Portas da MCU: **RESOLVIDO** — 6 usáveis D0–D5 (flexíveis) + 4 analógicas A0–A3 (bug do V3, evitar).
- [x] Switch escolhido: **2950-24** (o 2960-24TT não estava disponível; qualquer L2 de 24 portas serve).
- [x] MCU-PT suporta pacote `tcp`? **CONFIRMADO (02/07/2026)** — Garagem-MCU conectou ao broker.
- [x] CO/CO₂ Detector funcionam com `digitalRead`/`analogRead`? **NÃO** — são Smart Things (Registration Server), sem API programável. Ver gotcha na seção 1.1. Correção: pacote `environment`, confirmado funcionando.
- [x] RFID Reader é Component GPIO? **NÃO** — mas foi **REABILITADO como nó MQTT independente**: o script Python embutido do Thing tem `tcp`/`json` e publica direto no broker (`thing_rfid_reader.py`, testado). Requisito: I/O Config → Digital Slots 0→1. Ver gotcha na seção 1.1.
- [x] `onReceive(callback)` — **CONFIRMADO**: assinatura `(data)`, um argumento só.
- [x] `uptime()` — **CONFIRMADO**: funciona para cálculo de hold de estado.
- [x] Fan é `customWrite` (Custom), não `digitalWrite` — **CONFIRMADO e CORRIGIDO** via doc oficial do device.
- [x] `Environment.setTimeMultiplier()` — **CONTORNADO**: em vez de acelerar o ambiente real, `zona_garagem.py` usa `MODO_DEMO` (rampa em software, gateada pelo estado real do Old Car). Não foi necessário testar essa chamada.
- [ ] **HIPÓTESE (promissora, não testada):** um Smart Thing com slot adicionado via `Advanced → I/O Config` pode ser lido por MCU/SBC via cabo IoT, se o script embutido dele escrever o estado no próprio slot? Evidência a favor: o script original da Cisco no RFID Reader fazia `analogWrite(A1, state)` — só faz sentido se o slot for legível do outro lado do cabo. Se confirmada, abre uma 2ª rota (GPIO) para Things além da rota de rede já validada — útil quando não se quer depender do broker. Testar cabeando um Thing numa MCU e lendo com `digitalRead`/`customRead`.
- [ ] Smoke Detector da Cozinha: **aplicado direto o padrão da Garagem** (`environment`, sem testar GPIO primeiro) em `zona_cozinha.py`. `Environment.get("Smoke")` é **inferido** da doc do Old Car (lista fumaça como emissão, mesma família de CO/CO₂) mas **nunca testado empiricamente** — confirmar o nome exato do envID ao montar (se der erro, tentar variações como `"Smoke Detector"`).
- [ ] Metal Detector é Component GPIO de verdade? (não confirmado — mesma dúvida do RFID Reader)
- [x] Siren e Camera do Perímetro: **CONFIRMADOS (02/07/2026)** — `customWrite` simples ("0"/"1", liga/desliga) funciona nos dois.
- [ ] Template "MQTT Broker/Client - Python" existe na aba Programming? (relevante para a vitrine C, não bloqueia o backbone B)
- [ ] Listar TODOS os componentes em: End Devices > Components > Sensors
- [ ] Listar TODOS os componentes em: End Devices > Components > Actuators
- [ ] Testar conexão Humiture Sensor ao SBC — funciona com `analogRead()`?
- [ ] Verificar se Sound Frequency Detector existe como componente
- [ ] Verificar se ATM Pressure Sensor existe como componente

---

## Fontes

- [Packet Tracer IoT Tutorials](https://www.packettracernetwork.com/internet-of-things.html)
- [IoT Devices Configuration](https://www.packettracernetwork.com/internet-of-things/pt7-iot-devices-configuration.html)
- [MQTT Protocol in PT](https://www.packettracernetwork.com/internet-of-things/mqtt-protocol.html)
- [Python API Reference (PT 7.3.1)](https://tutorials.ptnetacad.net/help/default/iot_python_api.htm)
- [Python API Reference (Archive.org)](https://ia801707.us.archive.org/15/items/qt-5-web-engine-core/Cisco%20Packet%20Tracer%207.3.1/help/default/iot_python_api.htm)
- [MQTT Broker Setup Guide](https://anna-s.medium.com/how-to-set-up-an-mqtt-broker-and-clients-in-cisco-packet-tracer-4f63c9e3661b)
- [Smart Warehouse with IoT](https://wiredwhite.com/smart-warehouse-using-cisco-packet-tracer-and-iot-devices/)
- [IoT Systems Design Lab Book](https://orca.cardiff.ac.uk/id/eprint/175226/1/IOTLabBookPT.pdf)
