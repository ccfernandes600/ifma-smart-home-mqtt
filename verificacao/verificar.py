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
outro agente significa reler todo o MicroPython à mão.

A última seção roda `testes_logica.py`, que exercita a lógica com dublês do PT.
Foi medido com defeitos plantados em 03/11/2026: ao acrescentar regra, plante o
defeito numa cópia e confira que ela pega.

    python3 verificacao/verificar.py

Sai com 0 se tudo passa, 1 se algo quebrou. Cada regra abaixo está registrada em
CLAUDE.md ou em docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md — o verificador não inventa
política, só torna executável a que já existe.
"""

import ast
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAIZ, "src")

# Pacotes que existem no SBC-PT/MCU-PT do Packet Tracer. Fora desta lista, o
# script simplesmente não roda no simulador — e o erro só aparece na hora da
# demonstração, com a turma olhando.
# Espelha a tabela §2.1 de docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md, que é a
# fonte de verdade da API. Esta lista já divergiu dela uma vez (23/09): aceitava
# math/random/serial/i2c/spi/sensors/actuators, que não estão documentados, e
# rejeitava email/networking/ioeclient/usb/realhttp/realtcp/realudp, que existem.
# Nos dois sentidos o erro é caro: o primeiro deixa passar import que só quebra
# dentro do simulador; o segundo barra código correto.
# Pacote novo entra PRIMEIRO no levantamento, depois aqui.
PACOTES_PT = {
    "gpio",
    "time",
    "networking",
    "tcp",
    "udp",
    "http",
    "realhttp",
    "realtcp",
    "realudp",
    "email",
    "json",
    "ioeclient",
    "os",
    "file",
    "usb",
    "physical",
    "environment",
}

# Orçamento de portas por controlador (docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md).
# A MCU tem 6 portas usáveis (D0-D5); as analógicas dedicadas A0-A3 têm o bug
# herdado do V3 e são proibidas.
LIMITE_PORTAS = {"SBC": 10, "MCU": 6}

# A API certa de cada dispositivo, pelo nome da constante da porta. Fan com
# digitalWrite não dá erro nenhum: o Fan simplesmente não gira. Vem da doc de cada
# dispositivo (docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md §1.2).
SO_CUSTOM = {
    "FAN", "PORTA", "JANELA", "SIRENE", "CAMERA", "LCD_MESTRE",
    "IRRIGACAO", "DRENO", "LUMINARIA",  # doc de cada device, lida em 03/11/2026
}
SO_DIGITAL = {"AC", "ALARME", "SPEAKER", "SPRINKLER", "UMIDIFICADOR"}
SO_ANALOG = {"LED"}  # Smart LED: "use analogWrite to adjust the device brightness"
ESCRITAS = {"digitalWrite", "analogWrite", "customWrite"}

# De que pacote do PT vem cada nome. Import esquecido só quebra dentro do simulador.
API_DOS_PACOTES = {
    "gpio": {
        "pinMode", "digitalRead", "digitalWrite", "analogRead", "analogWrite",
        "customRead", "customWrite", "add_event_detect", "HIGH", "LOW", "IN", "OUT",
    },
    "time": {"sleep", "uptime", "ctime", "delay"},
    "tcp": {"TCPClient", "TCPServer"},
    "json": {"dumps", "loads"},
    "http": {"HTTPServer"},
    "realhttp": {"RealHTTPClient"},
    "environment": {"Environment"},
}

LIMITE_LCD = 14  # o LCD do PT corta o excedente sem avisar (bancada de 23/09)
IP_BROKER = "192.168.1.100"

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


def nos_da_automacao():
    """Broker, zonas e RFID Reader; ficam de fora os diagnósticos e os instrumentos."""
    return [
        c for c in arquivos
        if re.match(r"(broker_central|zona_\w+|thing_rfid_reader)\.py$", os.path.basename(c))
    ]


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
        linhas = fonte(caminho).splitlines()
        for i, linha in enumerate(linhas, 1):
            if "customRead(" not in linha or ".strip()" in linha:
                continue
            # Também vale `x = customRead(p)` seguido de `x = x.strip()`.
            m = re.match(r"\s*(\w+)\s*=", linha)
            seguinte = linhas[i] if i < len(linhas) else ""
            if not (m and m.group(1) + ".strip()" in seguinte):
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


def _mcu_so_d0_d5():
    # A contagem de portas não basta: quatro portas com uma em D7 cabem no
    # orçamento e não existem na placa.
    ruins = []
    for caminho in arquivos:
        texto = fonte(caminho)
        if controlador(texto) != "MCU":
            continue
        for nome, valor, _ in portas_declaradas(texto):
            if valor > 5:
                ruins.append(f"{os.path.basename(caminho)} {nome}=D{valor}")
    if ruins:
        raise AssertionError("MCU só tem D0–D5: " + ", ".join(ruins))
    return None


def _api_do_dispositivo():
    ruins = []
    for caminho in nos_da_automacao():
        for no in ast.walk(ast.parse(fonte(caminho))):
            if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Name)):
                continue
            if no.func.id not in ESCRITAS or not no.args:
                continue
            alvo = no.args[0]
            nome = os.path.basename(caminho)
            if isinstance(alvo, ast.Constant):
                ruins.append(f"{nome}:{no.lineno} pino literal em {no.func.id}")
            elif isinstance(alvo, ast.Name):
                if alvo.id in SO_CUSTOM and no.func.id != "customWrite":
                    ruins.append(f"{nome}:{no.lineno} {alvo.id} exige customWrite")
                if alvo.id in SO_DIGITAL and no.func.id != "digitalWrite":
                    ruins.append(f"{nome}:{no.lineno} {alvo.id} exige digitalWrite")
                if alvo.id in SO_ANALOG and no.func.id != "analogWrite":
                    ruins.append(f"{nome}:{no.lineno} {alvo.id} exige analogWrite")
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


def _ao_receber():
    # O PT chama onReceive com UM argumento. Com dois, o erro só aparece quando
    # chega a primeira mensagem; sem o registro, a zona fica surda em silêncio.
    ruins = []
    for caminho in nos_da_automacao():
        texto = fonte(caminho)
        for no in ast.parse(texto).body:
            if isinstance(no, ast.FunctionDef) and no.name == "ao_receber":
                if len(no.args.args) != 1:
                    ruins.append(f"{os.path.basename(caminho)}: ao_receber precisa de 1 argumento")
                if ".onReceive(ao_receber)" not in texto:
                    ruins.append(f"{os.path.basename(caminho)}: ao_receber não foi registrado")
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


def _nada_orfao():
    # Função ou constante de porta que ninguém usa costuma ser fiação esquecida,
    # como um add_event_detect removido: o sensor para de reagir sem erro nenhum.
    ruins = []
    for caminho in nos_da_automacao():
        arvore = ast.parse(fonte(caminho))
        usados = {n.id for n in ast.walk(arvore) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        usados |= {n.attr for n in ast.walk(arvore) if isinstance(n, ast.Attribute)}
        for no in arvore.body:
            nomes = []
            if isinstance(no, ast.FunctionDef):
                nomes = [no.name]
            elif (
                isinstance(no, ast.Assign)
                and isinstance(no.value, ast.Constant)
                and type(no.value.value) is int
            ):
                nomes = [a.id for a in no.targets if isinstance(a, ast.Name) and a.id.isupper()]
            ruins += [f"{os.path.basename(caminho)}: {n}" for n in nomes if n not in usados]
    if ruins:
        raise AssertionError("definido e nunca usado: " + ", ".join(ruins))
    return None


def _imports_cobrem_o_uso():
    ruins = []
    for caminho in arquivos:
        arvore = ast.parse(fonte(caminho))
        com_estrela, explicitos = set(), set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom):
                for apelido in no.names:
                    if apelido.name == "*":
                        com_estrela.add(no.module)
                    else:
                        explicitos.add(apelido.name)
        usados = {n.id for n in ast.walk(arvore) if isinstance(n, ast.Name)}
        for pacote, nomes in API_DOS_PACOTES.items():
            if pacote in com_estrela:
                continue
            for nome in sorted((nomes & usados) - explicitos):
                ruins.append(f"{os.path.basename(caminho)}: {nome} sem import de {pacote}")
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


def _ponto_de_entrada():
    # Script sem a chamada final roda, não imprime erro e não faz nada.
    ruins = []
    for caminho in arquivos:
        texto = fonte(caminho)
        nome = os.path.basename(caminho)
        if '__name__ == "__main__"' not in texto:
            ruins.append(f"{nome}: sem bloco __main__")
        for no in ast.parse(texto).body:
            if isinstance(no, ast.FunctionDef) and no.name == "main":
                if all(isinstance(c, ast.Pass) for c in no.body):
                    ruins.append(f"{nome}: main() vazio")
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


def _textos_do_lcd():
    # Foi assim que "Movimento na garagem" virou "Movimento na g", escondendo
    # justamente onde olhar. Marcador {} conta como 4 caracteres (ID do cartão).
    arvore = ast.parse(fonte(os.path.join(SRC, "broker_central.py")))

    def texto(no):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            return no.value
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr == "format"
            and isinstance(no.func.value, ast.Constant)
        ):
            return no.func.value.value.replace("{}", "0000")
        return None

    achados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            if no.func.id in ("mostrar", "mostrar_aviso_rfid"):
                achados += no.args[:2]
        if isinstance(no, ast.Assign) and any(isinstance(a, ast.Name) and a.id == "onde" for a in no.targets):
            achados.append(no.value)
        if isinstance(no, ast.FunctionDef) and no.name == "situacao_da_casa":
            for r_ in ast.walk(no):
                if isinstance(r_, ast.Return) and isinstance(r_.value, ast.Tuple):
                    achados += r_.value.elts[:2]
    textos = [t for t in map(texto, achados) if t is not None]
    longos = [t for t in textos if len(t) > LIMITE_LCD]
    if longos:
        raise AssertionError(f"mais de {LIMITE_LCD} caracteres: " + "; ".join(longos))
    return f"{len(textos)} textos conferidos"


teste("customRead() sempre com .strip()", _customread_strip)
teste("MCU não usa as portas A0–A3", _mcu_sem_analogicas)
teste("MCU só usa D0–D5", _mcu_so_d0_d5)
teste("cada atuador usa a API certa, sem pino literal", _api_do_dispositivo)
teste("ao_receber tem 1 argumento e está registrado", _ao_receber)
teste("nenhuma função ou porta órfã", _nada_orfao)
teste("todo nome da API do PT tem o import correspondente", _imports_cobrem_o_uso)
teste("todo script tem ponto de entrada", _ponto_de_entrada)
teste("textos do LCD cabem em 14 caracteres", _textos_do_lcd)

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
        portas.update(re.findall(r"(?:BROKER_PORT|PORTA_BROKER)\s*=\s*(\d+)", fonte(caminho)))
    if portas and portas != {"1883"}:
        raise AssertionError(f"portas de broker divergentes: {sorted(portas)}")
    return "1883 em todos os scripts" if portas else None


def _ip_do_broker():
    # IP errado também não dá erro: a zona segue automatizando, só que muda.
    ruins = []
    for caminho in arquivos:
        for ip in re.findall(r'BROKER_IP\s*=\s*"([^"]+)"', fonte(caminho)):
            if ip != IP_BROKER:
                ruins.append(f"{os.path.basename(caminho)}: {ip}")
    if ruins:
        raise AssertionError(f"o broker é {IP_BROKER}: " + "; ".join(ruins))
    return None


def _zona_bate_com_o_arquivo():
    # O nome da zona vira tópico: "Jardim" e "jardim" são tópicos diferentes.
    ruins = []
    for caminho in nos_da_automacao():
        nome = os.path.basename(caminho)
        m = re.search(r'^ZONA\s*=\s*"([^"]+)"', fonte(caminho), re.M)
        if not m:
            continue
        esperado = "perimetro" if nome.startswith("thing_rfid") else nome[5:-3]
        if m.group(1) != esperado:
            ruins.append(f"{nome}: ZONA={m.group(1)!r}, esperado {esperado!r}")
    if ruins:
        raise AssertionError("; ".join(ruins))
    return None


teste("tópicos seguem casa/<zona>/<grandeza>", _topicos)
teste("todos apontam para a mesma porta de broker", _porta_broker)
teste("todos apontam para o IP do broker", _ip_do_broker)
teste("ZONA bate com o nome do arquivo", _zona_bate_com_o_arquivo)

def _topicos_das_zonas():
    """Devolve (publicados, aceitos), lidos do código de cada nó."""
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
    return publicados, aceitos


def _pontas_soltas():
    # O broker e as zonas conversam por tópico, e tópico errado não dá erro:
    # a mensagem simplesmente não chega. Duas pontas soltas são defeito de
    # verdade, e as duas só aparecem lendo os dois lados juntos.
    publicados, aceitos = _topicos_das_zonas()

    broker = fonte(os.path.join(SRC, "broker_central.py"))
    lidos = set(re.findall(r'estado\.get\(\s*["\'](casa/[^"\']+)["\']', broker))
    # O RFID não passa por estado.get(): é comparado direto em ao_receber().
    lidos |= set(re.findall(r'topico\s*==\s*["\'](casa/[^"\']+)["\']', broker))
    # Qualquer literal de comando, para pegar também o que passa por variável.
    enviados = set(re.findall(r'["\'](casa/[a-z0-9_]+/cmd/[a-z0-9_]+)["\']', broker))

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
    return "{} tópicos publicados, {} lidos pelo broker, {} só para o painel".format(
        len(publicados), len(lidos & publicados), sobrando
    )


def _arquitetura_bate():
    # A tabela de tópicos de docs/ARQUITETURA.md é o contrato do protocolo, e já
    # divergiu do código sem ninguém notar.
    publicados, aceitos = _topicos_das_zonas()
    documentados, comandos = set(), set()
    with open(os.path.join(RAIZ, "docs", "ARQUITETURA.md"), encoding="utf-8") as f:
        linhas = f.read().splitlines()
    nomes = {
        "Perímetro": "perimetro", "Sala": "sala", "Cozinha": "cozinha",
        "Quarto": "quarto", "Jardim": "jardim", "Garagem": "garagem",
    }
    for linha in linhas:
        m = re.match(r"- (\w+): (.*) · cmd: (.*)$", linha)
        if not (m and m.group(1) in nomes):
            continue
        zona = nomes[m.group(1)]
        documentados |= {f"casa/{zona}/{g}" for g in re.findall(r"`(\w+)`", m.group(2))}
        comandos |= {f"casa/{zona}/cmd/{c}" for c in re.findall(r"`(\w+)`", m.group(3))}
    # cmd/modo é broadcast (casa/todas/...), e a tabela lista só os direcionados.
    aceitos = {c for c in aceitos if not c.endswith("/cmd/modo")}
    diferencas = sorted((documentados ^ publicados) | (comandos ^ aceitos))
    if diferencas:
        raise AssertionError("divergem entre código e ARQUITETURA.md: " + ", ".join(diferencas))
    return f"{len(documentados)} tópicos e {len(comandos)} comandos"


teste("broker e zonas falam os mesmos tópicos", _pontas_soltas)
teste("a tabela de tópicos da ARQUITETURA bate com o código", _arquitetura_bate)


# --------------------------------------------------------------------------- #
print("\nReferência V3 (não editar)")


def _v3_intacto():
    v3 = os.path.join(os.path.dirname(RAIZ), "ifma-smart-home-packet-tracer")
    if not os.path.isdir(v3):
        return "V3 não está neste computador, pulado"
    if not os.path.isdir(os.path.join(v3, ".git")):
        return "V3 sem git, não dá para conferir"
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
print("\nComportamento (com dublês do Packet Tracer)")


def _logica():
    # Dublê prova a lógica do script, não o comportamento do simulador.
    p = subprocess.run(
        [sys.executable, os.path.join(RAIZ, "verificacao", "testes_logica.py")],
        capture_output=True,
        text=True,
    )
    ruins = [x.strip() for x in p.stdout.splitlines() if x.startswith("  FALHA")]
    if p.returncode != 0:
        raise AssertionError("; ".join(ruins) or p.stderr.strip()[-300:])
    return f"{p.stdout.count('  ok ')} testes"


teste("os defeitos da revisão de 03/11 não voltaram", _logica)

# --------------------------------------------------------------------------- #
print()
if falhas:
    print(f"FALHOU: {len(falhas)} verificação(ões) — " + ", ".join(falhas))
    sys.exit(1)
print("TUDO CERTO — o projeto está íntegro.")
