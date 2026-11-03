# Revisão estática — 03/11/2026

Tudo o que dá para conferir **sem abrir o Packet Tracer**. Registro do que foi achado em 03/11. As
correções entraram no mesmo dia, e o `RETOMAR.md` diz o que foi feito e o que ficou de fora.

**Como foi feita:** Claude Code coordenou e julgou; Gemini 4 Argon revisou o código sem ver os achados
do coordenador; Copilot CLI auditou documentação × código sem poder gravar; Gemini 3.8 Flash revisou a
simulação; um subagente Sonnet plantou 34 defeitos numa cópia para testar o verificador. As citações
foram conferidas por script contra os arquivos, e os defeitos marcados como *reproduzido* rodaram com
dublês dos pacotes do PT. **Dublê prova a lógica do script, não o comportamento do simulador.**

## 1. Defeitos de lógica

| Id | Sev. | Onde | Defeito | Evidência |
|---|---|---|---|---|
| C1 | alta | `zona_quarto.py` | Em modo viagem, o umidificador é desligado ao receber o comando e **religa em até 2 s**: `atualizar_umidificador()` não olha o modo. Contradiz o que `ARQUITETURA.md` declara fechado. Adormecido no clima de São Luís, cuja umidade não desce de 62 %. | reproduzido; achado por dois revisores |
| C2 | alta | `zona_garagem.py`, `zona_sala.py`, `zona_quarto.py` | Movimento usa `publicar()` direto. Se o `movimento=0` falha, nunca é reenviado e a Central fica presa em MOVIMENTO ou INTRUSAO. O `RETOMAR.md` diz que o Perímetro "era a única" zona assim; não era. | reproduzido; dois revisores |
| C3 | alta | `broker_central.py`, `zona_quarto.py` | Movimento na Sala ou no Quarto em modo viagem não vira INTRUSAO, embora a docstring do Quarto diga que é "tratado pela Central". **Decisão D1.** | leitura |
| C4 | média | `broker_central.py` | `estado` não expira: zona que sai com gás a 25 % deixa ALERTA DE GAS e Speaker ligados até reiniciar a Central. O heartbeat planejado é a base da correção. | reproduzido |
| C5 | média | `broker_central.py` | Tela RFID sem prazo: ACESSO OK some na próxima publicação de qualquer zona, com a porta ainda aberta; CARTAO NEGADO fica até alguém publicar. | reproduzido; dois revisores |
| C6 | média | `broker_central.py` | `verificar_porta_rfid()` zera o prazo e loga "fechada" mesmo se o comando não foi entregue. Agrava a pendência da porta sem prazo local. | leitura |
| C7 | média | todas as zonas | `manter_conexao()` reconecta sem limpar `anterior`: uma Central recém-reiniciada fica sem os valores até eles mudarem. | reproduzido |
| C8 | média | seis zonas × Central | `ao_receber()` engole JSON inválido em silêncio. Se o TCP juntar duas mensagens numa leitura, as duas se perdem, e a zona já as marcou como enviadas. As zonas enviam 3–4 mensagens em sequência. **Testar no PT; no mínimo, logar.** | reproduzido com dublê; falta o PT |
| C9 | média | Sala, Quarto, Garagem, Jardim | Comando manual é sobrescrito no ciclo seguinte; na Cozinha, persiste. O `RETOMAR.md` só cita sirene e câmera. Bloqueia os botões futuros do painel. **Decisão D3.** | reproduzido |
| C10 | média | `zona_cozinha.py`, luz do Quarto | Atuadores só são escritos na transição: Stop com alarme ligado e Run sem perigo não os repõem. **Só vale se o PT preservar a saída entre execuções: testar.** | reproduzido com dublê; falta o PT |
| C11 | média | `diag_smoke.py`, `BANCADA.md` | `TAXA` diz "por hora", mas a API é **por segundo** (§2.9 do levantamento); e `setContribution` é chamado uma vez, enquanto os dispositivos da Cisco chamam a cada segundo. A promessa "sobe a 30/h" está sem base. | leitura; falta o PT |
| C12 | baixa | Cozinha, Garagem | Limiar de gás sem histerese; o exaustor pode oscilar perto de 20 %, ao contrário das outras automações. | leitura |
| C13 | baixa | `zona_jardim.py` | Loga "Irrigacao: desligou" e "Dreno: desligou" na partida. | leitura |
| C14 | baixa | `zona_garagem.py` | Comentário `FAN ... (digitalWrite)` contradiz o `customWrite` do código; cabeçalho diz "API de escrita ainda não confirmada", já confirmada. | três revisores |

## 2. A temperatura: o diagnóstico está mais aberto do que os documentos dizem

- **T1 — `simulacao/README.md` afirma como fato o que o `RETOMAR.md` trata como aberto, e se contradiz.**
  Uma seção atribui o −1 °C ao contêiner aninhado (H2). Outra manda, com o mesmo sintoma: "não procure
  contêiner errado [...] É o `MAX_RATE`" (H1). O README é para publicação: precisa dizer o que foi
  medido e o que é hipótese.
- **T2 — Hipótese nova, H4: efeito residual dos atuadores. Não provada.** O `RETOMAR.md` registra que a
  divergência apareceu **depois** de o AC funcionar em malha fechada. Os dispositivos chamam
  `setContribution(..., True)` (visto no script do Heating Element; falta ver o do AC), e H1 sozinha não explica −1 °C, pois a rampa só sobe rumo a
  uma curva que não desce de 24,5 °C. A assinatura pode **se confundir com H1**: `C/h` em +5 seria também
  a recuperação depois do AC. O `diag_temperatura.py` não separa as duas.
- **T3 — "~1,5 °C por minuto real" × "2,5 °C/min" no mesmo README.** A conta dá 2,5. A medição citada
  (2,8 → 27,1 °C em 14 min) não decide, porque a rampa pode ter terminado antes do fim do intervalo.

A favor de H4, medido em 23/09 e citado no próprio README: o AC derrubou o ambiente a 3,31 °C/min real,
acima do limite de 2,5 da curva.

**Protocolo proposto para a bancada:** rodar `diag_temperatura.py` num contêiner **sem atuadores** e
repetir no da Sala com AC e Fan. Só a segunda discrepando aponta para H4.

## 3. Simulação

| Id | Sev. | Defeito |
|---|---|---|
| S1 | média | **Sobrescreve o arquivo errado:** o comando do README `--perfil sao-luis-seco --tolerancia 5`, sem `--saida`, grava por cima do XML completo, enquanto o versionado se chama `_enxuto`. |
| S2 | média | **Tutorial quebra:** "Mexa só em `PERFIS`" e o exemplo com só `minha-cidade` fazem `python3 gerar_ambiente.py` falhar (`Perfil 'sao-luis-seco' nao existe`). Testado. Falta dizer `--perfil minha-cidade` e manter os perfis existentes. |
| S3 | média | **Chuva fora do "dia típico":** o perfil chuvoso soma 15,5 cm no dia (pico de 6 cm/h). O documento promete "números, não valores inventados". Rever com dados do INMET. |
| S4 | média | **Água ajustada ao limiar:** 12 cm ("solo seco") e 88 cm vêm em centímetros de lâmina d'água, mas parecem escolhidos para cruzar os limiares raw do Jardim, sem unidade definida. Contradiz o espírito de "não ajuste para a demo". Calibrar na bancada. |
| S5 | baixa | `AMBIENTE_SIMULADO.md` diverge do gerador: umidade às 17 h e 20 h (70/80 × 68/78), luz às 06:15 e 17:45, tabelas sem hora 24. Melhor apontar para o gerador como fonte única. |
| S6 | baixa | README: "AC + ventilador da Sala e do Quarto"; o Quarto não tem ventilador. Limiares `<150`/`>800` × `<=`/`>=` no código. |

**Rejeitado:** "fórmulas de Heat invertidas". O catálogo vem do XML exportado pelo próprio PT, a grandeza
é inativa e a citação do revisor não era literal.

**Conferido e correto:** os dois XMLs completos e os dois enxutos (`--tolerancia 5`) são regenerados
**idênticos ao byte**. `"Smoke"`, `"CO"`, `"CO2"` e `"Ambient Temperature"` constam do catálogo exportado pelo
PT, o que reforça a confirmação do ID de fumaça.

## 4. Verificador: pega 13 de 33

Defeitos plantados em cópia, mais um uso correto:

| Resultado | Casos |
|---|---|
| **Pegou (13)** | `class`; import inexistente (2); `customRead` sem strip; A0 em MCU; estouro de portas (2); porta repetida; comentário divergente; tópico do broker lido sem publicador (2); comando direto sem tratador; `BROKER_PORT` divergente |
| **Falso positivo (1)** | `x = customRead(p)` com `x.strip()` na linha seguinte |
| **Deixou passar (20)** | **MCU em D7**; porta sem comentário; pino literal; **tópico RFID renomeado de um lado só (2 casos)**; comando por variável; **`BROKER_IP` errado**; **`PORTA_BROKER` diferente**; `ZONA` com maiúscula; `/cmd/` sem remetente; **Fan com `digitalWrite`**; **LCD acima de 14 caracteres (2)**; **sem `onReceive`**; sem `add_event_detect`; **`ao_receber(client, data)`**; **import ausente (2)**; `main()` vazio; sem bloco `__main__` |

Em negrito, os testes que proponho acrescentar: são baratos e cobrem gotchas que o projeto já pagou para
aprender. A `FORCA-TAREFA.md` diz 12 verificações; são 13. O "1.900 linhas" do cabeçalho também envelheceu.

## 5. Repositório e operação

- **R1 — `main` está 19 commits atrás** (`origin/main` parou em 18/08); todo o trabalho desde então está em
  `higiene-e-fronteira`, e o GitHub mostra o estado antigo. **Decisão D4.**
- **R2 — `BANCADA.md` aponta para a distro antiga** (`\\wsl.localhost\Ubuntu-26.04\...`); a atual é `Dell`.
  O roteiro também está parado em 21/09: `.pkt` "de 04/07" (é de 23/09), "montar as três zonas" (já
  montadas), lista de recolagem antiga.
- **R3 — `CLAUDE.md` envelhecido:** `src/` e `web/` "a criar" (`web/` só tem um `desktop.ini`), PT 9.0.0, `tcp`
  na MCU "em aberto", campo `ts`.
- **R4 — `LEVANTAMENTO_DISPOSITIVOS_PT9.md`** ainda dá `Smoke` como "inferido, não testado" (tabela 1.1,
  gotcha e §4).
- **R5 — `RETOMAR.md` em ordem invertida:** 23/09 antes de 21/09, com o trecho antigo contradizendo o novo.

## 6. Decisões do professor

- **D1:** movimento na Sala e no Quarto em modo viagem vira INTRUSAO? *Recomendo sim:* é quem está dentro
  de casa, e a docstring já promete.
- **D2:** intrusão aciona o Home Speaker? *Recomendo sim:* a Central calada no evento mais grave contradiz o
  papel dela.
- **D3:** comando manual ganha prioridade sobre a automação? *Recomendo adiar* até os botões do painel e
  registrar agora o padrão (comando vale até a próxima mudança de estado do sensor).
- **D4:** quando levar `higiene-e-fronteira` para `main`? *Recomendo depois da fase de correções, antes da
  bancada*, para o `.pkt` novo já nascer no ramo principal.

## 7. Documentação × código

Auditoria do Copilot CLI: 33 contradições, com as duas citações literais conferidas por script. **32 aceitas.**
Rejeitada a de "50+ portas" no README: é capacidade, não portas em uso.

| # | Sev. | Documento | Problema | Correção |
|---|---|---|---|---|
| 1 | alta | `docs/ARQUITETURA.md` | A tabela de portas da Sala diz que o Fan usa digitalWrite, mas o código e a regra confirmada no PT usam customWrite com "0"/"1"/"2". | Trocar a diretiva do Fan da Sala (D5) para `customWrite` na tabela. |
| 2 | alta | `docs/ARQUITETURA.md` | A tabela da Garagem diz que o Fan usa digitalWrite, mas o código aciona o Fan com customWrite; o comentário da constante FAN em zona_garagem.py também diz digitalWrite e contradiz o corpo do código. | Corrigir a tabela da Garagem (e o comentário da constante FAN) para `customWrite`. |
| 3 | media | `docs/ARQUITETURA.md` | O Perímetro usa 5 portas (D0 a D4) com só D5 livre, mas o título da seção diz 4/6 com 2 livres, e a própria tabela abaixo lista 5 dispositivos. | Corrigir o título para 5/6 (1 porta livre) e ajustar os totais que repetem 4/6. |
| 4 | media | `docs/ARQUITETURA.md` | A Cozinha usa 6 portas (D0 a D5) e tem 4 livres (D6–D9), mas o título diz 4/10 com 6 livres, contradizendo a própria tabela de 6 linhas. | Corrigir para 6/10 (4 portas livres) e ajustar a frase de totais sobre a Cozinha. |
| 5 | baixa | `docs/ARQUITETURA.md` | O total declarado (41) não bate com o código: Central 3 + Perímetro 5 + Sala 9 + Cozinha 6 + Quarto 8 + Jardim 7 + Garagem 4 = 42, e pelos títulos da própria ARQUITETURA a soma seria 39. | Atualizar o total para 42 portas, junto com as correções de Perímetro (5/6) e Cozinha (6/10). |
| 6 | media | `docs/ARQUITETURA.md` | O formato documentado inclui o campo `ts` (também nos comandos), mas nenhuma zona, o RFID Reader nem o broker enviam `ts`; só topic e payload. | Remover `ts` dos exemplos e da descrição do protocolo, ou implementá-lo no código. |
| 7 | media | `docs/ARQUITETURA.md` | O documento diz que o payload analógico é a leitura crua 0–1023, mas Sala, Quarto e Cozinha publicam temp em °C e umidade em %; só luz, vento, pressão e água (Jardim) saem em raw quantizado. | Documentar que temp/umidade vão em unidades reais e que só luz/água/vento/pressão são raw quantizado em passos de 10. |
| 8 | media | `docs/ARQUITETURA.md` | O verificador imprime "22 tópicos publicados, 7 lidos pelo broker, 15 só para o dashboard": o broker passou a ler também casa/perimetro/movimento via estado.get(), então o 7º não é o rfid. | Corrigir a nota para a saída real (7 lidos, 15 só dashboard) e explicar que o rfid é um 8º consumidor, tratado fora do estado.get(). |
| 9 | media | `docs/ARQUITETURA.md` | O movimento do Perímetro entra na regra da Central (tela INTRUSAO!/MOVIMENTO "No portao"), então a Central usa 8 tópicos, não os 7 da tabela, e a tabela só cita movimento da garagem. | Incluir casa/perimetro/movimento na tabela de regras da Central e corrigir as contagens para 8 decididos e 14 só exibidos. |
| 10 | media | `docs/ARQUITETURA.md` | O LCD mestre mostra "ACESSO OK" / "Cartao <id>" para cartão válido, não "ACESSO LIBERADO". | Trocar o texto documentado para "ACESSO OK". |
| 11 | media | `docs/ARQUITETURA.md` | O LCD mostra "CARTAO NEGADO" / "ID <n>" para cartão fora da whitelist, não "CARTAO INVALIDO". | Trocar o texto documentado para "CARTAO NEGADO". |
| 12 | media | `docs/ARQUITETURA.md` | O LCD mostra "MOVIMENTO" na linha 1 e "Na garagem" na linha 2, e o painel diz "MOVIMENTO NA GARAGEM"; o texto "MOVIMENTO — Garagem (normal)" não existe. | Descrever a tela real: "MOVIMENTO" / "Na garagem". |
| 13 | media | `docs/ARQUITETURA.md` | A nota da Cozinha diz que Environment.get("Smoke") é inferido e não testado, mas o código e a pendência da seção 8 da própria ARQUITETURA o dão como CONFIRMADO em 21/09 (build 9.0.1.0858). | Atualizar a nota da Cozinha para dizer que "Smoke" foi confirmado em 21/09/2026. |
| 14 | baixa | `docs/ARQUITETURA.md` | O aviso da Garagem trata a aceleração como pendente, mas a seção 8 a marca como RESOLVIDA via MODO_DEMO. | Reescrever o aviso apontando para MODO_DEMO como solução adotada. |
| 15 | media | `docs/MONTAGEM_PACKET_TRACER.md` | A ordem de montagem trata o tcp na MCU como pendente, mas está confirmado desde 02/07/2026 (inclusive no Passo 3 do mesmo guia). | Trocar por "tcp na MCU já confirmado (02/07/2026)". |
| 16 | baixa | `docs/MONTAGEM_PACKET_TRACER.md` | O painel mostra "ALERTA DE GAS" sem acento e "VISITANTE NA PORTA", não "ALERTA DE GÁS" nem "VISITANTE". | Usar os textos exatos "ALERTA DE GAS" e "VISITANTE NA PORTA". |
| 17 | baixa | `docs/MONTAGEM_PACKET_TRACER.md` | O Passo 4 diz que os detectores disparam com o Old Car, mas o mesmo guia (e a ARQUITETURA) os define como decorativos, sem influência; quem age é a leitura via environment. | Reescrever para "a leitura via environment passa de 20% → Fan + Porta + Alarme". |
| 18 | alta | `docs/BANCADA.md` | O cenário RFID manda conferir "ACESSO LIBERADO", texto que a Central nunca escreve (LCD e log mostram "ACESSO OK \| Cartao 1005"), levando a reprovar um teste correto. | Trocar para "ACESSO OK". |
| 19 | alta | `docs/BANCADA.md` | A lista de scripts a recolar (Central, Sala, Quarto) está desatualizada: Perímetro (reenviar_estado/publicar_se_mudou) e RFID Reader também mudaram na bancada de 23/09 e rodariam a versão antiga no nó. | Incluir Perímetro e RFID Reader (e a Central de 23/09) na lista de recolagem. |
| 20 | baixa | `docs/BANCADA.md` | A faixa do painel mostra "VISITANTE NA PORTA"; só o LCD mostra "VISITANTE". | Dizer "VISITANTE NA PORTA" no painel e "VISITANTE" no LCD. |
| 21 | baixa | `docs/BANCADA.md` | A BANCADA sugere esperar 10 s porque a zona às vezes reconecta sozinha, enquanto a regra (Sala, ARQUITETURA 7.1, TESTE_ISOLADO) é sempre reiniciar as zonas. | Alinhar: reiniciar as zonas sempre; remover a espera ou marcá-la como exceção não confiável. |
| 22 | alta | `docs/TESTE_ISOLADO.md` | O teste espera "CARTAO INVALIDO" no LCD, mas o código mostra "CARTAO NEGADO" / "ID <n>". | Trocar para "CARTAO NEGADO". |
| 23 | baixa | `docs/RETOMAR.md` | src/ tem hoje 15 arquivos .py (broker, 6 zonas, RFID, Heating Element e 6 diag_*), que o verificador conta, não 12 com 3 diagnósticos. | Atualizar a contagem e o número de diagnósticos. |
| 24 | media | `docs/RETOMAR.md` | A contagem não fecha (5+3≠6 zonas) e Cozinha e Quarto já rodaram e publicaram na bancada de 21/09, só o Jardim e a Garagem não haviam subido. | Corrigir para o estado real: Perímetro/Garagem/Sala validadas, Cozinha/Quarto publicando em 21/09, Jardim nunca rodou. |
| 25 | media | `docs/RETOMAR.md` | A "Ordem sugerida" ainda trata Environment.get("Smoke") como incógnita a testar primeiro, mas a tabela "O que foi provado" e o código o dão como confirmado em 21/09. | Marcar o passo 1 como concluído. |
| 26 | baixa | `docs/RETOMAR.md` | Com o movimento do Perímetro lido pelo broker, o verificador imprime 7 lidos e 15 só dashboard, e o 7º não é o rfid. | Atualizar a saída citada e a explicação do 7º tópico. |
| 27 | baixa | `docs/RETOMAR.md` | O documento diz que foi atualizado em 23/09, mas cita um arquivo criado em 25/09. | Atualizar a data do cabeçalho ou corrigir a data de criação do diagnóstico. |
| 28 | media | `docs/EVOLUCAO_HARDWARE_REAL.md` | O roadmap atribui a escolha de SBC ao bug analógico da MCU, mas o bug é só das A0–A3 e o critério adotado é o número de portas (6). | Reescrever: as zonas analógicas foram para SBC por terem mais de 6 dispositivos. |
| 29 | media | `README.md` | O README marca cozinha e quarto como nunca rodadas (e "escrito, a testar" na árvore), mas elas já publicaram no painel em 21/09; só o Jardim não subiu. | Reduzir a pendência para o Jardim e atualizar os rótulos de cozinha/quarto. |
| 30 | baixa | `README.md` | O README fala em cinco diag_*.py mas lista seis, e há seis em src/. | Corrigir para seis. |
| 32 | media | `CLAUDE.md` | O CLAUDE.md mantém aberto se a MCU-PT suporta tcp, mas README e ARQUITETURA o dão como confirmado em 02/07/2026. | Marcar como confirmado e remover o item em aberto. |
| 33 | media | `CLAUDE.md` | O CLAUDE.md descreve a mensagem com campo `ts`, que o código não envia. | Remover `ts` da descrição do formato. |
