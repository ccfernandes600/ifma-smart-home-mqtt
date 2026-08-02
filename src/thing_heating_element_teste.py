# =====================================================================
# HEATING ELEMENT (Smart Thing) — script embutido, versao de TESTE
# ---------------------------------------------------------------------
# NAO faz parte da automacao das zonas -- e um instrumento de teste,
# como o Old Car na Garagem. Serve para forcar a temperatura da Sala
# subir e validar a reacao do AC/Fan/RGB (zona_sala.py).
#
# Montagem: Rocker Switch --[cabo IoT]--> Heating Element (D0 dele),
# posicionado no MESMO CONTEINER FISICO do Temperature Sensor da Sala
# (a "temperatura ambiente" e uma variavel compartilhada do contexto
# fisico -- ver docs/LEVANTAMENTO_DISPOSITIVOS_PT9.md secao 2.9).
# Nao precisa de nenhuma ligacao com o SBC da Sala.
#
# TEMPERATURE_RATE turbinado (100. em vez do original 10./3600 = 10C/h)
# -- em teste real (03/07/2026) essa taxa aquece rapido o suficiente
# para uma demonstracao em aula, mesmo com o contentor fisico grande
# (a taxa e dividida por Environment.getVolume(): quanto maior o
# comodo, mais fraco o efeito do aquecedor, fisicamente correto).
#
# O print de updateEnvironment() mostra input, volume real do conteiner
# e a taxa efetiva em C/hora -- use para calibrar TEMPERATURE_RATE se
# a subida estiver rapida ou lenta demais no seu ambiente.
#
# AJUSTADO (03/07/2026): script original usava digitalRead(0) via
# add_event_detect. Teste simultaneo confirmou que digitalRead(0) e
# analogRead(0) SEMPRE retornam o mesmo valor nesta porta (nao ha
# divergencia real -- 14 leituras identicas lado a lado). A causa do
# problema anterior foi o gesto de clique (ALT+clique necessario, nao
# clique normal), nao a funcao de leitura. Trocado para analogRead()
# + polling (sem add_event_detect) por precaucao: nao confirmamos se
# portas adicionadas manualmente via I/O Config disparam evento de
# forma confiavel -- polling e o padrao ja validado (zona_sala.py).
#
# Fonte original: script padrao da Cisco para o device Heating Element.
# =====================================================================

from time import *
from physical import *
from gpio import *
from environment import Environment

HUMIDITY_RATE = -2.0 / 3600  # -2% por hora (original, sem alteracao)
TEMPERATURE_RATE = 2.0  # TURBINADO p/ teste/demo (original era 10./3600 = 10C/h).
# CALIBRADO (03/07/2026): com este volume de conteiner (~91630 cm3,
# quase igual ao VOLUME_AT_RATE de referencia), TEMPERATURE_RATE=100
# deu ~109C/s (392880 C/h) -- rapido DEMAIS, estoura o sensor (max 100C)
# em menos de 1s. 2.0 da uma taxa efetiva de ~2.2C/s, cruzando os 30C
# em ~15s -- ritmo observavel e controlavel numa demonstracao em aula.
VOLUME_AT_RATE = 100000.0
MAX_RATE = 1.0e6

input = 0.0


def setup():
    pass


def atualizar_entrada():
    """Le a porta D0 por POLLING (nao por add_event_detect). Testes
    empiricos (03/07/2026) mostraram analogRead(0) consistente (1023
    ligado / 0 desligado) enquanto digitalRead(0) foi inconsistente
    nesta porta adicionada manualmente via I/O Config -- suspeita de
    que portas assim nao geram evento de forma confiavel, mesmo padrao
    ja visto nos sensores analogicos da Sala (zona_sala.py)."""
    global input
    input = analogRead(0) / 1023.0
    digitalWrite(5, HIGH if input > 0 else LOW)


def loop():
    atualizar_entrada()
    updateEnvironment()
    delay(1000)


def updateEnvironment():
    humidity_rate = input * HUMIDITY_RATE * VOLUME_AT_RATE / Environment.getVolume()
    temperature_rate = (
        input * TEMPERATURE_RATE * VOLUME_AT_RATE / Environment.getVolume()
    )
    Environment.setContribution("Humidity", humidity_rate, MAX_RATE, True)
    Environment.setContribution("Ambient Temperature", temperature_rate, MAX_RATE, True)
    print(
        "input={} volume={} temp_taxa_efetiva_C_por_h={}".format(
            input, Environment.getVolume(), temperature_rate * 3600
        )
    )


if __name__ == "__main__":
    setup()
    while True:
        loop()
        sleep(0)
