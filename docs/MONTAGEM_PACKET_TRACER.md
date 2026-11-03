# Guia de Montagem no Cisco Packet Tracer

Passo a passo para montar a topologia do V4 e carregar os scripts. Referências completas de portas e IPs estão em [ARQUITETURA.md](ARQUITETURA.md).

> **Pré-requisito:** Packet Tracer 9.0.0+. **A bancada de 21/09/2026 rodou no build 9.0.1.0858** — é a versão em que valem as confirmações datadas desse dia. Todos os 7 nós ficam na mesma LAN `192.168.1.0/24` — o pub/sub é local, então **não precisa de roteador** para a automação funcionar (o roteador/NAT só entra depois, se você quiser o portal externo como no V3).

---

## Ordem de montagem recomendada

1. Rede base (switch + IPs)
2. Central (broker) — subir primeiro
3. Garagem (MCU) — `tcp` na MCU já confirmado (02/07/2026)
4. Sala (SBC) — valida o padrão de zona analógica
5. Demais zonas
6. Objetos ambientais e testes

---

## Passo 1 — Rede base

1. Arraste um **Switch 2950-24** para a área lógica (qualquer switch L2 de 24 portas serve; todos os nós ficam na mesma LAN, sem VLAN nem config extra).
2. Arraste um **PC** (será o PC0, `192.168.1.10`).
3. Conecte tudo ao switch com **cabo de cobre direto (Copper Straight-Through)** na porta **FastEthernet0** de cada dispositivo.
4. Configure **IP estático** em cada nó (aba `Config` → interface, ou `Desktop → IP Configuration` no PC):

| Nó | IP | Máscara | Gateway |
|---|---|---|---|
| PC0 | 192.168.1.10 | 255.255.255.0 | 192.168.1.1 |
| Central (broker) | 192.168.1.100 | 255.255.255.0 | 192.168.1.1 |
| Perímetro (MCU) | 192.168.1.21 | 255.255.255.0 | 192.168.1.1 |
| Sala (SBC) | 192.168.1.22 | 255.255.255.0 | 192.168.1.1 |
| Cozinha (SBC) | 192.168.1.23 | 255.255.255.0 | 192.168.1.1 |
| Quarto (SBC) | 192.168.1.24 | 255.255.255.0 | 192.168.1.1 |
| Jardim (SBC) | 192.168.1.25 | 255.255.255.0 | 192.168.1.1 |
| Garagem (MCU) | 192.168.1.26 | 255.255.255.0 | 192.168.1.1 |
| CO Detector (decorativo) | 192.168.1.31 | 255.255.255.0 | 192.168.1.1 |
| CO₂ Detector (decorativo) | 192.168.1.32 | 255.255.255.0 | 192.168.1.1 |
| RFID Reader (nó ativo) | 192.168.1.33 | 255.255.255.0 | 192.168.1.1 |

> Gateway pode ficar em branco enquanto não houver roteador — não afeta a comunicação dentro da LAN.

---

## Passo 2 — Adicionar cada controlador e seus dispositivos

Para **cada nó**:

1. Em `End Devices → Home` (ou `Components`), arraste um **SBC-PT** ou **MCU-PT** conforme a coluna Controlador.
2. Conecte-o ao switch (FastEthernet) e configure o IP (tabela acima).
3. Em `Components`, arraste os **sensores/atuadores** da zona.
4. Ligue cada dispositivo IoT a uma porta do controlador com o **IoT Custom Cable**, respeitando a porta `Dx` do mapa abaixo.
5. Abra o controlador → aba **Programming** → crie um projeto Python vazio → cole o script correspondente de `src/` → **Run**.

> **Regra da MCU:** use apenas **D0–D5** (as analógicas A0–A3 têm o bug do V3). Na MCU as D0–D5 fazem digital/analog/custom normalmente.

### Mapa de portas (resumo)

**Central — SBC (.100)**
`D0` Push Button (modo) · `D1` LCD mestre · `D2` Home Speaker

**Perímetro — MCU (.21)**
`D0` Motion · `D1` Push Button (campainha) · `D2` Door · `D3` Siren · `D4` Camera · (D5 livre)

> ✅ **RFID Reader entra como nó de rede independente, NÃO por cabo IoT.** Ele não tem API GPIO (a doc do device diz `Direct/Local/Remote Control: N/A`), mas tem um **script Python próprio editável** com `tcp`/`json` — então ele mesmo publica `casa/perimetro/rfid` direto no broker. Montagem:
>
> 1. Arraste o **RFID Reader** e clique nele → aba **Advanced** → **I/O Config**.
> 2. ⚠️ **Ele vem de fábrica com 0 slots**: mude **Digital Slots de 0 → 1** (Analog Slots pode ficar 0). Confira também o **Network Adapter** (`PT-IOT-NM-1CFE` para cabo; ou o adaptador WiFi).
> 3. Conecte ao switch e configure o IP `192.168.1.33` (tabela do Passo 1).
> 4. Aba **Programming** → substitua o script padrão pelo `src/thing_rfid_reader.py` → **Run**.
> 5. Arraste um **RFID Card**, clique nele → **Advanced** → defina o ID no script JavaScript dele (`var CARD_ID = 1005;`).
> 6. Aproxime o Card do Reader (a detecção é por proximidade física) → o Reader publica a tag no broker.
>
> A Porta do Perímetro continua sendo acionada por comando (`cmd/porta`) — agora a Central pode abri-la ao receber um cartão válido.

**Sala — SBC (.22)**
`D0` Temperature · `D1` Humidity · `D2` Photo · `D3` Motion · `D4` AC · `D5` Fan · `D6/D7/D8` LED R/G/B

**Cozinha — SBC (.23)**
`D0` Temperature · `D1` Humidity · `D2` Fire Sprinkler · `D3` Window · `D4` Fan · `D5` Alarm · (D6–D9 livres)

> ⚠️ **Não ligue Smoke/CO Detector por cabo IoT** — mesma família de Smart Thing do CO da Garagem (sem `Direct/Local Control`). O `zona_cozinha.py` lê fumaça e CO pelo pacote `environment`, sem porta física. Se quiser os detectores visíveis na topologia, conecte-os via rede como decorativos (padrão dos da Garagem). **Cenário de teste:** um **Old Car** no mesmo contêiner físico da Cozinha serve como fonte — a doc dele lista fumaça (3%/h) além de CO/CO₂ (e é possível turbinar a taxa editando o script embutido dele, como fizemos no Heating Element).

**Quarto — SBC (.24)**
`D0` Temperature · `D1` Humidity · `D2` Photo · `D3` Motion · `D4` AC · `D5` Humidifier · `D6` Smart LED · `D7` Window

**Jardim — SBC (.25)**
`D0` Water Level · `D1` Wind · `D2` ATM Pressure · `D3` Photo · `D4` Lawn Sprinkler · `D5` Drain · `D6` Light

**Garagem — MCU (.26)**
`D0` Motion · `D1` Garage Door · `D2` Fan · `D3` Alarm · (D4/D5 livres)

> ⚠️ **Não ligue CO/CO₂ Detector por cabo IoT.** Esses sensores são *Smart Things* no PT — a doc do próprio dispositivo diz `Direct/Local/Remote Control: N/A` — não respondem a `digitalRead`/`analogRead`. O script lê o gás pelo pacote `environment` (concentração ambiente simulada), sem usar porta física nem depender desses devices.
>
> **Decisão do projeto:** manter CO Detector (`192.168.1.31`) e CO₂ Detector (`192.168.1.32`) na topologia por completude visual — conecte-os via WiFi ou cabo Ethernet ao switch, com IP estático. Eles ficam **decorativos**: sem Registration Server configurado, não reportam a lugar nenhum e não influenciam a automação (que já funciona via `environment`). Colocar o **Old Car** na mesma sala/contêiner da Garagem no *Physical Workspace* é o que importa de fato.

---

## Passo 3 — Ordem de execução dos scripts

1. **Central primeiro** (`broker_central.py`) — o broker precisa estar ouvindo antes das zonas conectarem.
2. **Garagem** (`zona_garagem.py`) — `tcp` na MCU já **confirmado** ✅ (testado 02/07/2026, Central logou "Zona conectada").
3. **Sala** e demais zonas.

> Scripts de diagnóstico temporários em `src/` (`diag_garagem.py`, `diag_environment.py`, `diag_time_multiplier.py`) — usados para depurar o comportamento dos sensores no simulador. Podem ser removidos quando o projeto estiver estável.

---

## Passo 4 — Objetos ambientais e testes

- **Garagem:** adicione um **Old Car** perto do sensor de CO/CO₂ (os detectores são decorativos e não influenciam nada). Com ele ligado, a leitura via environment passa de 20% → Fan + Porta + Alarme, e a Central anuncia no Speaker/LCD.
- **Sala/Quarto:** use um **item de aquecimento/resfriamento** ou ajuste manual do sensor para variar Temperatura e ver o AC/Fan/LED reagirem.
- **Perímetro:** acione o **Push Button** (campainha) e veja a Central tocar o Home Speaker.
- Acompanhe os `print()` no terminal de cada nó (aba Programming) e o **modo Simulação** para ver os pacotes na rede.

---

## Passo 5 — Abrir o painel web

O painel é servido pela própria Central, sem nó extra.

1. Com a Central rodando, abra o **PC0** → aba *Desktop* → **Web Browser**.
2. Vá para `http://192.168.1.100` (porta 80, o padrão do navegador do PT).
3. A página mostra a faixa de situação (CASA OK, VISITANTE NA PORTA, MODO VIAGEM, MOVIMENTO, INTRUSAO ou ALERTA DE GAS),
   o modo atual, quantas zonas estão conectadas e uma tabela por zona com o último valor de
   cada grandeza. Ela se recarrega sozinha a cada 5 segundos.
4. Para conferir valor por valor sem depender do layout, use `http://192.168.1.100/estado`,
   que devolve o estado em JSON.

**Se a página não abrir:** confirme que a Central está com o script rodando (o terminal dela
registra "Painel web em http://192.168.1.100:80" no arranque) e que o PC0 tem gateway e máscara
corretos — o navegador do PT não avisa a diferença entre "sem rota" e "servidor fora do ar".

> Para ver o painel fora do simulador, antes de montar a bancada:
> `python3 verificacao/previa_painel.py` gera `verificacao/previa_painel.html` com dados de
> exemplo. Use `--alerta` para ver a faixa vermelha do cenário de gás.

## Passo 6 (opcional/futuro)

- **Vitrine MQTT real:** adicione um **IoT Server**, habilite o serviço **MQTT Broker** (aba Services) e mostre pacotes MQTT reais no modo Simulação.
- **Fundo isométrico:** carregue `assets/planta_casa_zonas.png` como imagem de fundo (Physical Workspace) para posicionar cada nó no cômodo real.
- **Portal externo:** roteador + NAT + Netlify, como no V3.
