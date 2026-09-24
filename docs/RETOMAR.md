# Retomar o V4 — revisão de 20/09/2026, atualizada em 23/09

## Bancada de 23/09 — Central e Perímetro aprovados

**Etapa 1 (Central sozinha): passou nos seis passos.** Broker, painel web, `/estado`, LCD e botão
de modo, tudo sem nenhuma zona no ar.

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

- A intrusão **não aciona o Home Speaker** da Central (só gás e campainha acionam). A sirene do
  perímetro soa localmente, mas a Central fica calada no evento mais grave. Decisão do professor.
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
- **a conexão fantasma**: se a Central responder ao heartbeat, a zona passa a saber que o broker
  morreu. Hoje ela não tem como descobrir, porque `connected()` mente — foi o que custou 40 min
  nesta bancada.

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
