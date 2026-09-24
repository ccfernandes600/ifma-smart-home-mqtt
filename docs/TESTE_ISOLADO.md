# Protocolo de teste isolado — um subsistema por vez

Ordem de validação com **tudo desligado menos o alvo**. Serve para localizar defeito sem
ambiguidade: se algo falha com um nó só rodando, a causa está naquele nó.

Regra que vale o protocolo inteiro: **uma variável por vez**. Zona que não está sendo testada fica
com o script parado (Programming → Stop), não só quieta.

---

## Por que cada zona é testada duas vezes

A arquitetura afirma que **a zona é autônoma** — ela automatiza mesmo sem broker, e a Central só
correlaciona o que atravessa zonas. Testar a zona junto com a Central não prova isso: se tudo
funciona, não dá para saber se a decisão foi local ou central.

Por isso cada zona passa por duas camadas:

| Camada | Central | O que prova |
|---|---|---|
| **A — autonomia** | **desligada** | sensor lido, regra local aplicada, atuador acionado, e o aviso de "sem conexao" sem travar o laço |
| **B — integração** | ligada | conecta, publica, aparece no painel e obedece ao broadcast de modo |

Se a camada A falhar, o problema é da zona. Se A passa e B falha, o problema é de rede, de tópico
ou da Central — e isso já é meio caminho do diagnóstico.

---

## Etapa 1 — Central sozinha

Nenhuma zona rodando.

| Passo | O que fazer | O que deve acontecer |
|---|---|---|
| 1.1 | Run no `broker_central.py` | terminal imprime `Broker ouvindo na porta 1883` e `Painel web em http://192.168.1.100:80` |
| 1.2 | LCD mestre | mostra `CASA OK / Modo normal` |
| 1.3 | Abrir `http://192.168.1.100` no PC0 | faixa verde, `conectados: 0 · publicando: 0`, texto "Nenhuma publicacao recebida ainda" |
| 1.4 | Abrir `/estado` | responde `{}` |
| 1.5 | Apertar o Push Button (D0) | log `Modo viagem = True`, LCD vai para `MODO VIAGEM`, painel fica azul |
| 1.6 | Apertar de novo | volta para `CASA OK` |

**Aprovado se:** os seis passos ocorrem sem nenhuma zona no ar. Isso isola servidor, LCD, botão e
painel do resto do sistema.

---

## Etapa 2 — Cada zona sozinha, camada A (Central desligada)

Pare a Central antes de começar. Rode **uma zona por vez**.

### 2.1 Sala — 192.168.1.22
- Esperado no arranque: `Sala conectando ao broker...` seguido de `AVISO: sem conexao` a cada ciclo.
  **O aviso é o resultado correto aqui** — prova que a zona segue funcionando sem broker.
- Aquecer o Temperature acima de **30 °C** → AC (D4) liga, Fan (D5) liga, RGB fica laranja, log
  `Climatizacao: LIGOU`.
- Esfriar abaixo de **28 °C** → desliga e o RGB volta ao verde. A folga de 2 °C é a histerese: se
  ligar e desligar no mesmo grau, ela não está funcionando.
- Acionar o Motion (D3) → log `Movimento detectado`, e o encerramento depois do hold.

### 2.2 Quarto — 192.168.1.24
- Temperatura acima de 30 °C → AC liga; abaixo de 28 °C → desliga.
- Umidade abaixo de **40%** → umidificador liga; só desliga ao voltar a **50%**.
- Motion **com o Photo escuro** (abaixo de 200 raw) → Smart LED acende; com luz alta, não acende.
  Esse par é o teste da regra composta: movimento sozinho não pode acender.

### 2.3 Cozinha — 192.168.1.23
- Sem fonte de fumaça, tudo desligado e log limpo.
- Injetar fumaça com o `diag_smoke.py` num SBC avulso no mesmo contêiner → ao cruzar **20%**,
  os quatro atuadores disparam **juntos**: sprinkler, janela, fan e alarme, com log `PERIGO`.
- Ao normalizar, os quatro voltam juntos.

### 2.4 Jardim — 192.168.1.25
- Nível de água abaixo de **150** → irrigação liga. Acima de **300** → desliga.
- Acima de **800** → dreno liga. Abaixo de **650** → desliga.
- Photo abaixo de **200** → luminária acende; acima de **300** → apaga.
- Detalhe do simulador que vale observar: o próprio Lawn Sprinkler eleva o nível de água do
  ambiente, então a malha fecha sozinha — irrigar faz o nível subir de verdade.

### 2.5 Garagem — 192.168.1.26 (MCU)
- **Primeiro olhe o arranque:** se houver erro de import, o problema é o pacote `environment` na
  MCU, e não a lógica. Anote a mensagem exata.
- Old Car ligado por perto → CO/CO₂ passam de **20%** → Fan, porta e alarme.
- Motion → log com hold; sem modo viagem, movimento sozinho não é intrusão.

### 2.6 Perímetro — 192.168.1.21 (MCU)
- Push Button da campainha → log de campainha, com hold.
- Motion → log de movimento.
- Porta e sirene **não devem reagir sozinhas**: elas só obedecem a comando da Central. Nesta camada,
  ficar paradas é o resultado certo.

### 2.7 RFID Reader — 192.168.1.33
- Aproximar o Card → o script do Reader publica a tag. Sem Central no ar, ele apenas registra a
  tentativa. Confirma que o Reader lê o cartão, que é o que esta camada precisa provar.

---

## Etapa 3 — Cada zona com a Central, camada B

Suba a Central e **uma** zona por vez.

Para cada zona, três confirmações:

1. **Central registra** `Zona conectada: 192.168.1.xx`.
2. **Painel mostra a zona** em `/estado` e na tabela, com valores que batem com o log da zona.
3. **Broadcast de modo chega:** aperte o botão da Central e veja o log da zona.
   - Sala, Quarto, Garagem e Perímetro registram `Modo viagem = True`.
   - **Cozinha e Jardim não reagem — e isso é o projetado**, não falha.

Casos específicos, quando chegar a vez:

- **Perímetro + Central:** cartão válido (ID 1005) no Reader → Central manda `cmd/porta`, a porta
  abre, e fecha sozinha depois de 5 s. Cartão diferente → LCD mostra `CARTAO INVALIDO` e a porta
  não abre.
- **Garagem + Central:** gás acima do limiar → além dos atuadores locais, a Central mostra
  `ALERTA DE GAS` no LCD, liga o Speaker e o painel fica vermelho.
- **Perímetro + Central, modo viagem:** movimento na Garagem com modo viagem ligado → `INTRUSAO!`.

---

## Etapa 4 — Todas juntas

Só depois que as seis passaram em A e B.

| Verificação | Esperado |
|---|---|
| Painel | `conectados: 7` (6 zonas + Reader) · `publicando: 6` |
| Perímetro | publica `movimento: nao` e `campainha: nao` assim que conecta (mudou em 23/09) |
| Modo viagem | quatro zonas reagem, Cozinha e Jardim seguem iguais |
| Gás na Cozinha e na Garagem | os dois levam o painel a vermelho |
| Carga | os logs continuam fluindo sem engasgo perceptível |

---

## Ficha de falha

Quando algo não passar, registre assim — é o que permite consertar sem repetir a bancada:

```
Nó:            Cozinha (192.168.1.23)
Etapa:         2.3, injeção de fumaça
Esperado:      quatro atuadores ligam ao cruzar 20%
Observado:     sprinkler e alarme ligam; janela e fan não
Mensagem:      (colar a linha exata do terminal)
Já tentado:    reiniciei o script; conferi que a janela está em D3
```

## Quatro regras operacionais que já custaram tempo

1. **Zona que rodou com a Central fora do ar precisa de Stop → Run depois que a Central subir.**
   Não importa quem caiu primeiro. Enquanto a Central está parada, as tentativas de `connect()`
   deixam o objeto cliente reportando conexão; quando a Central sobe de verdade, o
   `manter_conexao()` não tenta de novo porque acha que já está dentro.
   **Sintoma que engana:** a zona funciona — sensores, atuadores, log — e não emite nenhum
   `AVISO: sem conexao`, porque `connected()` mente. O que morre é só a rede, nos dois sentidos:
   nada chega na Central e nenhum broadcast de modo chega na zona.
   **Como confirmar em 5 segundos:** aperte o botão de modo da Central. Se a zona não logar
   `Modo viagem = ...`, é conexão fantasma. (Medido na bancada de 23/09, no Perímetro.)
2. **Editar o arquivo no repositório não muda o simulador.** O script roda a partir da cópia
   colada dentro do nó.
3. **Reinicie o Packet Tracer de tempos em tempos numa bancada longa.** Ele degrada com o
   acúmulo de janelas abertas e fechadas — cada aba Programming carrega um interpretador, e depois
   de algumas horas com muitos nós o programa trava. Travou em 23/09, depois de uma sessão de
   ~2 h com as janelas de seis nós. **Salve o `.pkt` antes de qualquer operação pesada**
   (importar ambiente, montar zona nova): é a diferença entre perder cinco minutos e perder a
   sessão. Lembrando que o ambiente mora dentro do `.pkt` — salvar antes de importar significa
   reimportar depois.
4. **A aba aberta do editor não recarrega sozinha.** Se o arquivo mudou no disco enquanto a aba
   estava aberta, copiar dali cola a versão velha — e o sintoma é a correção "não ter funcionado".
   Feche e reabra a aba antes de copiar. (Custou uma rodada inteira em 23/09.)
