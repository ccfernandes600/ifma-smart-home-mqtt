#!/usr/bin/env python3
"""Renderiza o painel web da Central fora do Packet Tracer.

Por que existe
--------------
O painel é montado por `pagina_painel()`, dentro do `broker_central.py`, que só
roda como MicroPython no simulador. Conferir o HTML lá dentro custa uma bancada
inteira: abrir o PT, montar a topologia, subir as zonas e abrir o navegador do PC.

Este script dubla os pacotes do Packet Tracer (`gpio`, `time`, `tcp`, `json`,
`http`), carrega o broker como um módulo comum, preenche o estado com valores
plausíveis e grava o HTML resultante. Serve para ver layout, rótulo, unidade e
quebra de linha antes de ir para a bancada — não substitui o teste no simulador,
que é onde a leitura dos sensores e a rede de fato acontecem.

    python3 verificacao/previa_painel.py            # grava previa_painel.html
    python3 verificacao/previa_painel.py --alerta   # cenário de vazamento de gás
"""

import json as _json
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "verificacao", "previa_painel.html")

# Valores de exemplo — um de cada grandeza que as zonas publicam hoje.
ESTADO_EXEMPLO = {
    "casa/sala/temp": 24.6,
    "casa/sala/umidade": 58,
    "casa/sala/luz": 180,
    "casa/sala/movimento": 1,
    "casa/quarto/temp": 22.1,
    "casa/quarto/umidade": 61,
    "casa/quarto/luz": 40,
    "casa/quarto/movimento": 0,
    "casa/cozinha/temp": 27.3,
    "casa/cozinha/umidade": 64,
    "casa/cozinha/fumaca": 2.5,
    "casa/cozinha/co": 1.0,
    "casa/garagem/co": 3.2,
    "casa/garagem/co2": 4.8,
    "casa/garagem/movimento": 0,
    "casa/jardim/agua": 30,
    "casa/jardim/vento": 12,
    "casa/jardim/pressao": 101,
    "casa/jardim/luz": 250,
    "casa/perimetro/movimento": 0,
    "casa/perimetro/campainha": 0,
    "casa/perimetro/rfid": 1005,
}


def dublar_pacotes():
    """Cria módulos falsos com a mesma superfície que o broker usa."""

    gpio = types.ModuleType("gpio")
    gpio.HIGH, gpio.LOW, gpio.IN, gpio.OUT = 1, 0, "in", "out"
    for nome in ("pinMode", "digitalWrite", "customWrite", "add_event_detect"):
        setattr(gpio, nome, lambda *a, **k: None)
    gpio.digitalRead = lambda *a, **k: 0

    tempo = types.ModuleType("time")
    tempo.ctime = lambda *a: "previa"
    tempo.sleep = lambda *a: None
    tempo.uptime = lambda: 0
    tempo.delay = lambda *a: None

    tcp = types.ModuleType("tcp")

    class TCPServer:  # noqa: N801 - nome vem da API do Packet Tracer
        def onNewClient(self, *a):
            pass

        def listen(self, *a):
            pass

    tcp.TCPServer = TCPServer

    js = types.ModuleType("json")
    js.dumps, js.loads = _json.dumps, _json.loads

    http = types.ModuleType("http")

    class _HTTPServer:
        @staticmethod
        def route(*a):
            pass

        @staticmethod
        def start(*a):
            return True

    http.HTTPServer = _HTTPServer

    for modulo in (gpio, tempo, tcp, js, http):
        sys.modules[modulo.__name__] = modulo


def carregar_broker():
    """Executa o broker_central.py como módulo, sem disparar o main()."""
    caminho = os.path.join(RAIZ, "src", "broker_central.py")
    modulo = types.ModuleType("broker_central")
    modulo.__file__ = caminho
    with open(caminho, encoding="utf-8") as arquivo:
        exec(compile(arquivo.read(), caminho, "exec"), modulo.__dict__)
    return modulo


def main():
    alerta = "--alerta" in sys.argv
    dublar_pacotes()
    broker = carregar_broker()

    broker.estado.update(ESTADO_EXEMPLO)
    broker.clientes.extend([object()] * 6)  # seis zonas conectadas
    if alerta:
        broker.estado["casa/cozinha/fumaca"] = 41.0  # acima do LIMIAR_GAS

    html = broker.pagina_painel()
    with open(SAIDA, "w", encoding="utf-8") as arquivo:
        arquivo.write(html)

    print("Painel gerado: {}".format(SAIDA))
    print(
        "  {} caracteres · {} zonas · cenário: {}".format(
            len(html),
            len(broker.linhas_por_zona()),
            "alerta de gás" if alerta else "normal",
        )
    )


if __name__ == "__main__":
    main()
