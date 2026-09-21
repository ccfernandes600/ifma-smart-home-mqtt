# =====================================================================
# ZONA JARDIM — no SBC (192.168.1.25)
# ---------------------------------------------------------------------
# Estacao meteorologica + irrigacao automatica. Clone do template
# validado da Sala (zona_sala.py), com tres automacoes locais em torno
# do NIVEL DE AGUA (uma grandeza, tres faixas):
#
#   nivel BAIXO (seco)    -> liga a IRRIGACAO (Lawn Sprinkler)
#   nivel na faixa boa    -> tudo desligado
#   nivel ALTO (alagado)  -> liga o DRENO (Drain Actuator)
#
# Detalhe fisico interessante do PT: o proprio Lawn Sprinkler CONTRIBUI
# para o nivel de agua do ambiente (0.1 cm/s, doc oficial) -- ou seja,
# irrigar faz o nivel subir de verdade, fechando a malha sozinho.
#
# 4a automacao: LUMINARIA acende quando escurece (Photo Sensor), com
# histerese pra nao piscar no lusco-fusco.
#
# Vento e pressao atmosferica sao so informativos (estacao meteo) --
# publicados crus/quantizados; o mapeamento raw->unidade fisica desses
# dois sensores NAO foi confirmado ainda (converter quando soubermos).
#
# ATENCAO -- NAO CONFIRMADO no PT ainda (checar doc dos devices ao
# montar): Lawn Sprinkler, Drain Actuator e Light assumidos
# digitalWrite binario (catalogo). Water Level/Wind/ATM Pressure
# assumidos analogRead (mesma familia do Temperature, ja validado).
# LIMIARES DE AGUA/LUZ EM RAW -- CALIBRAR com leituras reais no PT.
#
# MODO VIAGEM: esta zona ignora o broadcast casa/todas/cmd/modo de
# proposito. Planta nao viaja: a irrigacao depende da umidade do solo,
# e a luz do jardim acesa ajuda a simular presenca. Decisao registrada
# em docs/ARQUITETURA.md, junto com a da Cozinha.
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *

ZONA = "jardim"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

# --- Entradas ---
AGUA = 0  # D0: Water Level Monitor (analogRead 0-1023)
VENTO = 1  # D1: Wind Sensor         (analogRead 0-1023)
PRESSAO = 2  # D2: ATM Pressure        (analogRead 0-1023)
LUZ = 3  # D3: Photo Sensor        (analogRead 0-1023)
# --- Saidas ---
IRRIGACAO = 4  # D4: Lawn Sprinkler   (digitalWrite -- NAO CONFIRMADO)
DRENO = 5  # D5: Drain Actuator    (digitalWrite -- NAO CONFIRMADO)
LUMINARIA = 6  # D6: Light            (digitalWrite -- NAO CONFIRMADO)
# D7-D9 livres

# Faixas do nivel de agua (raw 0-1023) -- CALIBRAR com leituras reais
NIVEL_SECO = 150  # abaixo daqui: liga irrigacao
NIVEL_BOM = 300  # irrigacao desliga ao atingir (histerese da irrigacao)
NIVEL_ALAGADO = 800  # acima daqui: liga o dreno
NIVEL_OK = 650  # dreno desliga ao descer ate aqui (histerese do dreno)

# Luminaria (raw do Photo Sensor) -- CALIBRAR
LIM_ESCURO = 200  # abaixo: acende
LIM_CLARO = 300  # acima: apaga (histerese pro lusco-fusco)

PASSO_PUBLICACAO = 10  # quantizacao dos analogicos antes de publicar

_irrigando = False
_drenando = False
_luz_acesa = False

cliente = TCPClient()
_loops_sem_conexao = 0
anterior = {}  # ultimo valor publicado de cada grandeza


def log(msg):
    print("[{}] {}".format(ctime(), msg))


def publicar(grandeza, valor):
    if cliente.connected():
        cliente.send(
            dumps({"topic": "casa/{}/{}".format(ZONA, grandeza), "payload": valor})
        )
        return True
    log("AVISO: sem conexao com o broker -- {} nao publicado".format(grandeza))
    return False


def publicar_se_mudou(grandeza, valor):
    """Evita floodar o broker: so publica em mudanca de valor. So marca
    como publicado se o envio funcionou -- senao valores que falharam
    (ex.: 1o ciclo, antes da conexao abrir) nunca seriam reenviados."""
    if anterior.get(grandeza) != valor:
        if publicar(grandeza, valor):
            anterior[grandeza] = valor


def manter_conexao():
    """Reconecta ao broker se a conexao cair (padrao validado)."""
    global _loops_sem_conexao
    if cliente.connected():
        _loops_sem_conexao = 0
        return
    _loops_sem_conexao += 1
    if _loops_sem_conexao >= 3:  # tenta reconectar a cada ~6s
        _loops_sem_conexao = 0
        log("Reconectando ao broker {}...".format(BROKER_IP))
        cliente.connect(BROKER_IP, BROKER_PORT)


def quantizar(valor):
    """Arredonda a leitura analogica para multiplos de PASSO_PUBLICACAO."""
    return int(valor // PASSO_PUBLICACAO) * PASSO_PUBLICACAO


def atualizar_agua(nivel):
    """Tres faixas do nivel de agua: seco -> irriga; bom -> nada;
    alagado -> drena. Histereses evitam liga/desliga nos limiares."""
    global _irrigando, _drenando

    if nivel <= NIVEL_SECO:
        _irrigando = True
    elif nivel >= NIVEL_BOM:
        _irrigando = False

    if nivel >= NIVEL_ALAGADO:
        _drenando = True
    elif nivel <= NIVEL_OK:
        _drenando = False

    mudou_irrigacao = anterior.get("_irrigando") != _irrigando
    mudou_dreno = anterior.get("_drenando") != _drenando
    anterior["_irrigando"] = _irrigando
    anterior["_drenando"] = _drenando

    digitalWrite(IRRIGACAO, HIGH if _irrigando else LOW)
    digitalWrite(DRENO, HIGH if _drenando else LOW)

    if mudou_irrigacao:
        log(
            "Irrigacao: {} (nivel={})".format(
                "LIGOU" if _irrigando else "desligou", nivel
            )
        )
    if mudou_dreno:
        log("Dreno: {} (nivel={})".format("LIGOU" if _drenando else "desligou", nivel))


def atualizar_luminaria(luz_raw):
    """Luminaria com histerese: acende quando escurece, apaga quando
    clareia -- a folga entre os limiares evita piscar no lusco-fusco."""
    global _luz_acesa
    anterior_estado = _luz_acesa
    if luz_raw <= LIM_ESCURO:
        _luz_acesa = True
    elif luz_raw >= LIM_CLARO:
        _luz_acesa = False
    digitalWrite(LUMINARIA, HIGH if _luz_acesa else LOW)
    if _luz_acesa != anterior_estado:
        log(
            "Luminaria: {} (luz={})".format(
                "acendeu" if _luz_acesa else "apagou", luz_raw
            )
        )


def processar_sensores():
    """Polling dos analogicos (nao geram evento) + automacoes."""
    agua = analogRead(AGUA)
    vento = analogRead(VENTO)
    pressao = analogRead(PRESSAO)
    luz = analogRead(LUZ)

    atualizar_agua(agua)
    atualizar_luminaria(luz)

    publicar_se_mudou("agua", quantizar(agua))
    publicar_se_mudou("vento", quantizar(vento))
    publicar_se_mudou("pressao", quantizar(pressao))
    publicar_se_mudou("luz", quantizar(luz))


def ao_receber(data):
    """Comando do broker: casa/jardim/cmd/<atuador>."""
    try:
        cmd = loads(data)
    except:
        return
    alvo = cmd.get("topic", "")
    v = cmd.get("payload", 0)
    if alvo.endswith("/cmd/irrigacao"):
        digitalWrite(IRRIGACAO, HIGH if v else LOW)
        log("Comando recebido: irrigacao = {}".format(v))
    elif alvo.endswith("/cmd/dreno"):
        digitalWrite(DRENO, HIGH if v else LOW)
        log("Comando recebido: dreno = {}".format(v))
    elif alvo.endswith("/cmd/luz"):
        digitalWrite(LUMINARIA, HIGH if v else LOW)
        log("Comando recebido: luz = {}".format(v))


def setup():
    for p in [AGUA, VENTO, PRESSAO, LUZ]:
        pinMode(p, IN)
    for p in [IRRIGACAO, DRENO, LUMINARIA]:
        pinMode(p, OUT)
    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)
    log("Jardim conectando ao broker {}".format(BROKER_IP))


def main():
    setup()
    while True:
        manter_conexao()
        processar_sensores()
        sleep(2)


if __name__ == "__main__":
    main()
