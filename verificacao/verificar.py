#!/usr/bin/env python3
"""
Verificador do projeto — o contrato da força-tarefa de IAs.

Por que existe
--------------
Este projeto não tem build, lint nem teste: o Python roda como MicroPython
DENTRO do Packet Tracer, não no host. Não dá para executar nada aqui.

Mas ele tem regras normativas fortes — restrição pedagógica do IFMA, orçamento
de portas por controlador, gotchas do simulador — e essas regras são
verificáveis por leitura estática. Sem esse verificador, revisar o trabalho de
outro agente significa reler 1.900 linhas de MicroPython à mão.

    python3 verificacao/verificar.py

Sai com 0 se tudo passa, 1 se algo quebrou. Cada regra abaixo está registrada em
CLAUDE.md ou em docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md — o verificador não inventa
política, só torna executável a que já existe.
"""

import ast
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAIZ, "src")

# Pacotes que existem no SBC-PT/MCU-PT do Packet Tracer. Fora desta lista, o
# script simplesmente não roda no simulador — e o erro só aparece na hora da
# demonstração, com a turma olhando.
PACOTES_PT = {
    "gpio",
    "time",
    "json",
    "tcp",
    "udp",
    "http",
    "environment",
    "physical",
    "sensors",
    "actuators",
    "serial",
    "i2c",
    "spi",
    "math",
    "random",
    "os",
}

# Orçamento de portas por controlador (docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md).
# A MCU tem 6 portas usáveis (D0-D5); as analógicas dedicadas A0-A3 têm o bug
# herdado do V3 e são proibidas.
LIMITE_PORTAS = {"SBC": 10, "MCU": 6}

falhas = []


def teste(nome, fn):
    try:
        detalhe = fn()
        print(f"  ok    {nome}" + (f" — {detalhe}" if detalhe else ""))
    except Exception as e:  # noqa: BLE001
        print(f"  FALHA {nome} — {e}")
        falhas.append(nome)


def scripts():
    """Os scripts de zona/broker — o que roda dentro do simulador."""
    if not os.path.isdir(SRC):
        return []
    return sorted(os.path.join(SRC, f) for f in os.listdir(SRC) if f.endswith(".py"))


def fonte(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def controlador(texto):
    """SBC ou MCU, lido do cabeçalho do script ('... no MCU (192.168...)')."""
    cabeca = "\n".join(texto.splitlines()[:25]).upper()
    if re.search(r"\bNO MCU\b|\bMCU-PT\b|\(MCU\b", cabeca):
        return "MCU"
    return "SBC"


def portas_declaradas(texto):
    """Constantes de porta, no formato `NOME = n  # D0: descrição`.

    Devolve [(nome, valor, rótulo)] — o rótulo é o 'D0'/'A2' do comentário.
    É o formato que todos os scripts do projeto já usam.
    """
    achadas = []
    for linha in texto.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*#\s*([DA]\d)\b", linha)
        if m:
            achadas.append((m.group(1), int(m.group(2)), m.group(3)))
    return achadas


print("Verificando o Smart Home MQTT (V4)\n")
arquivos = scripts()
print(f"Scripts em src/: {len(arquivos)}\n")

# --------------------------------------------------------------------------- #
print("Sintaxe e restrições pedagógicas")


def _sintaxe():
    for caminho in arquivos:
        try:
            ast.parse(fonte(caminho), filename=caminho)
        except SyntaxError as e:
            raise AssertionError(f"{os.path.basename(caminho)}:{e.lineno} — {e.msg}")
    return f"{len(arquivos)} arquivos"


def _sem_classe():
    # Restrição pedagógica do IFMA: material de aluno sem `class`, lógica em def.
    encontrados = []
    for caminho in arquivos:
        arvore = ast.parse(fonte(caminho))
        for no in ast.walk(arvore):
            if isinstance(no, ast.ClassDef):
                encontrados.append(
                    f"{os.path.basename(caminho)}:{no.lineno} class {no.name}"
                )
    if encontrados:
        raise AssertionError("; ".join(encontrados))
    return None


def _imports_do_pt():
    # Import fora dos pacotes do simulador não quebra aqui — quebra na aula.
    ruins = []
    for caminho in arquivos:
        arvore = ast.parse(fonte(caminho))
        for no in ast.walk(arvore):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name.split(".")[0] for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module:
                nomes = [no.module.split(".")[0]]
            for n in nomes:
                if n not in PACOTES_PT:
                    ruins.append(f"{os.path.basename(caminho)}:{no.lineno} import {n}")
    if ruins:
        raise AssertionError("fora do Packet Tracer: " + "; ".join(ruins))
    return f"{len(PACOTES_PT)} pacotes permitidos"


def _logica_em_def():
    # Todo script deve ter a lógica em funções; no topo só constantes, imports
    # e a chamada final que arranca o programa.
    magros = []
    for caminho in arquivos:
        arvore = ast.parse(fonte(caminho))
        defs = sum(1 for n in arvore.body if isinstance(n, ast.FunctionDef))
        if defs == 0:
            magros.append(os.path.basename(caminho))
    if magros:
        raise AssertionError("sem nenhuma função def: " + ", ".join(magros))
    return None


teste("todos os scripts têm sintaxe válida", _sintaxe)
teste("nenhum uso de class", _sem_classe)
teste("só importa pacotes que existem no Packet Tracer", _imports_do_pt)
teste("lógica organizada em funções", _logica_em_def)

# --------------------------------------------------------------------------- #
print("\nGotchas do simulador (herdados do V3)")


def _customread_strip():
    # customRead() devolve string com lixo. Comparar sem .strip() funciona no
    # teste e falha na demonstração — foi o gotcha nº 1 do V3.
    ruins = []
    for caminho in arquivos:
        for i, linha in enumerate(fonte(caminho).splitlines(), 1):
            if "customRead(" in linha and ".strip()" not in linha:
                ruins.append(f"{os.path.basename(caminho)}:{i}")
    if ruins:
        raise AssertionError("customRead sem .strip(): " + ", ".join(ruins))
    return None


def _mcu_sem_analogicas():
    # As portas A0-A3 da MCU-PT têm o bug conhecido do V3. D0-D5 fazem
    # analogRead/Write normalmente — usar essas.
    ruins = []
    for caminho in arquivos:
        texto = fonte(caminho)
        if controlador(texto) != "MCU":
            continue
        for nome, _, rotulo in portas_declaradas(texto):
            if rotulo.startswith("A"):
                ruins.append(f"{os.path.basename(caminho)} {nome}={rotulo}")
    if ruins:
        raise AssertionError("MCU usando porta analógica dedicada: " + ", ".join(ruins))
    return None


teste("customRead() sempre com .strip()", _customread_strip)
teste("MCU não usa as portas A0–A3", _mcu_sem_analogicas)

# --------------------------------------------------------------------------- #
print("\nOrçamento e coerência de portas")


def _orcamento():
    estouros, resumo = [], []
    for caminho in arquivos:
        texto = fonte(caminho)
        portas = portas_declaradas(texto)
        if not portas:
            continue
        ctrl = controlador(texto)
        limite = LIMITE_PORTAS[ctrl]
        usadas = {v for _, v, _ in portas}
        resumo.append(f"{os.path.basename(caminho)[:-3]} {ctrl} {len(usadas)}/{limite}")
        if len(usadas) > limite:
            estouros.append(
                f"{os.path.basename(caminho)}: {len(usadas)} portas em {ctrl} (máx {limite})"
            )
    if estouros:
        raise AssertionError("; ".join(estouros))
    return " · ".join(resumo) if resumo else None


def _sem_porta_repetida():
    # Dois dispositivos no mesmo pino é erro de fiação: passa na leitura do
    # código e só aparece quando o atuador errado dispara no simulador.
    ruins = []
    for caminho in arquivos:
        vistos = {}
        for nome, valor, rotulo in portas_declaradas(fonte(caminho)):
            if valor in vistos:
                ruins.append(
                    f"{os.path.basename(caminho)}: {nome} e {vistos[valor]} na porta {valor}"
                )
            vistos[valor] = nome
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


def _rotulo_bate_com_valor():
    # `FAN = 4  # D5` é uma constante que mente: o comentário diz um pino e o
    # código usa outro. Quem for religar o circuito segue o comentário.
    ruins = []
    for caminho in arquivos:
        for nome, valor, rotulo in portas_declaradas(fonte(caminho)):
            if rotulo.startswith("D") and int(rotulo[1:]) != valor:
                ruins.append(
                    f"{os.path.basename(caminho)}: {nome}={valor} mas comentário diz {rotulo}"
                )
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


teste("nenhuma zona estoura o orçamento de portas", _orcamento)
teste("nenhuma porta usada por dois dispositivos", _sem_porta_repetida)
teste("o comentário da porta bate com o valor", _rotulo_bate_com_valor)

# --------------------------------------------------------------------------- #
print("\nProtocolo MQTT")


def _topicos():
    # Padrão fechado em docs/ARQUITETURA.md: casa/<zona>/<grandeza> e
    # casa/<zona>/cmd/<atuador>. Tópico fora do padrão não é assinado por ninguém.
    ruins = set()
    # Aceita dígitos (casa/garagem/co2), o placeholder de format() usado nos
    # scripts (casa/{}/{}) e o <zona> das docs. O que NÃO pode passar é
    # maiúscula, espaço ou um nível a mais de profundidade.
    padrao = re.compile(r"^casa/[a-z0-9_<>{}]+/(cmd/)?[a-z0-9_<>{}]+$")
    for caminho in arquivos:
        for topico in re.findall(r'"(casa/[^"]+)"', fonte(caminho)):
            if not padrao.match(topico):
                ruins.add(f"{os.path.basename(caminho)}: {topico}")
    if ruins:
        raise AssertionError(
            "fora do padrão casa/<zona>/...: " + "; ".join(sorted(ruins))
        )
    return None


def _porta_broker():
    # O broker escuta em 1883 (docs/ARQUITETURA.md). Cliente apontando para
    # outra porta fica mudo sem erro nenhum.
    portas = set()
    for caminho in arquivos:
        portas.update(re.findall(r"BROKER_PORT\s*=\s*(\d+)", fonte(caminho)))
    if portas and portas != {"1883"}:
        raise AssertionError(f"portas de broker divergentes: {sorted(portas)}")
    return "1883 em todos os scripts" if portas else None


teste("tópicos seguem casa/<zona>/<grandeza>", _topicos)
teste("todos apontam para a mesma porta de broker", _porta_broker)

def _pontas_soltas():
    # O broker e as zonas conversam por tópico, e tópico errado não dá erro:
    # a mensagem simplesmente não chega. Duas pontas soltas são defeito de
    # verdade, e as duas só aparecem lendo os dois lados juntos.
    publicados, aceitos = set(), set()
    for caminho in arquivos:
        texto = fonte(caminho)
        m = re.search(r'^ZONA\s*=\s*["\']([^"\']+)', texto, re.M)
        if not m:
            continue
        zona = m.group(1)
        for grandeza in re.findall(r'publicar(?:_se_mudou)?\(\s*["\']([^"\']+)["\']', texto):
            publicados.add("casa/{}/{}".format(zona, grandeza))
        corpo = texto.split("def ao_receber", 1)[-1].split("\ndef ", 1)[0]
        for atuador in re.findall(r'endswith\(\s*["\']/cmd/([a-z_]+)["\']', corpo):
            aceitos.add("casa/{}/cmd/{}".format(zona, atuador))

    broker = fonte(os.path.join(SRC, "broker_central.py"))
    lidos = set(re.findall(r'estado\.get\(\s*["\'](casa/[^"\']+)["\']', broker))
    enviados = set(re.findall(r'enviar_comando\([^,]+,\s*["\'](casa/[^"\']+)["\']', broker))

    problemas = []
    orfaos = sorted(lidos - publicados)
    if orfaos:
        problemas.append("o broker lê tópico que ninguém publica: " + ", ".join(orfaos))
    mudos = sorted(t for t in enviados - aceitos if not t.startswith("casa/todas/"))
    if mudos:
        problemas.append("o broker manda comando que a zona não trata: " + ", ".join(mudos))
    if problemas:
        raise AssertionError(" | ".join(problemas))
    sobrando = len(publicados - lidos)
    return "{} tópicos publicados, {} lidos pelo broker, {} só para o dashboard".format(
        len(publicados), len(lidos & publicados), sobrando
    )


teste("broker e zonas falam os mesmos tópicos", _pontas_soltas)


# --------------------------------------------------------------------------- #
print("\nReferência V3 (não editar)")


def _v3_intacto():
    v3 = os.path.join(os.path.dirname(RAIZ), "ifma-smart-home-packet-tracer")
    if not os.path.isdir(v3):
        return "V3 não está neste computador, pulado"
    if not os.path.isdir(os.path.join(v3, ".git")):
        return "V3 sem git, não dá para conferir"
    import subprocess

    p = subprocess.run(
        ["git", "status", "--short"], cwd=v3, capture_output=True, text=True
    )
    sujos = [
        linha
        for linha in p.stdout.splitlines()
        if not re.search(r"AGENTS\.md|GEMINI\.md|desktop\.ini", linha)
    ]
    if sujos:
        raise AssertionError(
            "o V3 é só consulta e foi modificado: "
            + "; ".join(s.strip() for s in sujos[:4])
        )
    return "intacto"


teste("o projeto V3 continua sem edições", _v3_intacto)

# --------------------------------------------------------------------------- #
print()
if falhas:
    print(f"FALHOU: {len(falhas)} verificação(ões) — " + ", ".join(falhas))
    sys.exit(1)
print("TUDO CERTO — o projeto está íntegro.")
