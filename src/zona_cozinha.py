# =====================================================================
# ZONA COZINHA — no SBC (192.168.1.23)
# ---------------------------------------------------------------------
# Zona de seguranca contra incendio/gas. Fumaca e CO NAO sao lidos por
# GPIO -- aplicando direto a licao da Garagem (mesmo padrao de Smart
# Thing sem API programavel), a leitura usa o pacote `environment`.
# NAO REQUER TESTE GPIO PRIMEIRO: ja sabemos que Smoke/CO Detector nao
# tem Direct/Local Control (mesma familia de dispositivos do CO da
# Garagem e do RFID Reader).
#
# envID "CO" confirmado na Garagem. envID "Smoke" CONFIRMADO na bancada
# de 21/09/2026 (PT 9.0.1.0858): Environment.get("Smoke") existe e
# retorna sem erro. Nao precisa mais testar "Smoke Detector" nem
# similares -- a incognita que segurava esta zona esta resolvida.
#
# ATENCAO ao ambiente: o valor lido e o do CONTEINER onde o SBC esta,
# nao o da cidade. Conteiner aninhado nasce de outro template e roda o
# clima generico da Cisco -- ver simulacao/README.md. Injetar fumaca
# com diag_smoke.py exige que o setContribution caia no MESMO conteiner
# que este script le, senao o numero nao mexe e parece defeito de codigo.
#
# Perigo (fumaca OU CO acima do limiar) aciona TODOS os atuadores juntos
# -- mesmo espirito do "tudo ao mesmo tempo" da Garagem: Fire Sprinkler
# (apaga), Window (ventila fumaca/gas), Fan (exaustao), Alarm (avisa).
# Nao depende de modo_viagem -- risco de incendio importa com ou sem
# gente em casa.
#
# Temperatura/Umidade sao so informativas aqui (nao ha climatizacao
# na Cozinha no design atual) -- publicadas, sem acionar nada sozinhas.
#
# ATENCAO -- NAO CONFIRMADO no PT ainda:
#   - Fire Sprinkler: assumido digitalWrite (binario), por analogia a
#     outros sprinklers do catalogo -- poderia ser Custom como o Fan.
#   - Window: assumido customWrite "1"/"0", por analogia a Door/Garage
#     Door (mesma familia "abre/fecha").
#   - Fan e Alarm: JA CONFIRMADOS em outras zonas (mesmo tipo de device
#     em todo o projeto) -- customWrite e digitalWrite respectivamente.
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *
from environment import *

ZONA = "cozinha"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

# --- Entradas ---
TEMP = 0  # D0: Temperature   (analogRead 0-1023)
UMID = 1  # D1: Humidity      (analogRead 0-1023)
# --- Saidas ---
SPRINKLER = 2  # D2: Fire Sprinkler (digitalWrite -- NAO CONFIRMADO)
JANELA = 3  # D3: Window          (customWrite -- NAO CONFIRMADO)
FAN = 4  # D4: Fan              (customWrite "0"/"1"/"2" -- confirmado)
ALARME = 5  # D5: Alarm            (digitalWrite -- confirmado)
# D6-D9 livres (Smoke/CO nao ocupam porta -- lidos via environment)

LIMIAR_GAS = 20  # % -- mesmo limiar usado na Garagem
# Sem PASSO_PUBLICACAO aqui: temp sai em graus inteiros e umidade em %
# inteiro, que ja e granularidade suficiente. Quantizar em passos de 10
# daria temperatura de 10 em 10 graus.

_perigo = False
cliente = TCPClient()
_loops_sem_conexao = 0
_republicar = False  # conexao caiu: reenviar tudo ao voltar
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
    """Reconecta ao broker se a conexao cair (padrao validado no
    RFID Reader / zona_sala.py)."""
    global _loops_sem_conexao, _republicar
    if cliente.connected():
        _loops_sem_conexao = 0
        if _republicar:
            # A Central pode ter reiniciado sem estado: esquecer o que ja
            # foi publicado faz cada valor ser enviado de novo, senao ela
            # ficaria sem dado ate o valor mudar.
            _republicar = False
            anterior.clear()
        return
    _republicar = True
    _loops_sem_conexao += 1
    if _loops_sem_conexao >= 3:  # tenta reconectar a cada ~6s (3 loops de 2s)
        _loops_sem_conexao = 0
        log("Reconectando ao broker {}...".format(BROKER_IP))
        cliente.connect(BROKER_IP, BROKER_PORT)


def para_celsius(raw):
    """Converte raw 0-1023 em Celsius (-100..+100, confirmado por doc
    do Temperature Sensor e validado empiricamente na Sala)."""
    return -100.0 + (raw / 1023.0) * 200.0


def para_percentual(raw):
    """Converte raw 0-1023 em percentual 0-100."""
    return raw * 100.0 / 1023.0


def acionar_atuadores(ligar):
    """Sprinkler, Janela, Fan e Alarm agem sempre juntos."""
    digitalWrite(SPRINKLER, HIGH if ligar else LOW)
    customWrite(JANELA, "1" if ligar else "0")
    customWrite(FAN, "2" if ligar else "0")
    digitalWrite(ALARME, HIGH if ligar else LOW)


def verificar_perigo():
    """Le fumaca/CO do ambiente (nao e GPIO) e aciona todos os
    atuadores juntos se qualquer um cruzar o limiar. Chamado por
    polling -- ambiente nao gera evento."""
    global _perigo
    fumaca = Environment.get("Smoke")
    co = Environment.get("CO")
    perigo = (fumaca >= LIMIAR_GAS) or (co >= LIMIAR_GAS)

    if perigo != _perigo:
        _perigo = perigo
        acionar_atuadores(perigo)
        log(
            "PERIGO: {} (fumaca={} co={})".format(
                "INCENDIO/GAS DETECTADO" if perigo else "normalizado", fumaca, co
            )
        )

    publicar_se_mudou("fumaca", round(fumaca, 2))
    publicar_se_mudou("co", round(co, 2))


def processar_ambiente():
    """Temperatura/umidade sao so informativas na Cozinha -- sem
    climatizacao. Polling porque sao analogicas (sem evento)."""
    temp_c = round(para_celsius(analogRead(TEMP)))
    umid_pct = round(para_percentual(analogRead(UMID)))
    publicar_se_mudou("temp", temp_c)
    publicar_se_mudou("umidade", umid_pct)


def ao_receber(data):
    """Comando do broker: casa/cozinha/cmd/<atuador>."""
    try:
        cmd = loads(data)
    except:
        return
    alvo = cmd.get("topic", "")
    v = cmd.get("payload", 0)
    if alvo.endswith("/cmd/sprinkler"):
        digitalWrite(SPRINKLER, HIGH if v else LOW)
        log("Comando recebido: sprinkler = {}".format(v))
    elif alvo.endswith("/cmd/janela"):
        customWrite(JANELA, "1" if v else "0")
        log("Comando recebido: janela = {}".format(v))
    elif alvo.endswith("/cmd/fan"):
        customWrite(FAN, "2" if v else "0")
        log("Comando recebido: fan = {}".format(v))
    elif alvo.endswith("/cmd/alarme"):
        digitalWrite(ALARME, HIGH if v else LOW)
        log("Comando recebido: alarme = {}".format(v))


def setup():
    for p in [TEMP, UMID]:
        pinMode(p, IN)
    for p in [SPRINKLER, JANELA, FAN, ALARME]:
        pinMode(p, OUT)
    # So se escreve na transicao de perigo: sem isto, um alarme que ficou
    # ligado na execucao anterior nunca seria desligado.
    acionar_atuadores(False)
    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)
    log("Cozinha conectando ao broker {}".format(BROKER_IP))


def main():
    setup()
    while True:
        manter_conexao()
        verificar_perigo()
        processar_ambiente()
        sleep(2)


if __name__ == "__main__":
    main()
