# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este projeto

Projeto **V4** de automação residencial IoT simulada no **Cisco Packet Tracer 9.0.0**, desenvolvido como atividade prática de Redes/IoT no IFMA Campus Monte Castelo. É a evolução do projeto V3 (GPIO direto, 1 SBC, 10 dispositivos) para uma **arquitetura distribuída com MQTT**, múltiplos SBCs por zona e 30+ dispositivos IoT.

Não é um projeto de software convencional: o código Python roda como **MicroPython dentro do editor de cada SBC no Packet Tracer**, não no host. Por isso **não há comandos de build, lint ou test** — a "execução" é colar/rodar o script no SBC dentro do simulador e acionar sensores manualmente. Os artefatos centrais são o arquivo `.pkt` (topologia), os scripts Python dos SBCs e a documentação.

## Verificador

Não há build, lint nem teste — mas há um **verificador**, que torna executáveis as
regras normativas deste arquivo:

```bash
python3 verificacao/verificar.py
```

Ele confere estaticamente o que o simulador não perdoa: sintaxe, ausência de `class`
(restrição pedagógica), só pacotes que existem no PT, `customRead()` sempre com
`.strip()`, MCU sem as portas A0–A3, orçamento de portas por controlador, pino
repetido, comentário de pino divergente do valor, padrão dos tópicos MQTT, porta
única de broker e integridade do V3.

É o critério de pronto de qualquer alteração — inclusive das feitas por outro agente
de IA (ver `../FORCA-TAREFA.md`). Ao resolver um gotcha novo do simulador,
acrescente o teste correspondente: é o que impede o erro de voltar.

## Projeto V3 (referência — não modificar)

`/home/ccfernandes/projetos/ifma-smart-home-packet-tracer/` é o clone do projeto V3 original (github.com/ccfernandes600/ifma-smart-home-packet-tracer). Serve **apenas como referência** de arquitetura e código — **nunca editar**. Padrões herdados do V3 que valem para o V4:

- Lógica centralizada em uma função `processar_sistema(*args)` disparada por `add_event_detect()` em cada sensor (event-driven, não polling).
- `customRead()` retorna string com lixo → sempre `.strip()` e comparar caractere a caractere antes de usar.
- Máquina de estados de segurança com feedback redundante: atuadores + LCD + `print()` no terminal com timestamp `ctime()`.
- LED RGB usa `analogWrite()` em portas **digitais** do SBC (suportam PWM).

## Fonte de verdade dos dispositivos e da API

`docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md` é o catálogo autoritativo e **fonte única** de dispositivos e API: 16 sensores, 20 atuadores, a Python API completa do SBC-PT (16 pacotes) e como o MQTT funciona no PT. **Consultar antes de propor qualquer dispositivo ou chamada de API.** O arquivo distingue três classes que não devem ser confundidas:

- **Components** (via IoT Custom Cable nas portas D0–D9 do SBC) → controlados por Python. É o foco do projeto.
- **Smart Things** (interface de rede própria) → controlados por JavaScript/Blockly, **não Python**. Opção secundária.
- **Objetos ambientais** (Old Car, Solar Panel…) → não conectam ao SBC; servem para criar cenários de teste dos sensores.

## Decisões de arquitetura ainda abertas (verificar no simulador antes de codificar)

A seção 4 de `LEVANTAMENTO_DISPOSITIVOS_PT9.md` lista a verificação manual pendente. Dois pontos bloqueiam decisões de código:

- **`analogWrite()` — RESOLVIDO**: aceita a faixa 0–1023, mas a resolução real é 256 níveis (slots 0–255): 1023↔255, 0↔0 (PWM de 8 bits). Usar 0–1023 no código, como o V3; os presets RGB do V3 continuam válidos.
- **Orçamento de portas por controlador** (verificado no PT 9.0.0): **SBC-PT** = 10 portas D0–D9 intercambiáveis (cada uma faz digital/analog/custom). **MCU-PT** = 6 portas usáveis D0–D5 (também flexíveis — aceitam analog/digital/custom) + 4 analógicas dedicadas A0–A3. O bug do V3 é **exclusivo das A0–A3** (evitá-las); as D0–D5 fazem `analogRead/Write` normalmente. Portanto o gargalo da MCU é o **nº de portas (6)**, não o analógico. Regra de alocação: zona com **>6 dispositivos → SBC**; zona com **≤6 dispositivos → MCU-elegível** (analógico OK em D0–D5).
- **Arquitetura MQTT — DECIDIDA (Opção B, evoluindo para C)**: como não há pacote Python `mqtt` nativo, não dá para publicar MQTT do mesmo script que lê GPIO. Solução adotada: pub/sub sobre `tcp`+`json` (nativos). Central = `TCPServer.listen(1883)` (broker); zonas = `TCPClient` publicando JSON `{"topic":"casa/<zona>/<grandeza>","payload":...,"ts":...}`. Evolução planejada (C): habilitar o serviço MQTT Broker real no IoT Server só para a vitrine (mostrar pacotes MQTT reais no modo simulação). Único item de rede ainda em aberto: confirmar no PT se a **MCU-PT suporta o pacote `tcp`** (define se a Garagem-MCU fecha como nó).

## Estrutura

- `src/` — scripts Python dos SBCs (a criar; um arquivo por SBC/zona)
- `web/` — portais HTML do dashboard (a criar; V3 usava portal interno no PT + portal externo no Netlify via SBC proxy)
- `docs/` — levantamento técnico e documentação

## Restrições pedagógicas (IFMA)

Material com fim didático: comentários em **português**, priorizar legibilidade, toda lógica reutilizável em funções `def`. Evitar `class`/herança salvo se a arquitetura MQTT escolhida exigir explicitamente. Compatível com Python 3.1X (na prática, o subconjunto MicroPython do SBC-PT).
