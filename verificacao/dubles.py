"""Dublês dos pacotes do Packet Tracer, para testar a lógica dos scripts no host.

Um dublê prova a lógica do script, não o comportamento do simulador: confirma
que o `if` faz o que deve, mas não diz se o PT junta mensagens TCP nem se preserva
a saída de um pino entre execuções. Isso continua sendo assunto de bancada.
"""

import json as _json
import os
import sys
import types

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


def carregar(nome, ambiente=None):
    """Carrega src/<nome>.py sem disparar o main(). Devolve um dicionário com o
    módulo e os controles do teste: pinos, relógio, mensagens enviadas e rede."""
    saidas, entradas = {}, {}
    relogio = {"t": 0.0}
    enviados = []
    rede = {"conectado": True, "tentativas": 0}
    env = dict(ambiente or {})

    gpio = types.ModuleType("gpio")
    gpio.HIGH, gpio.LOW, gpio.IN, gpio.OUT = 1023, 0, "in", "out"
    gpio.pinMode = lambda *a: None
    gpio.add_event_detect = lambda *a: None
    gpio.digitalWrite = saidas.__setitem__
    gpio.analogWrite = saidas.__setitem__
    gpio.customWrite = saidas.__setitem__
    gpio.digitalRead = lambda p: entradas.get(p, 0)
    gpio.analogRead = lambda p: entradas.get(p, 0)

    tempo = types.ModuleType("time")
    tempo.ctime = lambda *a: "t"
    tempo.sleep = lambda *a: None
    tempo.delay = lambda *a: None
    tempo.uptime = lambda: relogio["t"]

    class Cliente:
        ip = "192.168.1.21"

        def connected(self):
            return rede["conectado"]

        def send(self, dado):
            enviados.append(_json.loads(dado))

        def onReceive(self, funcao):
            pass

        def connect(self, *a):
            rede["tentativas"] += 1

        def close(self):
            rede["fechados"] = rede.get("fechados", 0) + 1

        def remoteIP(self):
            return self.ip

    class Servidor:
        def onNewClient(self, *a):
            pass

        def listen(self, *a):
            pass

    tcp = types.ModuleType("tcp")
    tcp.TCPClient, tcp.TCPServer = Cliente, Servidor

    js = types.ModuleType("json")
    js.dumps, js.loads = _json.dumps, _json.loads

    class ServidorHttp:
        route = staticmethod(lambda *a: None)
        start = staticmethod(lambda *a: True)

    http = types.ModuleType("http")
    http.HTTPServer = ServidorHttp

    class Ambiente:
        get = staticmethod(lambda chave: env.get(chave, 0.0))

    environment = types.ModuleType("environment")
    environment.Environment = Ambiente

    guardados = {}
    for dublado in (gpio, tempo, tcp, js, http, environment):
        guardados[dublado.__name__] = sys.modules.get(dublado.__name__)
        sys.modules[dublado.__name__] = dublado
    try:
        modulo = types.ModuleType(nome)
        logs = []
        modulo.__dict__["print"] = lambda *a: logs.append(" ".join(str(x) for x in a))
        with open(os.path.join(SRC, nome + ".py"), encoding="utf-8") as arquivo:
            exec(compile(arquivo.read(), nome, "exec"), modulo.__dict__)
    finally:
        for chave, valor in guardados.items():
            if valor is None:
                del sys.modules[chave]
            else:
                sys.modules[chave] = valor

    return {
        "m": modulo,
        "saidas": saidas,
        "entradas": entradas,
        "relogio": relogio,
        "enviados": enviados,
        "rede": rede,
        "env": env,
        "logs": logs,
        "Cliente": Cliente,
    }


def comando(modulo, topico, valor):
    """Entrega um comando do broker à zona."""
    modulo.ao_receber(_json.dumps({"topic": topico, "payload": valor}))


def publicacao(modulo, topico, valor):
    """Entrega à Central uma publicação de zona."""
    modulo.ao_receber(_json.dumps({"topic": topico, "payload": valor}))
