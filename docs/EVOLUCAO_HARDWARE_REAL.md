# Evolução para Hardware Real

> **Status:** roadmap / visão futura. A versão atual do projeto roda 100% no Cisco Packet Tracer.
> Este documento registra como o V4 migraria para **dispositivos físicos reais**, e por que a arquitetura já foi projetada pensando nisso.

---

## 1. Por que a arquitetura já é "de verdade"

As escolhas de design do V4 **não são específicas do simulador** — são o padrão de produção de IoT:

- **Broker central + nós de borda** = topologia clássica (ex.: Mosquitto + ESP32).
- **Publish/subscribe com tópicos** `casa/<zona>/<grandeza>` = prática padrão de MQTT.
- **Payloads JSON** = formato universal entre dispositivos.
- **Uma zona = um controlador** = como se distribui sensores fisicamente numa casa.

Ou seja: o projeto no Packet Tracer é um **protótipo fiel**, não uma maquete descartável. Migrar para hardware é trocar a *implementação*, não a *arquitetura*.

---

## 2. Tradução Simulação → Hardware Real

| Camada | Packet Tracer (V4) | Hardware real |
|---|---|---|
| Broker / Hub | SBC + `TCPServer:1883` | **Raspberry Pi + Mosquitto** (MQTT nativo) |
| Nós de borda | SBC / MCU | **ESP32** (WiFi + ADC + MicroPython) |
| Protocolo | TCP + JSON (padrão MQTT emulado) | **MQTT nativo** (`paho-mqtt` no Pi, `umqtt` no ESP32) |
| Dashboard | HTML + JS | **Node-RED** ou web via MQTT-over-WebSocket |
| GPIO | `digitalRead` / `analogRead` / `customRead` | `RPi.GPIO`, `machine.ADC`, libs por componente |

**Detalhe importante:** a nossa decisão "Opção B → C" (TCP+JSON evoluindo para MQTT real) **se resolve sozinha** no hardware. No mundo físico o MQTT nativo é o caminho *mais fácil* — a limitação do PT ("sem pacote Python `mqtt`") simplesmente não existe. Já projetamos pensando em MQTT; só troca o transporte.

---

## 3. A inversão RPi ↔ ESP32 (ponto didático)

No Packet Tracer, colocamos as zonas de clima (analógicas) no **SBC** porque a MCU tinha o bug das portas analógicas. **No hardware real, o mapeamento se inverte:**

- O **Raspberry Pi não tem entrada analógica** — precisa de um ADC externo (ex.: MCP3008).
- O **ESP32 tem ADC nativo + WiFi** — logo as zonas com muitos sensores analógicos ficam **melhores num ESP32** ("MCU") do que num Raspberry ("SBC").

O simulador **inverteu** a alocação natural. Entender essa inversão demonstra domínio real das diferenças entre um computador de placa única (Raspberry) e um microcontrolador (ESP32/Arduino) — muito além de decorar o comportamento do PT.

---

## 4. Mapa de componentes reais

### Sensores
| Dispositivo (PT) | Componente real | Interface |
|---|---|---|
| Motion Sensor | PIR HC-SR501 | digital |
| Push Button | botão + resistor pull-up | digital |
| RFID Reader | RC522 | SPI |
| Temperature + Humidity | **DHT22** (é o "Humiture Sensor") | 1-wire |
| Photo Sensor | LDR + divisor, ou BH1750 | analógico / I2C |
| ATM Pressure | BMP280 / BME280 | I2C |
| Water Level | boia (float switch) ou capacitivo | digital / analógico |
| Wind Sensor | anemômetro de pulso | digital (contagem) |
| Smoke | MQ-2 | analógico |
| CO | MQ-7 | analógico |
| CO₂ | **MH-Z19B (NDIR)** — os MQ não medem CO₂ com precisão | UART |

### Atuadores
| Dispositivo (PT) | Componente real | Controle |
|---|---|---|
| Door / Garage Door | servo SG90 ou motor + relé | PWM / relé |
| Window | servo / atuador linear | PWM / relé |
| Siren / Alarm | buzzer ou sirene 12V + relé | digital / relé |
| Camera | ESP32-CAM ou webcam no Pi | — |
| Fan / AC / Humidifier | relé + carga | relé |
| Fire/Lawn Sprinkler, Drain | válvula solenoide / bomba + relé | relé |
| LED / Smart LED | LED + resistor | digital / PWM |
| RGB LED | LED RGB (3 canais PWM) | PWM |
| LCD | LCD 16x2 I2C | I2C |
| Home Speaker | DFPlayer Mini ou buzzer | UART / digital |

---

## 5. Stack recomendada

```
        ┌───────────── Raspberry Pi (Hub) ─────────────┐
        │  Mosquitto (broker MQTT :1883)               │
        │  Node-RED (lógica global + dashboard)         │
        └───▲───────▲───────▲───────▲──────────────────┘
            │ WiFi  │       │       │   (MQTT nativo)
         ESP32   ESP32   ESP32   ESP32 ...
        Perímetro Sala  Cozinha  Jardim ...
```

- **Hub:** Raspberry Pi com Mosquitto + Node-RED (Node-RED substitui bem a "lógica cross-zone" da Central).
- **Bordas:** ESP32 por zona (WiFi + ADC nativo), MicroPython ou framework Arduino.
- **Broker:** Mosquitto local (ou nuvem: HiveMQ, AWS IoT Core) — mantém os mesmos tópicos `casa/<zona>/<grandeza>`.

---

## 6. MVP faseado (recomendado)

7 nós físicos é um projeto real: custo, montagem, solda, pull-ups, fontes. **Não construir tudo de uma vez.** Fases sugeridas:

1. **Fase 1 — Prova de pipeline:** Raspberry Pi (Mosquitto) + **1 ESP32 na Garagem** com sensor **MQ-7 (CO)**. Valida ponta-a-ponta e já é um detector de monóxido *genuinamente útil* numa garagem real.
2. **Fase 2 — Segunda zona + dashboard:** adiciona a Sala (DHT22 + PIR + relés) e o Node-RED.
3. **Fase 3 — Escala:** demais zonas conforme orçamento e tempo.

---

## 7. Diferenças que o mundo físico impõe (não existem no PT)

- Alimentação e fontes (3.3V/5V/12V), reguladores, consumo.
- Resistores de pull-up/pull-down, divisores de tensão, level shifting 3.3V↔5V.
- Ruído em leituras analógicas (calibração, média de amostras).
- Sensores de gás precisam de **aquecimento/calibração** (o MQ-7 tem ciclo de aquecimento).
- Segurança elétrica ao chavear cargas AC (relés, isolamento).
- Robustez de rede (reconexão WiFi, QoS do MQTT, last will/testament).

---

> Este roadmap conecta o protótipo (Packet Tracer) ao produto (hardware real), mostrando que a arquitetura foi pensada para ambos.
