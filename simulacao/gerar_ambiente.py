#!/usr/bin/env python3
# =====================================================================
# GERADOR DE AMBIENTE PARA O CISCO PACKET TRACER
# ---------------------------------------------------------------------
# Produz o XML de ambiente que o Packet Tracer importa na janela
# Environments, a partir de um perfil climatico escrito como DADO --
# uma tabela de (hora, valor) por grandeza.
#
# Por que existe: contêiner novo no PT nasce com temperatura 0 C e
# luminosidade 0, e nesse ambiente metade das regras de uma casa
# automatizada nunca dispara. Montar a curva clicando no editor
# funciona, mas o arquivo repete 56 grandezas em cada keyframe: editar
# a mao erra, e o resultado nao da para revisar nem versionar.
#
# Uso:
#   python3 gerar_ambiente.py --listar
#   python3 gerar_ambiente.py --perfil sao-luis-seco
#   python3 gerar_ambiente.py --perfil sao-luis-chuvoso --escala 60
#
# Como adicionar a sua cidade: ver README.md nesta pasta. Nao e preciso
# mexer em nada alem do dicionario PERFIS.
#
# Python 3 puro, sem dependencias -- roda em qualquer maquina de aluno.
# =====================================================================

import argparse
import os
import sys

SEGUNDOS_NO_DIA = 86400

# Limite de variacao da temperatura ambiente no PT: 0,00138889 por
# segundo = 1/720 = 5 C por hora simulada. Todas as outras grandezas
# vem com +-1000, que na pratica e "sem limite". Consequencia: degrau
# de temperatura nao existe, o simulador rampeia ate o valor novo.
TAXA_PADRAO = (-1000.0, 1000.0)
TAXA_TEMPERATURA = (-0.00138889, 0.00138889)


def _g(
    id_,
    nome,
    categoria,
    minimo,
    maximo,
    unidade,
    show=True,
    imp="",
    f_imp="",
    f_met="",
    taxa=TAXA_PADRAO,
):
    """Uma linha do catalogo de grandezas do PT."""
    return {
        "id": id_,
        "nome": nome,
        "categoria": categoria,
        "min": minimo,
        "max": maximo,
        "unidade": unidade,
        "show": show,
        "imperial": imp,
        "formula_imperial": f_imp,
        "formula_metrica": f_met,
        "taxa": taxa,
    }


# Catalogo completo, extraido de um ambiente exportado pelo PT 9.0.1.
# A ORDEM IMPORTA: o PT grava em ordem alfabetica de ID, e manter a
# mesma ordem deixa o diff do git legivel quando so o valor muda.
CATALOGO = [
    _g("Alpha", "Alpha", "Radiation", 0, 100, "%", False),
    _g(
        "Ambient Temperature",
        "Ambient Temperature",
        "Temperature",
        -100,
        100,
        "C",
        True,
        "F",
        "x*(9/5)+32",
        "(x-32)*(5/9)",
        TAXA_TEMPERATURA,
    ),
    _g("Argon", "Argon", "Gases", 0, 100, "%"),
    _g(
        "Atmospheric Pressure",
        "Atmospheric Pressure",
        "Other",
        -100,
        200,
        "kPa",
        True,
        "psi",
        "x*.14503773773020923",
    ),
    _g("Beta", "Beta", "Radiation", 0, 100, "%", False),
    _g("CO", "CO", "Gases", 0, 100, "%"),
    _g("CO2", "CO<sub>2</sub>", "Gases", 0, 100, "%"),
    _g("Clouds", "Clouds", "Water", 0, 100, "%"),
    _g("Compaction", "Compaction", "Earth Physical Features", 0, 100, "Moh", False),
    _g(
        "Composition Hardness",
        "Composition Hardness",
        "Earth Physical Features",
        0,
        100,
        "Moh",
        False,
    ),
    _g(
        "Electromagnetic Radiation",
        "Electromagnetic Radiation",
        "Light (Sun)",
        0,
        100,
        "%",
    ),
    _g(
        "Elevation",
        "Elevation",
        "Earth Physical Features",
        0,
        100000,
        "m",
        True,
        "ft",
        "x*3.2808",
        "x/3.280",
    ),
    _g("Fire", "Fire", "Temperature", 0, 100, "", False),
    _g("Gamma", "Gamma", "Radiation", 0, 100, "%", False),
    _g(
        "Gravity",
        "Gravity",
        "Gravity",
        -100,
        100,
        "m/s<sup>2</sup>",
        True,
        "ft/s<sup>2</sup>",
        "x*3.2808399",
        "x*0.3048",
    ),
    _g(
        "Heat",
        "Heat (BTUs)",
        "Energy",
        -100,
        100,
        "KW",
        False,
        "BTU/hr",
        "x*0.00029307103866",
        "x*3412.142",
    ),
    _g("Helium", "He", "Gases", 0, 100, "%"),
    _g("Humidity", "Humidity", "Water", 0, 100, "%"),
    _g("Hydrogen", "H", "Gases", 0, 100, "%"),
    _g("Infrared", "Infrared", "Light (Sun)", 0, 100, "%"),
    _g("Ionization", "Ionization", "Temperature", 0, 100, "%", False),
    _g("Luminosity", "Luminosity", "Light (Sun)", 0, 100, "%", False),
    _g("Methane", "Methane", "Gases", 0, 100, "%"),
    _g("Moon Phases", "Moon Phases", "Gravity", -100, 100, "", False),
    _g("Motion Direction", "Direction", "Motion", -100, 100, "degrees", False),
    _g(
        "Motion Speed",
        "Speed",
        "Motion",
        0,
        100,
        "kph",
        False,
        "mph",
        "x/1.609344",
        "x*1.609344",
    ),
    _g("Neutron", "Neutron", "Radiation", 0, 100, "%", False),
    _g("Nitrogen", "Nitrogen", "Gases", 0, 100, "%"),
    _g("O2", "O<sub>2</sub>", "Gases", 0, 100, "%"),
    _g("Ohms", "Ohms", "Electricity", -100, 100, "&#8486;", False),
    _g("Ozone", "Ozone", "Gases", 0, 100, "%", False),
    _g("Photon", "Photon", "Radiation", 0, 100, "%", False),
    _g("Propane", "Propane", "Gases", 0, 100, "%", False),
    _g("Radiant Heat", "Radiant Heat", "Light (Sun)", 0, 100, "%"),
    _g("Radiation Level", "Level", "Radiation", 0, 1000, "mrem"),
    _g("Rain", "Rain", "Water", -100, 100, "cm", True, "in", "x*0.39", "x*2.54"),
    _g("Smoke", "Smoke", "Temperature", 0, 100, "%", False),
    _g("Snow", "Snow", "Water", -100, 100, "cm", True, "in", "x*0.39", "x*2.54"),
    _g("Soil pH", "Soil pH", "Earth Physical Features", 0, 100, "pH"),
    _g("Sound Pitch", "Pitch", "Sound", 0, 100, "CPS", False),
    _g("Sound Volume", "Volume", "Sound", 0, 100, "dB", False),
    _g("Sunlight", "Sunlight", "Light (Sun)", 0, 100, "%"),
    _g(
        "Torque",
        "Torque",
        "Energy",
        -100,
        100,
        "m/kg",
        False,
        "ft/lb",
        "x*1.48816",
        "x*0.671969",
    ),
    _g("Ultraviolet", "Ultraviolet", "Light (Sun)", 0, 100, "%"),
    _g("Visible Light", "Visible", "Light (Sun)", 0, 100, "%"),
    _g("Voltage", "Voltage", "Electricity", -100, 100, "V", False),
    _g(
        "Water Level",
        "Water Level",
        "Water",
        0,
        100,
        "cm",
        True,
        "in",
        "x*0.39",
        "x*2.54",
    ),
    _g(
        "Water Speed",
        "Speed",
        "Water",
        0,
        1000,
        "kph",
        False,
        "mph",
        "x/1.609344",
        "x*1.609344",
    ),
    _g(
        "Water Temperature",
        "Temperature",
        "Water",
        -100,
        100,
        "C",
        False,
        "F",
        "x*(9/5)+32",
        "(x-32)*(5/9)",
    ),
    _g(
        "Water Volume",
        "Volume",
        "Water",
        0,
        10000,
        "L",
        False,
        "gal",
        "x*0.26417",
        "x/0.26417",
    ),
    _g("Water pH", "Water pH", "Water", 0, 100, "pH", False),
    _g("Watts", "Watts", "Electricity", -100, 100, "W", False),
    _g("White Noise", "White Noise", "Sound", 0, 100, "%", False),
    _g("Wind Direction", "Direction", "Wind", -100, 100, "degrees"),
    _g("Wind Gusts", "Variance (gusts)", "Wind", 0, 100, "%"),
    _g(
        "Wind Speed",
        "Speed",
        "Wind",
        0,
        100,
        "kph",
        True,
        "mph",
        "x/1.609344",
        "x*1.609344",
    ),
]


# =====================================================================
# PERFIS CLIMATICOS
# ---------------------------------------------------------------------
# Cada perfil e um dicionario {ID da grandeza: [(hora, valor), ...]}.
# A hora vai de 0 a 24 e aceita fracao (6.5 = 06h30). O gerador
# interpola linearmente entre os pontos, que e o mesmo que o PT faz
# entre keyframes.
#
# REGRA: o valor em 0 e o valor em 24 devem ser iguais, senao a
# temperatura pula na virada do dia e o ciclo nao fecha.
#
# Fonte dos numeros: normais climatologicas de Sao Luis (MA), clima
# tropical Aw/Am, latitude 2 graus 31' S. Sao valores aproximados e de
# ordem de grandeza correta -- para trabalho academico que dependa do
# dado exato, use as Normais Climatologicas do INMET.
# =====================================================================

PERFIS = {
    "sao-luis-seco": {
        "descricao": "Sao Luis (MA), estacao seca -- setembro a novembro",
        "curvas": {
            # Minima ao amanhecer, maxima no meio da tarde. Amplitude
            # pequena: 8 C entre a minima e a maxima, tipico de litoral
            # equatorial.
            "Ambient Temperature": [
                (0, 26.0),
                (3, 25.0),
                (6, 24.5),
                (9, 29.0),
                (12, 31.5),
                (14, 32.5),
                (17, 30.5),
                (20, 28.0),
                (22, 27.0),
                (24, 26.0),
            ],
            # Anda ao contrario da temperatura: maxima de madrugada,
            # minima no pico do calor.
            "Humidity": [
                (0, 84),
                (3, 87),
                (6, 88),
                (9, 78),
                (12, 66),
                (14, 62),
                (17, 68),
                (20, 78),
                (22, 82),
                (24, 84),
            ],
            # Nascer ~06h, por ~18h15, praticamente o ano inteiro --
            # a 2 graus do equador nao ha verao nem inverno de luz.
            "Visible Light": [
                (0, 0),
                (5.5, 0),
                (6, 10),
                (7, 35),
                (8, 60),
                (11, 95),
                (12, 100),
                (14, 95),
                (16, 60),
                (17, 35),
                (18, 10),
                (18.5, 0),
                (24, 0),
            ],
            "Sunlight": [
                (0, 0),
                (5.5, 0),
                (6, 10),
                (8, 60),
                (12, 100),
                (16, 60),
                (18, 10),
                (18.5, 0),
                (24, 0),
            ],
            # Brisa maritima: calmaria de madrugada, reforco a tarde.
            "Wind Speed": [
                (0, 10),
                (6, 8),
                (12, 16),
                (15, 20),
                (18, 16),
                (21, 12),
                (24, 10),
            ],
            "Clouds": [(0, 20), (12, 25), (16, 30), (24, 20)],
            "Rain": [(0, 0), (24, 0)],  # estacao seca: nao chove
            "Atmospheric Pressure": [(0, 101.0), (10, 101.3), (16, 100.9), (24, 101.0)],
            # Solo seco: abaixo do limiar de irrigacao do Jardim, entao
            # a irrigacao liga sozinha -- e o proprio sprinkler eleva o
            # nivel, fechando a malha.
            "Water Level": [(0, 12), (24, 12)],
        },
    },
    "sao-luis-chuvoso": {
        "descricao": "Sao Luis (MA), estacao chuvosa -- fevereiro a maio",
        "curvas": {
            # Chuva e nuvem derrubam a maxima em ~2,5 C e sustentam a
            # minima: o dia fica mais fresco E mais abafado.
            "Ambient Temperature": [
                (0, 25.0),
                (3, 24.0),
                (6, 23.5),
                (9, 27.5),
                (12, 29.5),
                (14, 30.0),
                (17, 28.0),
                (20, 26.5),
                (22, 25.5),
                (24, 25.0),
            ],
            "Humidity": [
                (0, 90),
                (6, 93),
                (9, 86),
                (12, 78),
                (14, 74),
                (16, 80),
                (18, 86),
                (21, 89),
                (24, 90),
            ],
            # Mesmo nascer e por do sol, mas o teto cai: nuvem densa
            # tira um terco da luz mesmo ao meio-dia.
            "Visible Light": [
                (0, 0),
                (5.5, 0),
                (6, 8),
                (8, 40),
                (11, 65),
                (12, 70),
                (14, 55),
                (16, 35),
                (17, 20),
                (18, 6),
                (18.5, 0),
                (24, 0),
            ],
            "Sunlight": [
                (0, 0),
                (5.5, 0),
                (6, 8),
                (8, 40),
                (12, 70),
                (16, 35),
                (18, 6),
                (18.5, 0),
                (24, 0),
            ],
            "Wind Speed": [(0, 8), (6, 6), (12, 12), (16, 18), (20, 10), (24, 8)],
            "Clouds": [(0, 70), (9, 75), (14, 90), (18, 85), (24, 70)],
            # Pancada de fim de tarde, que e o padrao da estacao.
            "Rain": [
                (0, 0),
                (13, 0),
                (15, 3),
                (16, 6),
                (17, 4),
                (18, 1),
                (19, 0),
                (24, 0),
            ],
            "Atmospheric Pressure": [(0, 100.6), (10, 100.9), (16, 100.4), (24, 100.6)],
            # Solo encharcado: acima do limiar de alagamento do Jardim,
            # entao quem liga e o dreno, nao a irrigacao.
            "Water Level": [(0, 78), (14, 80), (17, 88), (20, 84), (24, 78)],
        },
    },
}


# =====================================================================
# Geracao
# =====================================================================


def interpolar(curva, hora):
    """Valor da curva numa hora qualquer, por interpolacao linear.

    E o mesmo comportamento que o PT aplica entre keyframes com
    INTERPOLATE=true, entao a previa aqui bate com o simulador."""
    if hora <= curva[0][0]:
        return float(curva[0][1])
    if hora >= curva[-1][0]:
        return float(curva[-1][1])
    for i in range(len(curva) - 1):
        h0, v0 = curva[i]
        h1, v1 = curva[i + 1]
        if h0 <= hora <= h1:
            if h1 == h0:
                return float(v1)
            fracao = (hora - h0) / (h1 - h0)
            return float(v0) + (float(v1) - float(v0)) * fracao
    return float(curva[-1][1])


def horas_do_perfil(curvas):
    """Uniao das horas usadas por todas as grandezas, em ordem.

    Cada keyframe do PT carrega TODAS as grandezas, entao um ponto novo
    na curva da luz obriga a calcular tambem a temperatura naquela hora.
    Por isso a uniao, e nao a lista de cada uma em separado."""
    horas = set([0.0, 24.0])
    for curva in curvas.values():
        for hora, _ in curva:
            horas.add(float(hora))
    return sorted(horas)


def esc(texto):
    """Escapa como o PT escapa: & e < viram entidade, > fica cru."""
    return str(texto).replace("&", "&amp;").replace("<", "&lt;")


def bloco_grandeza(item, valor, ativa, indent):
    """Um <ENVIRONMENT_OPTION>, que e como o PT descreve uma grandeza."""
    esp = " " * indent
    linhas = [
        "{}<ENVIRONMENT_OPTION>".format(esp),
        "{}  <CATEGORY_ID>{}</CATEGORY_ID>".format(esp, esc(item["categoria"])),
        "{}  <ID>{}</ID>".format(esp, esc(item["id"])),
        "{}  <NAME>{}</NAME>".format(esp, esc(item["nome"])),
        "{}  <CATEGORY>{}</CATEGORY>".format(esp, esc(item["categoria"])),
        "{}  <TRANSFERENCE>100</TRANSFERENCE>".format(esp),
        "{}  <SHOW>{}</SHOW>".format(esp, "true" if item["show"] else "false"),
        "{}  <INTERPOLATE>true</INTERPOLATE>".format(esp),
        "{}  <ACTIVE>{}</ACTIVE>".format(esp, "true" if ativa else "false"),
        "{}  <VALUE>{}</VALUE>".format(esp, formatar_numero(valor)),
        "{}  <MIN>{}</MIN>".format(esp, formatar_numero(item["min"])),
        "{}  <MAX>{}</MAX>".format(esp, formatar_numero(item["max"])),
        "{}  <MIN_RATE>{}</MIN_RATE>".format(esp, formatar_numero(item["taxa"][0])),
        "{}  <MAX_RATE>{}</MAX_RATE>".format(esp, formatar_numero(item["taxa"][1])),
        "{}  <METRIC_UNIT>{}</METRIC_UNIT>".format(esp, esc(item["unidade"])),
        "{}  <IMPERIAL_UNIT>{}</IMPERIAL_UNIT>".format(esp, esc(item["imperial"])),
        "{}  <IMPERIAL_CONVERSION_FORMULA>{}</IMPERIAL_CONVERSION_FORMULA>".format(
            esp, esc(item["formula_imperial"])
        ),
        "{}  <METRIC_CONVERSION_FORMULA>{}</METRIC_CONVERSION_FORMULA>".format(
            esp, esc(item["formula_metrica"])
        ),
        "{}</ENVIRONMENT_OPTION>".format(esp),
    ]
    return "\n".join(linhas)


def formatar_numero(valor):
    """Inteiro sai sem casa decimal, como o PT grava."""
    numero = float(valor)
    if numero == int(numero) and abs(numero) < 1e15:
        return str(int(numero))
    return repr(round(numero, 8))


def erro_da_reconstrucao(curva, horas, grade):
    """Quanto a curva se deforma se o PT so tiver os pontos de 'horas'.

    Reconstroi por interpolacao linear entre os keyframes mantidos --
    que e exatamente o que o simulador faz -- e compara com a curva
    original numa grade fina."""
    pontos = [(h, interpolar(curva, h)) for h in horas]
    pior = 0.0
    for hora in grade:
        original = interpolar(curva, hora)
        reconstruido = interpolar(pontos, hora)
        pior = max(pior, abs(original - reconstruido))
    return pior


def simplificar(curvas, horas, tolerancia_pct):
    """Remove keyframes que nao mudam a forma, um a um.

    Por que importa: cada keyframe repete as 56 grandezas do catalogo,
    entao 20 keyframes dao ~1.120 blocos e um arquivo de 800 KB --
    contra 125 KB dos templates da propria Cisco. Arquivo carregado a
    cada inicializacao do simulador merece ser enxuto.

    A tolerancia e percentual sobre a amplitude de CADA grandeza, senao
    um limite em graus seria severo demais para a luz (0-100) ou frouxo
    demais para a temperatura (8 graus de amplitude)."""
    if tolerancia_pct <= 0:
        return horas, {}

    grade = [h / 4.0 for h in range(0, 97)]  # a cada 15 min
    limites = {}
    for grandeza_id, curva in curvas.items():
        valores = [interpolar(curva, h) for h in grade]
        amplitude = max(valores) - min(valores)
        limites[grandeza_id] = max(amplitude * tolerancia_pct / 100.0, 1e-9)

    mantidas = list(horas)
    while True:
        melhor_hora = None
        melhor_erro = None
        for hora in mantidas:
            if hora in (0.0, 24.0):
                continue  # as pontas fecham o ciclo, nunca saem
            candidatas = [h for h in mantidas if h != hora]
            pior_relativo = 0.0
            erros = {}
            for grandeza_id, curva in curvas.items():
                erro = erro_da_reconstrucao(curva, candidatas, grade)
                erros[grandeza_id] = erro
                pior_relativo = max(pior_relativo, erro / limites[grandeza_id])
            if pior_relativo <= 1.0 and (melhor_erro is None or pior_relativo < melhor_erro):
                melhor_erro = pior_relativo
                melhor_hora = hora
        if melhor_hora is None:
            break
        mantidas.remove(melhor_hora)

    # Erro final por grandeza, para o relatorio dizer o preco pago.
    finais = {}
    for grandeza_id, curva in curvas.items():
        finais[grandeza_id] = erro_da_reconstrucao(curva, mantidas, grade)
    return mantidas, finais


def gerar_xml(perfil, escala_simulada, escala_real, tolerancia=0.0):
    """Monta o ambiente inteiro: cabecalho, keyframes e padroes."""
    curvas = perfil["curvas"]
    horas, _erros = simplificar(curvas, horas_do_perfil(curvas), tolerancia)

    partes = ["<ENVIRONMENT>"]
    partes.append("  <TIME_IN_SECONDS>0</TIME_IN_SECONDS>")
    partes.append(
        "  <TIME_MULTIPLIER>{}</TIME_MULTIPLIER>".format(escala_simulada // escala_real)
    )
    partes.append("  <SIM_TIME_SETTING>{}</SIM_TIME_SETTING>".format(escala_simulada))
    partes.append("  <REAL_TIME_SETTING>{}</REAL_TIME_SETTING>".format(escala_real))
    partes.append("  <SIM_TIME_COMBO>60</SIM_TIME_COMBO>")
    partes.append("  <REAL_TIME_COMBO>60</REAL_TIME_COMBO>")
    partes.append("  <NOTES>{}</NOTES>".format(esc(perfil["descricao"])))
    partes.append("  <SHOW_NOTES>false</SHOW_NOTES>")
    partes.append("  <KEYFRAMES>")

    for hora in horas:
        segundos = int(round(hora * 3600))
        if segundos > SEGUNDOS_NO_DIA:
            continue
        partes.append("    <KEYFRAME>")
        partes.append("      <TIME>{}</TIME>".format(segundos))
        partes.append("      <ENVIRONMENT_OPTIONS>")
        for item in CATALOGO:
            curva = curvas.get(item["id"])
            if curva is None:
                partes.append(bloco_grandeza(item, 0, False, 8))
            else:
                partes.append(bloco_grandeza(item, interpolar(curva, hora), True, 8))
        partes.append("      </ENVIRONMENT_OPTIONS>")
        partes.append("    </KEYFRAME>")

    partes.append("  </KEYFRAMES>")

    # Bloco de padroes, fora dos keyframes: e o que o PT usa como
    # estado inicial da janela. Valores da hora zero, todos inativos.
    partes.append("  <ENVIRONMENT_OPTIONS>")
    for item in CATALOGO:
        curva = curvas.get(item["id"])
        valor = interpolar(curva, 0) if curva else 0
        partes.append(bloco_grandeza(item, valor, False, 4))
    partes.append("  </ENVIRONMENT_OPTIONS>")
    partes.append("</ENVIRONMENT>")
    return "\n".join(partes) + "\n"


def conferir_perfil(nome, perfil):
    """Avisa sobre os erros que so aparecem depois, rodando.

    Os tres achados da bancada de 23/09 viraram estas checagens."""
    avisos = []
    curvas = perfil["curvas"]
    conhecidas = set(item["id"] for item in CATALOGO)

    for grandeza_id, curva in curvas.items():
        if grandeza_id not in conhecidas:
            avisos.append(
                "{}: grandeza '{}' nao existe no PT".format(nome, grandeza_id)
            )
            continue

        horas = [h for h, _ in curva]
        if horas != sorted(horas):
            avisos.append("{}/{}: horas fora de ordem".format(nome, grandeza_id))

        # Ciclo aberto: o valor da meia-noite tem que fechar com o das 24h,
        # senao a grandeza da um salto na virada do dia.
        if horas and (horas[0] > 0 or horas[-1] < 24):
            avisos.append(
                "{}/{}: curva nao cobre de 0 a 24 h".format(nome, grandeza_id)
            )
        elif curva[0][1] != curva[-1][1]:
            avisos.append(
                "{}/{}: comeca em {} e termina em {} -- o ciclo nao fecha".format(
                    nome, grandeza_id, curva[0][1], curva[-1][1]
                )
            )

        item = [g for g in CATALOGO if g["id"] == grandeza_id][0]
        for hora, valor in curva:
            if not (item["min"] <= valor <= item["max"]):
                avisos.append(
                    "{}/{}: {} as {}h esta fora de {}..{}".format(
                        nome, grandeza_id, valor, hora, item["min"], item["max"]
                    )
                )

        # Limite de variacao: a temperatura nao sobe mais que 5 C por
        # hora simulada. Curva mais ingreme que isso e mentira -- o PT
        # vai rampear e os horarios previstos nao batem.
        if item["taxa"] != TAXA_PADRAO:
            limite = item["taxa"][1] * 3600
            for i in range(len(curva) - 1):
                h0, v0 = curva[i]
                h1, v1 = curva[i + 1]
                if h1 > h0:
                    taxa = abs(float(v1) - float(v0)) / (h1 - h0)
                    if taxa > limite:
                        avisos.append(
                            "{}/{}: {:.1f}/h entre {}h e {}h excede o limite de {:.1f}/h do PT".format(
                                nome, grandeza_id, taxa, h0, h1, limite
                            )
                        )
    return avisos


def resumir(perfil):
    """Imprime o que a curva vai produzir, sem abrir o simulador."""
    curvas = perfil["curvas"]
    temp = curvas.get("Ambient Temperature")
    if not temp:
        return
    valores = [(h, interpolar(temp, h)) for h in [h / 2.0 for h in range(0, 49)]]
    minima = min(valores, key=lambda p: p[1])
    maxima = max(valores, key=lambda p: p[1])
    print(
        "  temperatura: minima {:.1f} C as {:04.1f}h, maxima {:.1f} C as {:04.1f}h".format(
            minima[1], minima[0], maxima[1], maxima[0]
        )
    )

    # Janela acima de 30 C: e quando a climatizacao da Sala e do Quarto
    # deve ligar. Saber a hora prevista evita esperar por nada.
    acima = [h for h, v in valores if v >= 30.0]
    if acima:
        print(
            "  acima de 30 C (liga o AC): das {:04.1f}h as {:04.1f}h".format(
                acima[0], acima[-1]
            )
        )
    else:
        print("  nunca chega a 30 C -- a climatizacao nao vai ligar sozinha")


def main():
    parser = argparse.ArgumentParser(
        description="Gera o XML de ambiente do Packet Tracer a partir de um perfil climatico."
    )
    parser.add_argument(
        "--perfil", default="sao-luis-seco", help="nome do perfil (ver --listar)"
    )
    parser.add_argument(
        "--saida", help="arquivo de saida (padrao: ambiente_<perfil>.xml)"
    )
    parser.add_argument(
        "--escala",
        type=int,
        default=30,
        help="minutos simulados por minuto real (padrao: 30)",
    )
    parser.add_argument(
        "--listar", action="store_true", help="lista os perfis disponiveis"
    )
    parser.add_argument(
        "--tolerancia",
        type=float,
        default=0.0,
        help="simplifica os keyframes aceitando erro de ate N%% da amplitude de cada "
        "grandeza (0 = nao simplifica; 2 costuma cortar metade do arquivo)",
    )
    args = parser.parse_args()

    if args.listar:
        print("Perfis disponiveis:")
        for nome in sorted(PERFIS):
            print("  {:20s} {}".format(nome, PERFIS[nome]["descricao"]))
        return 0

    if args.perfil not in PERFIS:
        print("Perfil '{}' nao existe. Use --listar.".format(args.perfil))
        return 1

    perfil = PERFIS[args.perfil]
    avisos = conferir_perfil(args.perfil, perfil)
    if avisos:
        print("Problemas no perfil:")
        for aviso in avisos:
            print("  - {}".format(aviso))
        return 1

    saida = args.saida or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ambiente_{}.xml".format(args.perfil),
    )
    xml = gerar_xml(perfil, args.escala, 1, args.tolerancia)
    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write(xml)

    originais = horas_do_perfil(perfil["curvas"])
    horas, erros = simplificar(perfil["curvas"], originais, args.tolerancia)
    ativas = len(perfil["curvas"])
    print("Ambiente gerado: {} ({:.0f} KB)".format(
        saida, os.path.getsize(saida) / 1024.0))
    print("  perfil: {} -- {}".format(args.perfil, perfil["descricao"]))
    print(
        "  {} keyframes, {} grandezas ativas de {} do catalogo".format(
            len(horas), ativas, len(CATALOGO)
        )
    )
    if args.tolerancia > 0 and len(horas) < len(originais):
        print(
            "  simplificado: {} -> {} keyframes (tolerancia de {}% da amplitude)".format(
                len(originais), len(horas), args.tolerancia
            )
        )
        for grandeza_id in sorted(erros):
            if erros[grandeza_id] > 0.01:
                print("    {:22s} erro maximo {:.2f}".format(grandeza_id, erros[grandeza_id]))
    print(
        "  escala: 1 min real = {} min simulados (um dia em {:.0f} min reais)".format(
            args.escala, 1440.0 / args.escala
        )
    )
    resumir(perfil)
    return 0


if __name__ == "__main__":
    sys.exit(main())
