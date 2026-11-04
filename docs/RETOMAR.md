# Retomar o V4

## Estado do projeto (04/11/2026)

**V4 finalizado, com a casa ao vivo no site.** Conferido ao reabrir o `.pkt` oficial: 8 scripts iguais ao `src/`, 7 nós conectados, nenhuma mensagem descartada e nenhum acesso à internet.

**Em aberto:** testar em outra máquina (aguarda o notebook), causa da queda de temperatura ao abrir o arquivo, causa do consumo de memória do PT, prova direta do Home Speaker e do umidificador.

**Repositório público desde 04/11/2026:** varredura de texto no histórico sem chave nem dados pessoais, além do e-mail de commit. Tudo que entra no `main` passa a ser visto por todos: a chave e a cópia ao vivo nunca entram.

## Casa ao vivo (04/11/2026)

O V4 está finalizado e testado, e o site público está em https://ifma-smart-home-mqtt.netlify.app.

**Como funciona:** com `NUVEM_CHAVE` preenchida, a Central envia por `RealHTTPClient` o estado, o LCD, o modo e as contagens à
função `/api/estado`, a cada 10 s quando algo muda, e a cada 60 s no mínimo. O site consulta a cada 10 s e mostra
`Simulador desligado` depois de 150 s sem dados.

**Dois arquivos, de propósito:**

- `src/IFMA-MQTT.pkt`: oficial, no git, sem chave. Não toca na internet nem abre aviso de rede. Conferido ao reabrir.
- `src/IFMA-MQTT_ao-vivo.pkt`: cópia pessoal, fora do git. A chave está nela, em `~/.cache/pt-operacao/chave_estado.txt` e
  em `ESTADO_CHAVE` no Netlify. Se ela vazar, troque a variável no Netlify e cole a Central de novo.

**Para demonstrar:** abra a cópia ao vivo e clique em **`Yes to All`** no aviso `External Network Access`. Ele volta a cada
abertura e, com `Yes` simples, a cada envio. Enquanto o aviso estiver aberto, nada é enviado.

**Corrigido nesta rodada:**

- Montar o resumo enquanto uma zona publicava deu `dict changed size during iteration`. Agora fica dentro do `try`, e a Central tenta no ciclo seguinte. Painel e `/estado` usam o mesmo dicionário: uma recarga pode falhar nesse instante, sem derrubar a Central.
- Com o clima de São Luís, o Old Car ligado estabiliza o CO perto de 0,008 %, abaixo do gatilho antigo de 0,01 %. O gatilho passou a 0,005 %. Medido: `ALERTA DE GAS` no site público, e `CASA OK` cerca de 20 s depois de desligar o carro.

**Medido:** Alt+clique no movimento da Sala, em modo viagem, chegou à API pública como `INTRUSAO NA SALA` em cerca de 6 s; o modo viagem
levou ~20 s, somando o intervalo de envio e o cache de 5 s. O teste de falha de rede só foi feito com dublê.

## Bancada de 03/11/2026 — Blocos 0 a 7 concluídos

Build 9.0.1.0858. **Próximo: Bloco 8 (fechamento).** O `.pkt` salvo já tem os 8 scripts novos e o clima de São Luís, ainda
sem commit (Bloco 8). Cada colagem foi conferida copiando o texto de volta do editor: igual ao `src/`.

- **Rede:** 7 nós conectados na Central, com os IPs certos (.21 a .26 e .33); nenhum `Mensagem descartada`
  nessa carga.
- **Etapa 1 do TESTE_ISOLADO:** os seis passos aprovados, sem zona no ar.
- **Cartão 1005:** `ACESSO OK` às 17:34:52 e porta fechada às 17:34:59, só com a Central e o Reader
  envolvidos. Falta conferir a porta e o LCD no Bloco 6.
- **Temperatura, medição parcial, não é conclusão:** a Sala subiu de 2 °C a 24 °C em 9,3 min, cerca de
  2,37 °C/min, perto da rampa de 2,5 °C/min da H1. Sensor e ambiente coerentes nas 3 primeiras leituras.

**Critério de V4 finalizado, aceito em 03/11/2026:** seis zonas aprovadas, Bloco 7 com
`conectados: 7 · publicando: 6`, causa da temperatura registrada, `.pkt` salvo e README final. Alarme por e-mail,
botões no painel e vitrine ficam para a V4.1.

**Bloco 3 fechado — a causa da temperatura:**

| Hipótese | Resultado | Medição |
|---|---|---|
| H1, rampa | **Confirmada** | Cerca de 2,4 °C/min até a curva às 19:00, e depois sobre ela: 24,7/24,7 e 27,9/27,9 °C (ambiente/curva) |
| H2, clima errado | **Confirmada como causa de hoje** | A reinstalação do PT desfez o `Default City.xml`; o `Corporate Office` estava de fábrica até a importação |
| H3, sensor × ambiente | **Descartada** | Coincidem dentro da resolução do `raw` (~0,8 °C) |
| H4, resíduo do AC | **Não se repetiu** | 8 ciclos entre 28,5 e 30,3 °C; sem AC voltou à curva: 30,71 contra 30,73 °C |

- O AC ligou às 19:08:42, no horário que a curva previa. Com a curva acima de 30 °C, ele cicla a cada ~37 s.
- **Ainda em aberto:** o −1 °C de 23/09 não se repetiu, e a causa daquele dia não está provada. Ao abrir o `.pkt`,
  o ambiente caiu de 17,7 a 12,9 °C (18:50 a 18:52:41), sem AC, antes de subir para a curva. Vale repetir uma vez.
- **Os dispositivos estão todos no `Corporate Office`:** é um só clima para a casa, e o AC de uma zona afeta as outras.
- **O `.pkt` guarda o clima importado:** conferido ao salvar e reabrir, na mesma máquina. Falta testar em outra.
- **O perfil zera os gases no `Intercity`** (O2 e CO2 em 0,00 %), diferente do clima de fábrica. Conferir na
  Garagem, no Bloco 5, a linha de base do CO2.

**O PT consome cada vez mais memória, sem depender do nosso código:**

| Situação | Crescimento |
|---|---|
| PT sem arquivo | estável em ~460 MB |
| Central + Sala | ~87 MB/min |
| Só Central | ~64 MB/min |
| Nenhum script | ~75 MB/min |
| Relógio do ambiente pausado | ~100 MB/min |
| Cópia sem o clima de São Luís | ~100 MB/min |

Reabrir o arquivo não devolve a memória: só fechar o PT. Causa não apurada; relógio, clima e scripts não a
explicam. **Regra de bancada:** sessões de até 45 min e fechar o PT entre elas. O travamento de 18:31 foi com
3,7 GB, então não há limite garantido.

**Bloco 4 fechado:**

1. **O TCP junta mensagens?** Não observado nesta carga: 71 mensagens em ~8 min, com 7 conexões, e nenhum
   `Mensagem descartada`. É pouco tráfego (~9/min), então olhar de novo no Bloco 7.
2. **A saída de um pino sobrevive ao Stop?** Sim: com a Cozinha parada, alarme, janela e sprinkler seguiram
   acionados. No Run, com a fumaça limpa, o `setup` desligou tudo: a correção de 03/11 funciona.
3. **A injeção de fumaça funciona?** Sim, com ressalvas medidas:
   - Ela **não acumula**: estabiliza em taxa × 30 (0,25 → 7,5 %; 1,0 → 30 %).
   - Ela **quase não sai sozinha**: 15 s depois do Stop, ainda 29,997 %. Uma contribuição negativa zera na hora.
   - O ID `Smoke` é válido, e **um ID inexistente devolve −1, sem exceção** (o diagnóstico antigo dava falso positivo).

Ao abrir o `.pkt`, o ambiente estava de novo em 12,9 °C: a queda inicial é reproduzível.

**Blocos 5, 6 e 7 — resultado:**

| Item | Medido em 03/11 |
|---|---|
| Conexão | Com a Central parada, os 7 nós rodando conectaram 6 s depois de ela subir; depois de reiniciar, em 3 s. Sem Stop → Run |
| Jardim | Corrigidos sensores e atuadores: dreno liga com 87 cm, sprinkler jorra, luminária acende à noite |
| Quarto | LED com `analogWrite` acende com movimento no escuro; janela abre e fecha |
| Cozinha | `PERIGO` e `normalizado` com fumaça e com CO; alarme, sprinkler e janela visíveis |
| Garagem | CO acima de 20 %: alarme, porta aberta e exaustor girando |
| Modo normal | Movimento em Sala e Quarto não alerta; portão, Garagem e campainha aparecem no LCD e voltam |
| Modo viagem | `INTRUSAO!` em Sala, Quarto e Garagem, no LCD e no painel; Sala, Quarto, Garagem e Perímetro recebem o modo, Cozinha e Jardim não |
| Cartão | Válido abre e fecha; inválido não prende; gás passa na frente do `ACESSO OK` |
| Porta sem Perímetro | `Comando nao entregue` a cada ~6 s; a porta fecha ao voltar |
| Painel | `conectados: 7 · publicando: 6`, seis tabelas, `/estado` com os valores das zonas |

**Conferência visual e lógica, mas sem prova direta:**

- **Home Speaker:** nada no log nem na planta mostra o som; só o código e o teste de lógica.
- **Umidificador:** a API está na doc do device, mas ele nunca ligou: o perfil não desce de 62 %, e a umidade não
  responde à contribuição. O corte em modo viagem só tem teste de lógica.

**Bloco 8 — fechamento (22:27):** reaberto do zero, os 8 scripts do `.pkt` estão iguais ao `src/`, e os 7 nós conectaram
sozinhos, 25 s depois de abrir, sem nenhuma mensagem descartada. **Critério de V4 finalizado: cumprido.**

**Versão Linux, em 04/11:** o PT 9.0.1 (AppImage, no WSL) abriu o mesmo `.pkt`: planta completa, `conectados: 7 ·
publicando: 6` e as seis tabelas, sem Stop → Run. O ambiente marcava 18 °C e 85 % ainda de madrugada, abaixo da curva,
o que é compatível com a queda ao abrir o arquivo, sem medição contínua. No WSL, foi preciso instalar `libopengl0` e
`libxcb-cursor0`. Valeu como segundo sistema, mas não como outra máquina: mesmo computador e mesmo usuário. Só o painel
foi conferido; os demais comportamentos não foram repetidos no Linux.

**Site público, em 04/11:** https://ifma-smart-home-mqtt.netlify.app, com fonte em `web/`. Mostra os logs da bancada como reprodução, sem dados ao vivo. Não oferece o `.pkt`: este repositório é privado, e isso ainda é decisão em aberto. Para publicar de novo: `npx netlify-cli@17 deploy --prod --dir web` (sem `web/desktop.ini`).

**O simulador fala com a internet (04/11):** de um script no SBC, `RealHTTPClient` buscou o site por HTTPS (`200`, com o HTML) e enviou um estado por POST à função `/api/estado` (`200 {"ok":true,"topicos":2}`, e a API pública devolveu os valores). O PT pede autorização por arquivo e por endereço, na janela `External Network Access`; respondi `Yes` só para os dois endereços do site. Os callbacks de `onDone` recebem `(status, corpo)`. O site ainda não mostra esses dados, e o `.pkt` validado não mudou.

**Central desligada (04/11):** Perímetro, Garagem e Quarto seguiram reagindo a movimento e campainha, com os avisos de falta de broker. Sala seguiu lendo a temperatura. Cozinha e Jardim não foram acionados nessa condição; o código deles não depende da Central.

**Medições novas:**

- O sprinkler soma +3 cm fixos (12 → 15 cm), sem acumular. No perfil seco, a irrigação fica ligada direto.
- O mostrador do Photo Sensor do Jardim exibe `FILE NOT FOUND`. É só a imagem; a leitura funciona.
- **Queda ao abrir o arquivo, reproduzida 3 vezes e sem causa:** o ambiente parte certo, 26 °C às 00h do simulador, e cai a
  ~2,5 °C/min até cerca de 12,9 °C, sem AC, antes de subir até a curva. Leva uns 12 min. O −1 °C de 23/09 pode ser
  da mesma família, mas não está provado.
- **Primeira leitura depois de abrir o arquivo:** os sensores analógicos dão 0 no primeiro ciclo (`Temp -100C`, `Umidificador: LIGOU`
  por 3 s). Não chega à Central, porque ainda não há conexão. Inofensivo, mas aparece no log.

**Observado e ainda sem correção:**

- As zonas publicam tudo duas vezes ao conectar, com 2 a 3 s de diferença. No 1º ciclo o `connected()` ainda é
  falso, e isso marca `_republicar`. Inofensivo.
- O cartão fica ao lado do Reader: todo Run do Reader abre a porta, porque a tag é lida ao conectar.
- O recarregamento de 5 s do painel reescreve o campo de URL do PC: é preciso digitar e dar Enter dentro desse
  intervalo. `/estado` é texto, não link.
- A janela da Cozinha se chama `SBC_Sala`, fácil de confundir com `SBC Sala`. O programa dentro dela é o certo.
- O PT reabre cada nó no estado em que estava ao salvar: com só a Central rodando, só ela voltou rodando.
- O `.pkt` caiu de 999.876 para cerca de 607.000 bytes ao regravar, sem perda: reaberto às 18:03, os 8 scripts
  continuam iguais ao `src/`.
- O `simulacao/README.md` diz que o `NOTES` aparece no modo View, mas o gerador grava `SHOW_NOTES=false`:
  a conferência de "dois segundos" não funciona. O campo só aparece em Edit → Advanced.

## Onde estamos — 03/11/2026

**Fase sem simulador: concluída.** A [revisão estática](REVISAO_ESTATICA_2026-11-03.md) achou os
defeitos, e as correções entraram com testes. **Nada disso rodou no Packet Tracer.**

**Próximo passo: a bancada, seguindo o [BANCADA.md](BANCADA.md).** A primeira tarefa de conteúdo é fechar
o diagnóstico da temperatura, agora com quatro hipóteses (Bloco 3).

**O que mudou no código, e por isso todo nó precisa ser recolado:**

- Movimento na Sala e no Quarto em modo viagem vira intrusão; intrusão aciona o Speaker (decisões de 03/11).
- Movimento perdido é reenviado em todas as zonas. A afirmação do trecho de 23/09, de que o Perímetro "era a
  única" zona sem esse cuidado, estava errada.
- Reconexão volta a publicar o estado. **Não cobre a conexão fantasma:** continua valendo a regra de Stop → Run.
- Quarto não religa o umidificador em viagem; Cozinha e Quarto nascem com os atuadores em estado conhecido.
- Aviso de cartão no LCD dura 5 s; o fechamento da porta é repetido se não for entregue; JSON inválido
  aparece no log.
- `diag_smoke.py` reescrito: a taxa é por segundo, renovada a cada ciclo. **Não testado.**

**Decidido não fazer agora:**

| Item | Por quê |
|---|---|
| Comando manual com prioridade sobre a automação | Só importa quando o painel ganhar botões; o padrão está em `ARQUITETURA.md` §4 |
| Estado que não expira quando a zona some (C4) | Depende do heartbeat, previsto para depois da validação |
| Histerese no gás (C12) | Só se a bancada mostrar o exaustor oscilando |
| Rever a chuva e a água dos perfis (S3, S4) | Chuva com dados do INMET; água com a calibração da bancada |
| Prazo local para a Porta do Perímetro | Só se a Central fora do ar for cenário de aula |

**O verificador foi medido:** com 34 defeitos plantados, pegava 13 de 33 e reprovava um uso correto. Agora pega
os 33, sem falso positivo. As regras foram escritas olhando esses defeitos, então não é medida de defeito novo.

---

> **Daqui para baixo é histórico.** Vale como registro do que cada bancada viu; contagens, status e
> pendências são da data de cada trecho. Se contradisser o que está acima ou o `BANCADA.md`, vale o de cima.

## Bancada de 23/09 — Central e Perímetro aprovados

**Etapa 1 (Central sozinha): passou nos seis passos.** Broker, painel web, `/estado`, LCD e botão
de modo, tudo sem nenhuma zona no ar.

**Sala (.22), camada B: passou em parte — a temperatura continua em aberto.**

Passou: conexão, publicação das quatro grandezas, conversão de temperatura calibrada (raw 650 →
27,08 °C pela fórmula contra 27,1 °C do termômetro do simulador, 0,02 de erro), climatização com
histerese **em malha fechada real** — o AC do PT esfria o ambiente de verdade, então ele ligou a
30 °C, puxou a temperatura para baixo e desligou a 28 —, movimento com hold, e modo viagem cortando
AC e Fan com o RGB indo para azul mesmo com a temperatura acima de 30. O corte com calor é o que
prova a precedência do modo sobre o termostato.

**NÃO passou, e é o ponto onde paramos:** depois disso, a temperatura lida divergiu do painel
`Environments` — a umidade batia, a temperatura não. Chegou a marcar **−1 °C** com a cidade em São
Luís, e antes disso passou minutos 12 graus abaixo. A sessão terminou sem fechar o diagnóstico.

> Uma versão anterior deste documento dizia que a Sala "passou por inteiro". **Estava errado** — a
> frase descrevia só a primeira metade da bancada, antes de o problema de temperatura aparecer.

**Três hipóteses, e o instrumento que separa as três.** `src/diag_temperatura.py` (criado em 25/09)
loga, lado a lado, o que o sensor GPIO lê, o que o `Environment` devolve e a **taxa em °C por hora
simulada**:

| | Hipótese | Assinatura no log |
|---|---|---|
| H1 | **Limite de taxa.** Só `Ambient Temperature` tem `MIN_RATE/MAX_RATE = ±0,00138889`/s no XML, o que dá **5 °C por hora simulada**; todas as outras grandezas saem com ±1000, instantâneo. Se o cômodo começou longe da curva, ele rampa — e todo valor no meio do caminho está em trânsito. | a coluna `C/h` **cola em +5,0 ou −5,0** |
| H2 | **Contêiner errado.** O cômodo roda o template genérico da Cisco, não o de São Luís (ver `simulacao/README.md`). | `C/h` perto de **0** e o valor parado num número que a curva de São Luís nunca produz |
| H3 | **Sensor contra ambiente.** A zona lê por `analogRead`; o painel mostra `Ambient Temperature`. | as colunas **SENSOR e AMBIENTE divergem** |

H1 e H2 podem ser verdadeiras ao mesmo tempo, e aí se somam: alvo errado *e* convergência lenta.
Rodar o diagnóstico uns três minutos, com o multiplicador de tempo ligado se quiser acelerar — a
taxa é calculada sobre o relógio simulado.

**Perímetro (.21), camada B: passou.** Movimento, campainha, broadcast de modo, Camera, Sirene em
modo viagem e a cadeia RFID inteira (Card → Reader → broker → whitelist → `cmd/porta` → Door abre
e fecha em 5 s).

**Seis correções de código saíram desta bancada:**

1. **Perímetro publicava sem `publicar_se_mudou`** — era a única das seis zonas assim. Publicação
   perdida ficava perdida para sempre, e a Central seguiria com campainha tocando e o Home Speaker
   ligado. Agora usa a função e reenvia o estado a cada ciclo (com guarda de conexão, senão o log
   vira enxurrada sem broker).
2. **RFID Reader marcava a tag como publicada antes de saber se o envio funcionou.** Sem broker, a
   leitura se perdia calada. Visto ao vivo: o primeiro `publicar()` falhou e o segundo funcionou.
3. **LCD da Central corta em 14 caracteres** — cinco das seis telas perdiam o fim. `INTRUSAO! /
   Movimento na garagem` virava `Movimento na g`, escondendo justamente onde olhar.
4. **LCD e painel discordavam:** o cálculo de gás estava escrito duas vezes e a faixa do painel não
   conhecia a intrusão. Unificados em `situacao_da_casa()`.
5. **Movimento no perímetro não acendia nada na Central** — só a garagem tinha tela. Agora as duas
   têm, com a linha 2 dizendo onde.
6. **Docstring do `manter_conexao()` da Sala afirmava o contrário do que a bancada mostra.**

**Pendências abertas nesta bancada:**

- ~~A intrusão não aciona o Home Speaker da Central.~~ Decidido e feito em 03/11: aciona.
- `cmd/sirene` e `cmd/camera` são sobrescritos pelo `atualizar_seguranca()` no evento seguinte.
  Só aparece quando o painel ganhar botões.
- **A Porta do perímetro não tem prazo local:** quem fecha é a Central, 5 s depois. Central fora do
  ar entre o abrir e o fechar deixa a porta aberta indefinidamente.

### Depois de tudo validado: monitoramento de saúde e alarme por e-mail

Ideia do professor em 23/09, adiada por decisão dele para o fim da validação. Ordem obrigatória —
a segunda parte não faz sentido sem a primeira:

**1. Heartbeat (`casa/<zona>/vivo` a cada ~10 s).** É pré-condição, não enfeite: como as zonas usam
`publicar_se_mudou()`, silêncio é o comportamento normal de zona saudável. Sem heartbeat, qualquer
verificação por tempo acusa zona viva como morta. Ele paga em três lugares:

- painel honesto (`atualizado há Xs`, zona esmaecida quando envelhece) — hoje uma zona parada há dez
  minutos é idêntica a uma publicando agora;
- checklist de saúde na Central, com critério em vez de chute;
- **zona muda:** a zona que parar de ouvir a Central passaria a perceber, o que hoje depende do `connected()`.

**2. Alarme por e-mail.** O pacote `email` existe no PT (§2.6 do levantamento): `EmailClient.setup()`,
`.send()` e `onSend(callback)`, que confirma se o envio saiu — alarme que falha calado é pior que
alarme nenhum. Exige um Server-PT com SMTP/POP3, domínio e contas; testar isolado, como o
`diag_smoke.py`.

**Regra de projeto para esse alarme: enviar por transição, não por estado.** Uma mensagem quando a
zona cai, uma quando volta, com carência de alguns minutos. Zona instável mandando um e-mail a cada
20 s faz o destinatário criar filtro — e aí o alarme morreu de vez.


## ONDE PARAMOS — bancada de 21/09/2026 (build 9.0.1.0858)

**Antes de tudo, na próxima sessão:** conferir se o `src/IFMA-MQTT.pkt` do git já tem a montagem
desta bancada. Se a data dele ainda for 04/07, a montagem de Cozinha, Quarto e Jardim ficou só no
Packet Tracer e precisa ser salva e commitada.

**O que foi provado no simulador:**

| Item | Resultado |
|---|---|
| `HTTPServer` no SBC | ✅ funciona — painel abriu no navegador do PC0 |
| Rota `/` e rota `/estado` | ✅ as duas responderam |
| `Environment.get("Smoke")` | ✅ existe e retorna sem erro |
| Caminho zona → Central → painel | ✅ inteiro, com Cozinha, Quarto e Sala |

**Estado das zonas quando paramos:** publicando **3** (Cozinha, Quarto, Sala) e conectados **5** —
a leitura provável é Perímetro e RFID Reader conectados e calados, que é o comportamento correto
deles. **Garagem e Jardim não haviam subido**; era o que íamos conferir no terminal de cada uma.
O alvo é conectados 7 e publicando 6 — o Perímetro passou a publicar o estado ao conectar (23/09).

**Dois defeitos achados e corrigidos hoje:**

1. A lista de clientes da Central só crescia — o painel contava conexões aceitas, não zonas vivas.
   Resolvido com `limpar_clientes()` a cada ciclo, e o painel passou a mostrar dois números.
2. Reiniciar a Central orfana as zonas em silêncio (ver §7.1 da ARQUITETURA). Regra: recolou a
   Central, reinicie as zonas.

**Leitura dos sensores:** umidade marca 79% e prova que a leitura funciona; temperatura e luz
marcam 0 porque é o ambiente padrão do contêiner. Consequência: **nenhum cenário dispara sozinho**
— AC a 30 °C, luminária no escuro e Cozinha a 20% de fumaça ficam todos parados.

**Próximo passo sugerido:** subir Garagem e Jardim, depois criar um `diag_ambiente.py` (arquivo
novo) que injete temperatura e luminosidade por `setContribution`, como o `diag_smoke.py` faz com
fumaça — é o que permite demonstrar climatização e luminária sem depender do relógio do simulador.

---


> **21/09:** o painel web foi implementado e o modo viagem foi fechado. O que resta do projeto
> **só acontece com o Packet Tracer aberto** — ver "Ordem sugerida para a bancada", no fim.

Projeto parado desde 18/08 (33 dias). Esta revisão foi feita por leitura estática: nada aqui
roda fora do Packet Tracer. Serve para a bancada de amanhã render.

## Estado

- **12 scripts em `src/`**, 1.900 linhas: broker central, 6 zonas, o RFID Reader e 3 diagnósticos.
- **`verificacao/verificar.py` passa em tudo** (20/09, depois da higiene abaixo).
- **5 zonas validadas no simulador; 3 nunca rodaram**: `cozinha`, `quarto` e `jardim`.

## O que a revisão encontrou

### 1. ✅ Dois terços do tráfego alimentavam um dashboard que não existia — RESOLVIDO em 21/09

O painel passou a ser servido pela **própria Central**, em `HTTPServer` na porta 80: rota `/` com a
tabela por zona e rota `/estado` com o JSON bruto. A Central era o único nó com o estado completo,
então servir dali dispensou replicar dado e dispensou implementar fan-out para um nó web.

Os 15 tópicos que não entravam em regra nenhuma agora têm destino. A distinção que fica: a Central
**decide** sobre 7 tópicos e **exibe** os 22.

Para ver o painel sem abrir o simulador: `python3 verificacao/previa_painel.py`, que dubla os
pacotes do PT, carrega o broker como módulo comum e grava o HTML com dados de exemplo (`--alerta`
mostra o cenário de vazamento de gás).

<details><summary>Diagnóstico original de 20/09</summary>

As zonas publicam **22 tópicos**. A Central consome **7** — os quatro de gás (garagem e cozinha),
o movimento da garagem, a campainha e o `rfid`. Os **15 restantes** (temperatura, umidade, luz,
vento, pressão, água, movimento das demais zonas) são armazenados e nunca entram em regra nenhuma.

Não é defeito: são a matéria-prima do painel. Mas muda a prioridade da decisão que está em
`ARQUITETURA.md` como "onde servir o dashboard". Ela deixou de ser item futuro e passou a ser
**o que dá sentido a dois terços das mensagens**. Enquanto não existir, 15 tópicos são tráfego sem
consumidor.

> O verificador imprime "6 lidos, 16 só para o dashboard" porque só enxerga os `estado.get()` de
> `avaliar_regras()`. O 7º é o `casa/perimetro/rfid`, tratado como evento em `ao_receber()`.

</details>

### 2. ✅ Fronteira entre regra local e regra central — DECIDIDA em 20/09

**A zona é autônoma; a Central só correlaciona o que atravessa zonas.** É o que o código já fazia;
agora está escrito em `docs/ARQUITETURA.md` §4 ("Decisão: quem decide o quê"), com o critério para
saber onde uma regra nova deve morar.

O que motivou fechar antes da bancada: as zonas tratam **20 comandos de atuador** e a Central envia
**um** (`casa/perimetro/cmd/porta`) mais o broadcast `casa/todas/cmd/modo`. Os **19 caminhos sem
remetente** não são código morto — são a interface do dashboard. Quem senta na bancada não deve
tentar exercitá-los pela Central: **não há quem os envie, e isso é proposital**.

O que decidiu a questão a favor da autonomia: zona sem broker continua automatizando (o `publicar()`
só loga o aviso e segue), e centralizar exigiria um mapa zona→IP que o broker não tem — o
`enviar_comando()` acha o destino por `remoteIP()` e só conhece o `PERIMETRO_IP`.

### 3. ✅ Modo viagem — FECHADO em 21/09: 4 zonas reagem, 2 ignoram por decisão

- **Sala:** corta climatização (AC + Fan) e pinta o RGB de azul.
- **Quarto:** corta AC e umidificador e suspende a luz de presença — movimento com a casa vazia é
  assunto de vigilância, não motivo para iluminar o cômodo.
- **Perímetro e Garagem:** já tratavam, no eixo de vigilância.
- **Cozinha ignora:** incêndio não depende de haver gente em casa.
- **Jardim ignora:** planta não viaja. A irrigação segue a umidade do solo e a luz acesa ajuda a
  simular presença.

O modo virou decisão por zona, com justificativa escrita em cada script — e não um interruptor
global que algumas zonas esqueceram de ler.

<details><summary>Diagnóstico original de 20/09</summary>

`casa/todas/cmd/modo` é broadcast, mas só **Perímetro e Garagem** tratam.

- **Cozinha ignora de propósito** — risco de incêndio independe de haver gente em casa. Está
  comentado no topo de `zona_cozinha.py` e é decisão correta.
- **Sala, Quarto e Jardim ignoram por omissão.** Se a intenção é que o modo viagem mude o
  comportamento da casa inteira — apagar luzes, cortar climatização, reduzir irrigação —, faltam
  essas três. Registrado nas pendências de `ARQUITETURA.md`.

</details>

### 4. ✅ Higiene do repositório — RESOLVIDA em 20/09

- **O `.pkt` do V3 foi restaurado** (`git checkout`). A versão modificada em 01/09 está guardada em
  `../ifma-smart-home-packet-tracer/ifma-smart-home-v3_backup_2026-09-01.pkt.bak`, fora do git
  (casa com o `.gitignore`), caso a alteração faça falta.
- **`verificacao/`, `AGENTS.md` e `GEMINI.md` foram commitados.** O verificador é o contrato da
  força-tarefa: fora do git, não valia para os outros agentes.

## Ordem sugerida para a bancada

Tudo que sobrou depende do simulador. O código está fechado.

> **O passo a passo detalhado, bloco a bloco e com checkpoints, está em
> [BANCADA.md](BANCADA.md)** — inclusive o alerta de que os scripts alterados em 21/09 precisam ser
> recolados dentro dos nós, porque o Packet Tracer guarda uma cópia.

1. **`Environment.get("Smoke")` na cozinha.** É a única incógnita que pode forçar mudança de
   arquitetura, e o script da cozinha depende dela. Testar primeiro. Se der erro, tentar
   `"Smoke Detector"` ou similar.
2. **Rodar cozinha, quarto e jardim**, nessa ordem: a cozinha valida a leitura ambiental, o quarto
   repete o padrão da sala (já validado) e o jardim é o que tem mais sensores por controlador (7 de 10).
3. **Abrir o painel no PC0** (`http://192.168.1.100`) com as seis zonas publicando e conferir se as
   tabelas batem com o que cada zona loga. É o teste que fecha o projeto: se o painel mostra as seis
   zonas, o caminho zona → Central → tela está inteiro.
4. **Exercitar o modo viagem pelo botão da Central** e conferir, no painel, a faixa azul e as quatro
   zonas que reagem. Cozinha e Jardim devem permanecer como estão — é o comportamento projetado.
5. **Montagem final da topologia e documentação de fechamento.**

## Rodar o verificador

```bash
python3 verificacao/verificar.py
```

Ele ganhou nesta revisão a regra **"broker e zonas falam os mesmos tópicos"**, que acusa tópico lido
sem publicador e comando enviado sem tratador — os dois erros que, no Packet Tracer, não dão
mensagem nenhuma: a mensagem só não chega.

**Buraco conhecido nessa regra:** ela só lê os `estado.get()` do broker. Um tópico consumido por
comparação direta dentro de `ao_receber()` — hoje só o `casa/perimetro/rfid` — passa despercebido.
Se alguém renomear o tópico do RFID Reader, o verificador continua passando e o fluxo de acesso
morre calado.
