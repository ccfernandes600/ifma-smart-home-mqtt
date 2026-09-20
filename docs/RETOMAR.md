# Retomar o V4 — revisão de 20/09/2026

Projeto parado desde 18/08 (33 dias). Esta revisão foi feita por leitura estática: nada aqui
roda fora do Packet Tracer. Serve para a bancada de amanhã render.

## Estado

- **12 scripts em `src/`**, 1.900 linhas: broker central, 6 zonas, o RFID Reader e 3 diagnósticos.
- **`verificacao/verificar.py` passa em tudo** (20/09, depois da higiene abaixo).
- **5 zonas validadas no simulador; 3 nunca rodaram**: `cozinha`, `quarto` e `jardim`.

## O que a revisão encontrou

### 1. Dois terços do tráfego existem para um dashboard que não existe

As zonas publicam **22 tópicos**. A Central consome **7** — os quatro de gás (garagem e cozinha),
o movimento da garagem, a campainha e o `rfid`. Os **15 restantes** (temperatura, umidade, luz,
vento, pressão, água, movimento das demais zonas) são armazenados e nunca entram em regra nenhuma.

Não é defeito: são a matéria-prima do painel. Mas muda a prioridade da decisão que está em
`ARQUITETURA.md` como "onde servir o dashboard". Ela deixou de ser item futuro e passou a ser
**o que dá sentido a dois terços das mensagens**. Enquanto não existir, 15 tópicos são tráfego sem
consumidor.

> O verificador imprime "6 lidos, 16 só para o dashboard" porque só enxerga os `estado.get()` de
> `avaliar_regras()`. O 7º é o `casa/perimetro/rfid`, tratado como evento em `ao_receber()`.

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

### 3. Modo viagem é parcial — 2 zonas de 6

`casa/todas/cmd/modo` é broadcast, mas só **Perímetro e Garagem** tratam.

- **Cozinha ignora de propósito** — risco de incêndio independe de haver gente em casa. Está
  comentado no topo de `zona_cozinha.py` e é decisão correta.
- **Sala, Quarto e Jardim ignoram por omissão.** Se a intenção é que o modo viagem mude o
  comportamento da casa inteira — apagar luzes, cortar climatização, reduzir irrigação —, faltam
  essas três. Registrado nas pendências de `ARQUITETURA.md`.

### 4. ✅ Higiene do repositório — RESOLVIDA em 20/09

- **O `.pkt` do V3 foi restaurado** (`git checkout`). A versão modificada em 01/09 está guardada em
  `../ifma-smart-home-packet-tracer/ifma-smart-home-v3_backup_2026-09-01.pkt.bak`, fora do git
  (casa com o `.gitignore`), caso a alteração faça falta.
- **`verificacao/`, `AGENTS.md` e `GEMINI.md` foram commitados.** O verificador é o contrato da
  força-tarefa: fora do git, não valia para os outros agentes.

## Ordem sugerida para a bancada

1. **`Environment.get("Smoke")` na cozinha.** É a única incógnita que pode forçar mudança de
   arquitetura, e o script da cozinha depende dela. Testar primeiro. Se der erro, tentar
   `"Smoke Detector"` ou similar.
2. **Rodar cozinha, quarto e jardim**, nessa ordem: a cozinha valida a leitura ambiental, o quarto
   repete o padrão da sala (já validado) e o jardim é o que tem mais sensores por controlador (7 de 10).
3. **Fechar o dashboard.** Com as três zonas rodando, os 22 tópicos existem de fato e o painel tem o
   que mostrar. É também o que dá remetente aos 19 comandos.
4. **Decidir o modo viagem na Sala, no Quarto e no Jardim** (item 3) — é escrita de código, não
   bancada, mas só faz sentido depois que as três zonas rodarem.

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
