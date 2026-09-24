# Ambiente simulado — clima de São Luís (MA) dentro do Packet Tracer

Contêiner novo no PT nasce com **temperatura 0 °C e luminosidade 0**. Com isso, metade das regras
do projeto nunca dispara: climatização da Sala e do Quarto (30 °C), luminária do Jardim e luz de
presença do Quarto (escuro) ficam todas paradas — e o sistema parece quebrado quando está correto.

Este documento define o ambiente que faz os cenários acontecerem **sozinhos**, com números de
Paço do Lumiar / São Luís, não com valores inventados. Serve duas vezes: destrava a bancada e vira
material de aula, porque o aluno vê a automação reagir a um clima que ele reconhece.

---

## 1. Onde se configura

**Physical Workspace** → selecionar o contêiner (o cômodo ou a área) → abrir o editor de
**Environment**. Cada grandeza tem um gráfico de 24 horas, editável ponto a ponto, e um
liga/desliga dos efeitos ambientais.

**Cada contêiner tem o seu ambiente.** Não existe clima global: configurar a Sala não muda o
Jardim. Isso é vantagem, não trabalho extra — é o que permite dar sol de verdade ao Jardim e luz
atenuada ao Quarto.

**Comece por um contêiner só** (a Sala), confira a leitura no terminal e só então replique. Se
errar a escala, é melhor descobrir uma vez que seis.

---

## 2. Como a leitura chega ao código

| Grandeza | Sensor | Conversão no script | Escala |
|---|---|---|---|
| Temperatura | Temperature Sensor | `para_celsius(raw)` | raw 0–1023 ↔ **−100 a +100 °C** |
| Umidade | Humidity Sensor | `para_percentual(raw)` | raw 0–1023 ↔ 0–100 % |
| Luminosidade | Photo Sensor | usada crua (quantizada) | raw 0–1023 |

**Consequência da faixa de temperatura:** 200 °C espalhados em 1023 passos dão **0,195 °C por
unidade**. Toda a faixa de interesse do projeto (24 a 33 °C) cabe em **46 passos**, entre raw 634 e
raw 680. É pouca resolução, mas suficiente: o limiar de 30 °C cai em **raw 665**.

| °C | raw |
|---|---|
| 24 | 634 |
| 26 | 644 |
| 28 | 655 (desliga o AC) |
| 30 | 665 (**liga o AC**) |
| 32 | 675 |
| 33 | 680 |
| **0** | **511** ← o que o contêiner entrega hoje |

---

## 3. Curva de temperatura — externa (Jardim, Perímetro, Garagem)

Setembro em São Luís: quente e estável, amplitude diária pequena. Mínima de madrugada,
máxima no meio da tarde.

| Hora | °C |
|---|---|
| 00 | 26,0 |
| 03 | 25,0 |
| **06** | **24,5** ← mínima |
| 09 | 29,0 |
| 12 | 31,5 |
| **14** | **32,5** ← máxima |
| 17 | 30,5 |
| 20 | 28,0 |
| 22 | 27,0 |

## 4. Curva de temperatura — interna (Sala, Quarto, Cozinha)

Interior de alvenaria amortece a oscilação e atrasa o pico: a casa esquenta depois do sol e demora
mais para esfriar. Amplitude menor, pico deslocado para o fim da tarde.

| Hora | °C |
|---|---|
| 00 | 27,0 |
| 03 | 26,0 |
| 06 | 25,5 |
| 09 | 28,0 |
| 12 | 30,0 |
| **16** | **31,0** ← máxima, mais tarde que a externa |
| 19 | 29,5 |
| 22 | 28,0 |

**O que isso produz na automação:** a Sala e o Quarto cruzam os 30 °C por volta das **12 h** e só
descem abaixo de 28 °C perto das **22 h**. Ou seja, o AC liga e desliga sozinho, uma vez por dia,
com a histerese fazendo o papel dela. É o cenário que hoje não existe.

---

## 5. Umidade

Setembro é o fim da estação seca — úmido para padrões brasileiros, seco para o padrão de São Luís.
Anda ao contrário da temperatura: máxima de madrugada, mínima no pico do calor.

| Hora | % |
|---|---|
| 00 | 84 |
| 06 | 88 |
| 09 | 78 |
| 14 | 62 |
| 17 | 70 |
| 20 | 80 |

O umidificador do Quarto liga **abaixo de 40 %** e só desliga ao voltar a 50 %. Com esta curva ele
**nunca liga** — e isso é honesto: em São Luís, umidificador é equipamento sem função. Para
demonstrar a regra, use uma curva de exceção (ar-condicionado ligado o dia todo resseca o quarto)
ou injete o valor por script. **Não altere o limiar só para a demonstração funcionar.**

---

## 6. Luminosidade

São Luís fica a 2°31' de latitude sul: dia e noite quase iguais o ano inteiro, nascer por volta das
**06 h** e pôr às **18 h 15**. Sem verão nem inverno perceptíveis — o que torna a curva simples.

| Hora | % |
|---|---|
| até 05:45 | 0 |
| 06:15 | 20 |
| 08:00 | 60 |
| 11:00 | 95 |
| 12:00 | 100 |
| 14:00 | 95 |
| 16:00 | 60 |
| 17:45 | 20 |
| 18:30 em diante | 0 |

**Interno:** aplicar a mesma curva com **teto de 40 a 50 %** — cômodo com janela recebe uma fração
da luz externa. É o que faz a luz de presença do Quarto ter sentido: com 100 % lá dentro, ela
nunca acenderia de dia.

**Limiares que dependem disso:**

| Regra | Limiar | Quando deve acontecer |
|---|---|---|
| Luminária do Jardim acende | luz ≤ 200 raw | a partir do fim de tarde |
| Luminária do Jardim apaga | luz ≥ 300 raw | depois do nascer do sol |
| Luz de presença do Quarto | luz ≤ 200 raw **e** movimento | à noite, e só com alguém no cômodo |

⚠️ **Estes dois limiares estão marcados como "CALIBRAR no PT" no código, e continuam assim.** 200
raw equivale a ~20 % da escala **se** o PT mapear luminosidade linearmente em 0–1023. Isso não está
verificado. O passo 8 resolve.

---

## 7. O relógio — conferir antes de montar a curva

A curva avança com o relógio do simulador. **Antes de investir tempo nos pontos, meça quanto tempo
simulado passa por minuto real.** Se a relação for 1:1, um dia leva 24 horas e nenhuma
demonstração de aula alcança o pico das 14 h.

Três saídas, em ordem de preferência:

1. **Acelerar o tempo**, se a versão oferecer o controle.
2. **Deslocar a curva:** pôr o pico na hora simulada atual. Feio, mas resolve em dois cliques e não
   mexe em código.
3. **Injetar por script** (`setContribution`, como o `diag_smoke.py` faz com fumaça). É o caminho do
   `diag_ambiente.py`, ainda não escrito.

Para **aula gravada ou apresentação**, a opção 2 é a mais segura: nada depende de esperar.

---

## 8. Calibração — o que medir depois de configurar

A Sala já imprime a linha que serve de aferição:

```
Temp 31C (raw 670 | ambiente do PT: 31.0C)
```

| Conferir | Aprovado se |
|---|---|
| `raw` × `para_celsius()` | o °C calculado bate com o "ambiente do PT" da mesma linha |
| Temperatura ao cruzar 30 °C | `Climatizacao: LIGOU (AC+Fan)` aparece **uma vez**, não em sequência |
| Histerese | o desligamento só vem abaixo de 28 °C, não a 29,9 |
| Luz ao anoitecer | anotar o `raw` no instante em que a luminária deveria acender |

**A última linha é a que fecha a pendência de calibração.** Anote o raw observado ao anoitecer e
ajuste `LIM_ESCURO` / `LIM_CLARO` para esse valor medido — e então troque o comentário "CALIBRAR no
PT" pelo número e pela data. Limiar calibrado sem registro volta a ser chute na próxima revisão.

---

## 9. Por que isto vale além da bancada

Um ambiente com número real transforma o projeto: em vez de "o sensor lê 0 e nada acontece", a casa
passa a **acordar, esquentar, acender e apagar sozinha** ao longo de um dia de São Luís. O aluno
deixa de acionar sensor com Alt+clique para ver a automação responder ao clima da cidade onde ele
mora — e a diferença entre a curva externa e a interna vira, de graça, uma aula sobre por que se
mede o ambiente no lugar certo.
