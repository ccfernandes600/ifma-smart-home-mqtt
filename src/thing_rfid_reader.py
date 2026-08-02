# =====================================================================
# RFID READER (Smart Thing) — script embutido do dispositivo (192.168.1.33)
# ---------------------------------------------------------------------
# VALIDADO NO PT 9.0.0 (02/07/2026): tag 1005 lida e publicada.
#
# Este script roda DENTRO do RFID Reader (aba Programming do Thing),
# substituindo o script padrao da Cisco que falava com um Registration
# Server via ioeclient. Aqui, o Reader vira um NO MQTT independente:
# detecta o RFID Card por proximidade fisica e publica a tag em
# casa/perimetro/rfid direto no broker (tcp+json, como as zonas).
#
# SETUP NECESSARIO (ver docs/MONTAGEM_PACKET_TRACER.md):
#   - I/O Config: Digital Slots 0 -> 1 (device vem de fabrica SEM slots)
#     e conferir o Network Adapter (PT-IOT-NM-1CFE p/ cabo, ou WiFi)
#   - IP estatico 192.168.1.33 na LAN
#   - RFID Card: definir o ID no script JS dele (var CARD_ID = 1005;)
#
# Particularidades deste motor de script (diferente do SBC/MCU):
#   - devicesAt() retorna DICT {'0': 'NomeDevice', ...} -- indexar como
#     lista (devices[0]) da KeyError: 0
#   - getDeviceProperty(nome, "CardID") le o CARD_ID do Card
#   - exemplos da Cisco sao Python 2 (xrange, delay/idle)
# =====================================================================

from time import *
from physical import *
from gpio import *
from tcp import *
from json import *

DELAY_TIME = 1000

X_READ_DISTANCE = 50
Y_READ_DISTANCE = 50
cardID = 0
lastCardID = 0

ZONA = "perimetro"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

cliente = TCPClient()
_loops_sem_conexao = 0


def publicar(grandeza, valor):
    if cliente.connected():
        cliente.send(
            dumps({"topic": "casa/{}/{}".format(ZONA, grandeza), "payload": valor})
        )
    else:
        print("AVISO: sem conexao com o broker -- leitura nao publicada")


def manter_conexao():
    """Reconecta ao broker se a conexao cair (ex.: broker reiniciado).
    Sem isso, reiniciar a Central mataria a conexao e o Reader ficaria
    mudo em silencio -- a ordem de reinicio deixaria de funcionar."""
    global _loops_sem_conexao
    if cliente.connected():
        _loops_sem_conexao = 0
        return
    _loops_sem_conexao += 1
    if _loops_sem_conexao >= 5:  # tenta reconectar a cada ~5s
        _loops_sem_conexao = 0
        print("Reconectando ao broker {}...".format(BROKER_IP))
        cliente.connect(BROKER_IP, BROKER_PORT)


def setup():
    cliente.connect(BROKER_IP, BROKER_PORT)
    print("RFID Reader conectando ao broker {}".format(BROKER_IP))


def loop():
    global cardID, lastCardID
    # devicesAt() neste motor retorna um DICT {'0': 'NomeDevice', ...}
    # (confirmado no PT 9.0.0) -- as chaves sao indices em string e os
    # VALORES sao os nomes. O exemplo oficial da Cisco indexava como
    # lista (devices[i]) e quebrava com KeyError: 0.
    devices = devicesAt(getCenterX(), getCenterY(), X_READ_DISTANCE, Y_READ_DISTANCE)

    found = False
    for k in devices:
        nome = devices[k]
        if nome == getName():
            continue
        valor = getDeviceProperty(nome, "CardID")
        if valor:  # so e leitura valida se o vizinho tiver CardID definido
            cardID = valor
            found = True
            break

    if not found:
        cardID = lastCardID = 0
    else:
        if lastCardID != cardID:
            lastCardID = cardID
            publicar("rfid", cardID)
            print("RFID leu tag: {}".format(cardID))

    delay(DELAY_TIME)


if __name__ == "__main__":
    setup()
    while True:
        manter_conexao()  # reconecta se o broker tiver reiniciado
        loop()
        idle()
