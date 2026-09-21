# Retomar o V4 — revisão de 20/09/2026, atualizada em 21/09

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
