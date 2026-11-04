# Ambiente climático para o Packet Tracer

Gerador do arquivo de ambiente que o Cisco Packet Tracer importa na janela **Environments**,
com o clima de São Luís (MA) — e um tutorial para trocar por qualquer outra cidade.

## O problema que isto resolve

Contêiner novo no Packet Tracer nasce com **temperatura 0 °C e luminosidade 0**, e assim fica
para sempre. Num projeto de automação residencial, isso significa que metade das regras nunca
dispara: o ar-condicionado espera 30 °C que não chegam, a luminária espera um anoitecer que não
acontece, e quem está testando conclui que o código está quebrado quando ele está certo.

Dá para montar a curva clicando no editor do PT. O problema aparece depois: o arquivo repete
**56 grandezas em cada keyframe**, então editar à mão erra, e o resultado não dá para revisar em
diff nem versionar junto com o projeto.

Aqui o clima é **dado**: uma tabela de `(hora, valor)` por grandeza. O gerador cuida do resto.

E há um ganho que não é óbvio: **o `.pkt` é binário e cifrado, mas o ambiente é XML.** Esta é a
única parte do estado do simulador que cabe no git de verdade.

## Uso

```bash
python3 gerar_ambiente.py --listar
python3 gerar_ambiente.py --perfil sao-luis-seco
python3 gerar_ambiente.py --perfil sao-luis-chuvoso --escala 60
```

Python 3 puro, sem dependências. A saída vai para `ambiente_<perfil>.xml` nesta pasta.

O gerador imprime o que a curva vai produzir, antes de você abrir o simulador:

```
  20 keyframes, 9 grandezas ativas de 56 do catalogo
  escala: 1 min real = 30 min simulados (um dia em 48 min reais)
  temperatura: minima 24.5 C as 06.0h, maxima 32.5 C as 14.0h
  acima de 30 C (liga o AC): das 10.5h as 17.5h
```

A última linha é a mais útil: ela diz **em que horário simulado o ar-condicionado vai ligar**. Se
disser "nunca chega a 30 C", não adianta esperar.

### Importar no Packet Tracer

Physical Workspace → janela **Environments** → aba **Advanced** → botão **Import File**.
(Do lado dele fica o `Export File`, que é como este gerador foi modelado.)

Isso carrega o ambiente na `Location` atual, e vale para a sessão.

**Para não reimportar a cada sessão**, copie o XML para a pasta de templates da instalação:

```
C:\Arquivos de Programas\Cisco Packet Tracer 9.0.1\templates\environments\
```

Ele passa a aparecer junto com os `Default *.xml` que vêm de fábrica.

> ⚠️ **Essa pasta fica dentro da instalação e some numa atualização ou reinstalação do Packet
> Tracer.** O arquivo versionado neste repositório é a fonte; o que está em `templates/` é cópia.

### Para o ambiente já subir carregado, sem importar nada

Copiar o XML para `templates/environments/` faz ele **aparecer na lista**, mas não o torna o padrão
— e o dropdown `Defaults:` da aba Advanced também não resolve isso. **O Packet Tracer carrega o
arquivo pelo nome.** O caminho que funciona (confirmado em 23/09/2026, PT 9.0.1):

1. Renomear os originais, para ter volta: `Default City.xml` → `Default City_orig.xml`, e o mesmo
   com `Default Intercity.xml`.
2. Copiar o seu ambiente por cima, **com o nome `Default City.xml`** (e `Default Intercity.xml`,
   se quiser o nível intercidades também).
3. Reabrir o Packet Tracer: ele sobe com o seu clima.

> **Confira o tamanho do arquivo depois de copiar.** É o jeito mais rápido de saber qual perfil
> ficou no lugar — dois arquivos com nome parecido e conteúdo diferente são fáceis de trocar, e o
> sintoma aparece só meia hora depois, quando uma automação não dispara no horário previsto.

### ⚠️ Cada contêiner tem o seu ambiente — inclusive os de dentro

Trocar o `Default City.xml` resolve a cidade. **Não resolve os cômodos.** Um contêiner aninhado
nasce de outro template (`Default Container.xml`, `Default Building.xml`, `Default Closet.xml`) e
roda o clima genérico da Cisco, independente do que a cidade estiver fazendo.

> **Diagnóstico de 03/11/2026 (PT 9.0.1.0858).** Com o clima de São Luís importado no contêiner onde os
> dispositivos estão (`Corporate Office`), o ambiente subiu a cerca de 2,4 °C/min até alcançar a curva e
> passou a acompanhá-la: 27,9 °C medidos contra 27,9 °C previstos. Sensor e ambiente coincidem dentro
> da resolução do `raw`, de cerca de 0,8 °C. Depois de 8 ciclos do ar-condicionado, o ambiente voltou
> para a curva: 30,71 °C contra 30,73 °C. O −1 °C de 23/09 **não se repetiu**, e a causa daquele dia não
> ficou provada; contêiner com clima de fábrica é a explicação mais provável.
>
> **Ainda sem explicação:** ao abrir o `.pkt`, o ambiente caiu de 17,7 °C a 12,9 °C antes de subir para a
> curva. Espere uns 12 minutos depois de abrir o arquivo antes de confiar na temperatura.

**Como saber:** abra `Environments`, escolha a `Location` e clique em **Edit → Advanced**. O campo de notas
mostra a descrição do perfil, como `Sao Luis (MA), estacao seca`; se estiver vazio, é o clima de fábrica.
No modo View a nota não aparece, porque o gerador grava `SHOW_NOTES=false`.

**Como corrigir:** trocar o `Location:` para o contêiner que tem os dispositivos, importar o XML ali e
**salvar o `.pkt`**. O arquivo guarda o clima: conferido ao salvar e reabrir em 03/11/2026, na mesma máquina.

**Por que isso engana:** o script lê o contêiner onde o SBC está. O painel mostra a Location
selecionada, que pode ser outra. Dá para perder bastante tempo procurando erro
no código antes de desconfiar de qual ambiente está sendo lido.

### Arquivo enxuto, para quem vai deixar como template

Os templates da própria Cisco têm 125 KB. Um ambiente com 20 keyframes passa de 800 KB, porque
**cada keyframe repete as 56 grandezas**. Se o arquivo vai ser carregado a cada inicialização,
vale enxugar:

```bash
python3 gerar_ambiente.py --perfil sao-luis-seco --tolerancia 5
```

A `--tolerancia` remove keyframes que não mudam a forma da curva, aceitando erro de até N % da
amplitude **de cada grandeza** — percentual e não absoluto, senão um limite em graus seria severo
demais para a luz (0–100) e frouxo demais para a temperatura (8 °C de amplitude).

Medido no perfil seco:

| Tolerância | Keyframes | Tamanho | Erro na temperatura | Erro na luz | Janela do AC |
|---|---|---|---|---|---|
| 0 | 20 | 834 KB | — | — | 10h30–17h30 |
| **5 %** | **12** | **514 KB** | **0,33 °C** | 3,3 % | 10h30–17h30 |
| 12 % | 9 | 395 KB | 0,78 °C | 10 % | 10h30–17h30 |

**5 % é o ponto de equilíbrio:** 0,33 °C é menos de dois passos do sensor, que tem resolução de
0,195 °C. Acima disso a curva de luz começa a se deformar de verdade.

E o que mais importa: **a janela em que o ar-condicionado liga não muda em nenhum nível.** A
simplificação corta ponto redundante, não altera comportamento.

> O gerador foi modelado a partir de um ambiente exportado pelo **PT 9.0.1**. Na primeira
> importação, confira se a janela aceita o arquivo direto; se ela esperar algum invólucro em volta
> de `<ENVIRONMENT>`, é uma linha de ajuste no gerador.

## Como o ambiente do PT funciona

Cinco coisas que valem saber antes de mexer:

**1. Keyframes em segundos do dia.** `0` é meia-noite, `43200` é meio-dia, `86400` fecha o ciclo.
O PT interpola linearmente entre eles (`INTERPOLATE=true`), e o gerador faz a mesma conta na
prévia — por isso os horários que ele imprime batem com o simulador.

**2. Todo keyframe carrega todas as grandezas.** Um ponto novo na curva da luz obriga a calcular
também a temperatura naquele instante. O gerador resolve isso sozinho: ele junta as horas de todas
as curvas e interpola cada grandeza em cada ponto.

**3. `ACTIVE` liga a grandeza.** Grandeza fora do perfil sai com `ACTIVE=false` e não afeta nada.
Cuidado ao editar à mão: **`ACTIVE=false` em um único keyframe** já foi visto num arquivo editado
pelo editor gráfico, e o efeito é a grandeza sumir naquele trecho do dia.

**4. `TRANSFERENCE` é quanto do ambiente do contêiner-pai chega ao filho, em porcentagem.** Todas
as grandezas saem em 100. É a alavanca para simular interior: baixando a transferência da luz
visível para ~40 % no contêiner da casa, os cômodos recebem uma fração do sol — que é o
comportamento físico real, e evita ter de manter duas curvas.

> Este item ainda não foi confirmado experimentalmente neste projeto. Teste rápido: mude a
> transferência de uma grandeza para 50 num contêiner filho e veja se a leitura cai pela metade.

**5. A temperatura tem limite de variação, as outras não.**

```xml
<MIN_RATE>-0.00138889</MIN_RATE>
<MAX_RATE>0.00138889</MAX_RATE>
```

0,00138889 por segundo = **5 °C por hora simulada**. Degrau de temperatura não existe: o PT rampeia
até o valor novo. Numa escala de 1:30, são 2,5 °C por minuto real. O gerador recusa curva mais
íngreme que esse limite, porque ela produziria horários diferentes dos previstos.

> **O limite vale para a curva, não para os atuadores.** Medido em 23/09: com o ar-condicionado
> ligado, o ambiente caiu a **3,31 °C/min real** — acima do teto de 2,50 °C/min que o `MAX_RATE`
> imporia. A contribuição de um dispositivo (`Environment.setContribution`) passa por cima do
> limite da curva. Na prática isso é bom: significa que a automação consegue vencer o clima, que é
> o que se espera de um ar-condicionado.

**6. A escala de tempo.** `--escala 30` significa 1 minuto real = 30 minutos simulados, ou seja, um
dia inteiro em 48 minutos. Para calibrar, 30 dá tempo de anotar valores; para apresentar, 60 ou 120
encurta o dia para 24 ou 12 minutos.

## Trocar São Luís pela sua cidade

**Acrescente** sua cidade ao dicionário `PERFIS` do `gerar_ambiente.py`, sem apagar os perfis que
já existem, e gere com `python3 gerar_ambiente.py --perfil minha-cidade`. Sem `--perfil`, o padrão
continua sendo `sao-luis-seco`.

```python
PERFIS = {
    # ... perfis existentes ...
    "minha-cidade": {
        "descricao": "Cidade (UF), estação seca",
        "curvas": {
            "Ambient Temperature": [
                (0, 22.0), (6, 19.0), (14, 31.0), (20, 25.0), (24, 22.0),
            ],
            "Humidity":     [(0, 70), (6, 80), (14, 45), (20, 65), (24, 70)],
            "Visible Light": [(0, 0), (6, 5), (12, 100), (18, 5), (18.5, 0), (24, 0)],
        },
    },
}
```

A hora vai de 0 a 24 e **aceita fração**: `6.5` é 06h30.

### Onde buscar os números

- **Temperatura e umidade:** Normais Climatológicas do INMET, que trazem média das máximas, média
  das mínimas e umidade relativa por mês. Escolha um mês representativo da estação que quer simular.
- **Nascer e pôr do sol:** efemérides do Observatório Nacional. É o que define onde a curva de luz
  sobe e desce — e quanto mais longe do equador, mais isso muda entre verão e inverno.
- **Vento:** estações do INMET, ou a média da região.

Três dicas de quem já errou isso:

1. **A mínima é ao amanhecer, não à meia-noite.** Curva que começa na mínima em `0h` parece certa
   no gráfico e está errada na física.
2. **A umidade anda ao contrário da temperatura.** Máxima de madrugada, mínima no pico do calor.
3. **Interior atrasa e amortece.** Uma casa de alvenaria chega ao pico umas duas horas depois da
   rua, e com amplitude menor. Se você não for usar `TRANSFERENCE`, modele isso na curva.

### O gerador recusa perfil com erro

Antes de gravar, ele confere — e cada checagem veio de um erro real de bancada:

| Checagem | Por que existe |
|---|---|
| Grandeza existe no catálogo do PT | nome errado passa despercebido e a curva simplesmente não age |
| Horas em ordem e cobrindo 0 a 24 h | trecho sem cobertura vira valor congelado |
| **Valor em 0 h igual ao de 24 h** | senão a grandeza salta na virada do dia |
| Valor dentro de `MIN..MAX` | o PT satura sem avisar |
| Variação dentro do `MAX_RATE` | curva íngreme demais é promessa que o simulador não cumpre |

## O que cada grandeza aciona neste projeto

Se você for reaproveitar o gerador em outro projeto, esta tabela muda — mas serve de modelo do que
conferir.

| Grandeza | Limiar no código | O que acontece |
|---|---|---|
| Ambient Temperature | ≥ 30 °C liga, ≤ 28 °C desliga | AC e ventilador da Sala; AC do Quarto |
| Humidity | < 40 % liga, ≥ 50 % desliga | umidificador do Quarto |
| Visible Light | ≤ 200 raw acende, ≥ 300 apaga | luminária do Jardim, luz de presença do Quarto |
| Water Level | ≤ 15 cm irriga, ≥ 80 cm drena | irrigação e dreno do Jardim |

**Um resultado honesto do perfil de São Luís:** o umidificador **nunca liga**, porque a umidade não
desce de 62 %. Está certo — em São Luís, umidificador é equipamento sem função. O perfil chuvoso,
pelo mesmo motivo, mal encosta nos 30 °C: o ar-condicionado quase não trabalha.

**Não mude o limiar para a demonstração funcionar.** Se precisar exercitar uma regra que o clima
local não produz, injete o valor por script (é o que o `src/diag_smoke.py` faz com fumaça) e deixe
o clima em paz. Limiar ajustado para a demo é limiar que mente sobre o projeto.

## Calibração — o passo que fecha a conta

O sensor de temperatura do PT devolve `raw` de 0 a 1023 mapeado em **−100 a +100 °C**: 0,195 °C por
unidade, e toda a faixa de interesse (24 a 33 °C) cabe em 46 passos, entre raw 634 e raw 680.

| °C | raw |
|---|---|
| 24 | 634 |
| 28 | 655 (desliga o AC) |
| 30 | 665 (**liga o AC**) |
| 33 | 680 |
| **0** | **511** ← o que um contêiner sem ambiente entrega |

Com o ambiente carregado, a zona da Sala imprime a linha de aferição:

```
Temp 31C (raw 670 | ambiente do PT: 31.0C)
```

Os dois números batendo confirmam a conversão. Se o `raw` estiver em 511 e o ambiente em 0, o
ambiente não foi aplicado àquele contêiner.

**Confirmado na bancada de 23/09/2026, PT 9.0.1.0858:** `raw 650` → 27,08 °C pela fórmula, contra
27,1 °C do termômetro do simulador. Dois centésimos de diferença.

Na mesma medição apareceu um efeito que engana: enquanto o ambiente sobe rápido, **o sensor vem
atrás**. No mesmo intervalo, `raw 646` dava 26,30 °C contra 27,0 °C do ambiente — 0,7 °C de
defasagem, que some quando a rampa desacelera. Ao conferir a calibração, use uma leitura com o
ambiente estável, não uma tirada no meio da subida.

### Diagnóstico rápido: a umidade bate e a temperatura não

Se, depois de importar, a umidade do painel coincidir com o que a zona publica **e a temperatura
não**, a primeira suspeita é o `MAX_RATE`. Ele não explica valor abaixo da curva: nesse caso, veja
o aviso de diagnóstico em aberto, mais acima, e rode o `src/diag_temperatura.py`.

A `Ambient Temperature` é a **única** grandeza do catálogo com limite de variação (±5 °C por hora
simulada). Todas as outras vêm com ±1000, que na prática é ilimitado. Então, no instante do
import:

- umidade, nuvens, pressão e nível de água **saltam** para o valor da curva
- a temperatura **rampeia** de onde estava, a 2,5 °C/min na escala 1:30

Medido em 23/09: painel em 26,12 °C e umidade 83,69 %, com a zona publicando umidade 83 e
temperatura 5. A umidade bater é o que prova que a zona está lendo o contêiner certo — se fosse
Location errada, as duas estariam divergentes.

Basta esperar: `(alvo − atual) ÷ 2,5` dá os minutos que faltam.

### O ambiente demora a "esquentar"

Ao importar, o ambiente não salta para o valor da curva: ele parte de onde estava (0 °C num
contêiner novo) e **sobe respeitando o `MAX_RATE` de 5 °C por hora simulada**. Numa escala de 1:30
isso dá 2,5 °C por minuto real, ou seja, **uns 10 minutos até alcançar uma curva que comece perto
dos 25 °C**. Medido em 23/09: 2,8 °C às 11h34, 27,1 °C às 11h48, intervalo que não fixa a taxa,
porque a rampa pode ter alcançado a curva antes do fim.

Não é defeito, e não adianta reimportar achando que falhou. Se precisar do ambiente quente logo no
começo de uma aula, importe antes e deixe rodando enquanto a turma chega.

**Os limiares de luz estão resolvidos:** medido em 03/11/2026, o Photo Sensor lê praticamente só 0 ou 1023, com a virada
perto das 17h45 simuladas. Qualquer limiar entre os extremos funciona. Ao acender, a luminária do Jardim pode
iluminar o próprio sensor e piscar uma vez, por poucos segundos.
