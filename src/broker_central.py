# =====================================================================
# CENTRAL / BROKER — Smart Home MQTT (roda no SBC 192.168.1.100)
# ---------------------------------------------------------------------
# Papel: TCPServer na porta 1883 (padrao MQTT). Recebe as publicacoes
# JSON das zonas, mantem o estado global da casa, aplica as regras que
# cruzam zonas e aciona o LCD mestre + o Home Speaker.
#
# Protocolo (ver docs/ARQUITETURA.md):
#   publicacao: {"topic": "casa/<zona>/<grandeza>", "payload": <valor>}
#   comando:    {"topic": "casa/<zona>/cmd/<atuador>", "payload": <valor>}
#
# OBS: onReceive(callback) chama o callback com UM argumento (data),
# nao (client, data) -- confirmado no PT 9.0.0 (erro: "ao_receber()
# missing 1 required argument: data"). Vale tanto no client.onReceive
# quanto no lado do servidor (por-conexao).
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *

# --- Portas do proprio SBC Central ---
BTN_MODO = 0  # D0: Push Button (alterna modo casa/viagem)
LCD_MESTRE = 1  # D1: LCD mestre (2 linhas)
SPEAKER = 2  # D2: Home Speaker (avisos sonoros)

PORTA_BROKER = 1883

# --- Estado global: ultimo valor recebido de cada topico ---
estado = {}
clientes = []
modo_viagem = False

LIMIAR_GAS = 20  # % -- mesmo limiar usado nas zonas (ver zona_garagem.py)
_ultima_tela = None  # evita reescrever o LCD e repetir o log sem necessidade

# --- Controle de acesso por RFID (o Reader publica casa/perimetro/rfid) ---
CARTOES_VALIDOS = [1005]  # IDs autorizados a abrir a porta do perimetro
DURACAO_PORTA_RFID = 5  # segundos que a porta fica aberta apos cartao valido
PERIMETRO_IP = "192.168.1.21"
_porta_fecha_em = 0  # uptime() em que a porta deve fechar (0 = fechada)


def log(msg):
    """Espelha eventos no terminal com carimbo de tempo."""
    print("[{}] {}".format(ctime(), msg))


def mostrar(linha1, linha2):
    """Escreve no LCD mestre e registra no terminal. Atualiza o cache
    de tela para o avaliar_regras() saber que o LCD mudou."""
    global _ultima_tela
    customWrite(LCD_MESTRE, "{}\n{}".format(linha1, linha2))
    log(linha1 + " | " + linha2)
    _ultima_tela = (linha1, linha2)


def avaliar_regras():
    """O 'cerebro' da casa: decisoes que dependem de varias zonas."""
    # Gas/fumaca so conta como perigo a partir do mesmo limiar usado nas
    # zonas (LIMIAR_GAS) -- nao basta ser != 0, senao alerta cedo demais
    gas = (
        estado.get("casa/garagem/co", 0) >= LIMIAR_GAS
        or estado.get("casa/garagem/co2", 0) >= LIMIAR_GAS
        or estado.get("casa/cozinha/co", 0) >= LIMIAR_GAS
        or estado.get("casa/cozinha/fumaca", 0) >= LIMIAR_GAS
    )
    campainha = estado.get("casa/perimetro/campainha", 0)
    movimento_garagem = estado.get("casa/garagem/movimento", 0)
    intrusao = movimento_garagem and modo_viagem  # movimento + ninguem esperado em casa

    digitalWrite(SPEAKER, HIGH if (gas or campainha) else LOW)

    if gas:
        tela = ("ALERTA DE GAS", "Verifique a casa")
    elif intrusao:
        tela = ("INTRUSAO!", "Movimento na garagem")
    elif campainha:
        tela = ("VISITANTE", "Campainha tocada")
    elif movimento_garagem:
        tela = ("MOVIMENTO", "Garagem (normal)")
    elif modo_viagem:
        tela = ("MODO VIAGEM", "Casa monitorada")
    else:
        tela = ("CASA OK", "Modo normal")

    # So escreve no LCD/loga se o estado da tela realmente mudou
    if tela != _ultima_tela:
        mostrar(tela[0], tela[1])


def enviar_comando(ip, topico, valor):
    """Envia um comando para a zona conectada com aquele IP."""
    msg = dumps({"topic": topico, "payload": valor})
    for c in clientes:
        if c.connected() and c.remoteIP() == ip:
            c.send(msg)
            return True
    log("Comando nao entregue (zona {} offline): {}".format(ip, topico))
    return False


def processar_rfid(tag):
    """Controle de acesso: cartao valido abre a porta do perimetro por
    DURACAO_PORTA_RFID segundos (verificar_porta_rfid fecha depois)."""
    global _porta_fecha_em
    try:
        tag_num = int(tag)
    except:
        tag_num = 0
    if tag_num == 0:
        return
    if tag_num in CARTOES_VALIDOS:
        if enviar_comando(PERIMETRO_IP, "casa/perimetro/cmd/porta", 1):
            _porta_fecha_em = uptime() + DURACAO_PORTA_RFID
            mostrar("ACESSO LIBERADO", "Cartao {}".format(tag_num))
    else:
        mostrar("CARTAO INVALIDO", "ID {}".format(tag_num))


def verificar_porta_rfid():
    """Fecha a porta do perimetro apos o prazo do cartao valido."""
    global _porta_fecha_em
    if _porta_fecha_em and uptime() >= _porta_fecha_em:
        _porta_fecha_em = 0
        enviar_comando(PERIMETRO_IP, "casa/perimetro/cmd/porta", 0)
        log("Porta do perimetro fechada automaticamente")
        avaliar_regras()  # restaura a tela de estado no LCD


def ao_receber(data):
    """Chega uma publicacao JSON de uma zona."""
    try:
        msg = loads(data)
    except:
        return
    topico = msg.get("topic", "")
    valor = msg.get("payload", 0)
    estado[topico] = valor
    log("RX  " + topico + " = " + str(valor))
    if topico == "casa/perimetro/rfid":
        processar_rfid(valor)  # evento de acesso: nao passa pela tela de estado
        return
    avaliar_regras()


def transmitir_modo(alvo=None):
    """Avisa as zonas conectadas sobre o modo atual (casa/viagem). Se
    'alvo' for informado, manda so pra esse cliente (zona recem-conectada);
    senao, transmite pra todas."""
    msg = dumps({"topic": "casa/todas/cmd/modo", "payload": modo_viagem})
    destinatarios = [alvo] if alvo else clientes
    for c in destinatarios:
        if c.connected():
            c.send(msg)


def ao_novo_cliente(client):
    """Uma zona acabou de conectar ao broker."""
    clientes.append(client)
    client.onReceive(ao_receber)
    log("Zona conectada: " + client.remoteIP())
    transmitir_modo(alvo=client)  # zona nova precisa saber o modo atual


def ler_modo(*args):
    """Interrupcao do botao de modo. O Push Button do PT e momentaneo
    (dispara ao apertar E ao soltar) -- por isso so reagimos a transicao
    para HIGH e INVERTEMOS o modo, tratando o botao como toggle. Ignorar
    o LOW evita que soltar o botao desfaca a troca na hora."""
    global modo_viagem
    if digitalRead(BTN_MODO) == HIGH:
        modo_viagem = not modo_viagem
        transmitir_modo()
        avaliar_regras()
        log("Modo viagem = {}".format(modo_viagem))


def setup():
    pinMode(BTN_MODO, IN)
    pinMode(LCD_MESTRE, OUT)
    pinMode(SPEAKER, OUT)
    add_event_detect(BTN_MODO, ler_modo)

    servidor = TCPServer()
    servidor.onNewClient(ao_novo_cliente)
    servidor.listen(PORTA_BROKER)
    log("Broker ouvindo na porta {}".format(PORTA_BROKER))
    avaliar_regras()


def main():
    setup()
    while True:
        verificar_porta_rfid()  # fecha a porta do perimetro apos o prazo
        sleep(1)


if __name__ == "__main__":
    main()
