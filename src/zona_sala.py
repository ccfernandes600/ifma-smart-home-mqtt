# =====================================================================
# ZONA SALA — no SBC (192.168.1.22)
# ---------------------------------------------------------------------
# Zona de clima/conforto. Usa sensores ANALOGICOS -> por isso e SBC.
# Sensores: Temperatura, Umidade, Luminosidade (analog) + Movimento
# (digital). Atuadores: AC, Fan, LED RGB (R/G/B).
#
# REVISADO (03/07/2026) com as licoes validadas na Garagem/Perimetro:
#   - Fan e CUSTOM, nao digital: customWrite("0"/"1"/"2") -- confirmado
#     na Garagem (0=off, 1=vel. baixa, 2=vel. alta).
#   - Motion com hold de 10s (o sensor do PT volta a LOW sozinho em ~5s).
#   - Reconexao automatica ao broker (padrao validado no RFID Reader).
#   - Histerese na climatizacao (liga em LIM_TEMP_ALTA, so desliga
#     LIM_TEMP_ALTA-HISTERESE abaixo) -- evita liga/desliga rapido
#     quando a temperatura oscila no limiar.
#   - Leituras publicadas em unidades REAIS: temperatura em graus C
#     (conversao raw 0-1023 -> -100..+100C, faixa padrao do PT) e
#     umidade em % -- o log compara a conversao com o termometro do
#     simulador (Environment.get("Ambient Temperature")) p/ conferencia.
#   - Luz quantizada (passos de PASSO_PUBLICACAO) antes de publicar --
#     valores do PT derivam continuamente, sem isso floodaria o broker.
#
# AC CONFIRMADO (03/07/2026, doc do device no PT): "Local Control:
# DigitalWrite HIGH on D0 for ON, LOW for OFF" -- binario e digital,
# digitalWrite correto (diferente do Fan, que tem 3 estados/Custom).
# Resfria -10C/h e -2% umidade/h.
#
# analogRead CONFIRMADO (03/07/2026): temp raw=500 e umidade raw=790
# lidos com sucesso -- primeira leitura analogica do projeto validada.
#
# analogWrite: faixa 0-1023 (resolucao real de 256 niveis / 8 bits).
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *
from environment import *

ZONA = "sala"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

# --- Entradas ---
TEMP = 0  # D0: Temperature   (analogRead 0-1023)
UMID = 1  # D1: Humidity      (analogRead 0-1023)
LUZ = 2  # D2: Photo Sensor  (analogRead 0-1023)
MOV = 3  # D3: Motion        (digitalRead, evento)
# --- Saidas ---
AC = 4  # D4: AC / Air Conditioner (digitalWrite HIGH/LOW -- confirmado)
FAN = 5  # D5: Fan             (customWrite "0"/"1"/"2" -- confirmado)
LED_R = 6  # D6: LED R (analogWrite)
LED_G = 7  # D7: LED G (analogWrite)
LED_B = 8  # D8: LED B (analogWrite)

# Conversao do Temperature Sensor -- CONFIRMADO pela doc do device
# (03/07/2026): "analogRead gives values from 0 to 1023 mapping to
# -100C to 100C". (A mesma doc tambem cita "0 to 255" no Data Spec --
# e a dualidade 8/10 bits ja vista no analogWrite; a API retorna
# 0-1023, comprovado pela leitura raw=500 no teste.)
SENSOR_TEMP_MIN = -100.0  # C correspondente a raw 0
SENSOR_TEMP_MAX = 100.0  # C correspondente a raw 1023

# Climatizacao (em graus Celsius)
LIM_TEMP_ALTA = 30.0  # liga AC/Fan a partir daqui (C)
HISTERESE = 2.0  # so desliga abaixo de LIM_TEMP_ALTA - HISTERESE (C)

PASSO_PUBLICACAO = 10  # quantizacao da luz (raw) antes de publicar
DURACAO_MOVIMENTO = 10  # segundos que "movimento" fica reportado ativo

_mov_expira_em = 0
_quente = False  # estado da climatizacao (mantido p/ histerese)
_modo_viagem = False  # chega da Central pelo broadcast casa/todas/cmd/modo

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
    """Reconecta ao broker se a conexao cair (ex.: broker reiniciado).
    ATENCAO -- na bancada de 21/09 isto NAO cobriu o reinicio da Central:
    o objeto cliente seguiu reportando connected() com o servidor fora do
    ar (conexao fantasma) e a zona ficou muda. Regra operacional enquanto
    nao houver heartbeat: recolou a Central, reinicie as zonas."""
    global _loops_sem_conexao
    if cliente.connected():
        _loops_sem_conexao = 0
        return
    _loops_sem_conexao += 1
    if _loops_sem_conexao >= 3:  # tenta reconectar a cada ~6s (3 loops de 2s)
        _loops_sem_conexao = 0
        log("Reconectando ao broker {}...".format(BROKER_IP))
        cliente.connect(BROKER_IP, BROKER_PORT)


def rgb(r, g, b):
    analogWrite(LED_R, r)
    analogWrite(LED_G, g)
    analogWrite(LED_B, b)


def quantizar(valor):
    """Arredonda a leitura analogica para multiplos de PASSO_PUBLICACAO.
    Os valores do PT derivam continuamente -- sem isso, cada polling
    publicaria um valor 'novo' e inundaria o broker."""
    return int(valor // PASSO_PUBLICACAO) * PASSO_PUBLICACAO


def para_celsius(raw):
    """Converte a leitura crua (0-1023) do Temperature Sensor em C,
    usando a faixa padrao do PT (SENSOR_TEMP_MIN..SENSOR_TEMP_MAX)."""
    return SENSOR_TEMP_MIN + (raw / 1023.0) * (SENSOR_TEMP_MAX - SENSOR_TEMP_MIN)


def para_percentual(raw):
    """Converte leitura crua (0-1023) em percentual 0-100 (umidade)."""
    return raw * 100.0 / 1023.0


def atualizar_climatizacao(temp):
    """Liga AC+Fan quando esquenta; so desliga com folga (histerese),
    evitando liga/desliga em sequencia no limiar.

    Em modo viagem a climatizacao fica desligada: nao ha quem sinta calor,
    e sem esse corte o AC passaria a viagem inteira ligado por temperatura."""
    global _quente
    if _modo_viagem:
        if _quente:
            log("Modo viagem: climatizacao desligada")
        _quente = False
        digitalWrite(AC, LOW)
        customWrite(FAN, "0")
        rgb(0, 0, 900)  # azul: sala em modo viagem
        return
    anterior_quente = _quente
    if temp >= LIM_TEMP_ALTA:
        _quente = True
    elif temp <= LIM_TEMP_ALTA - HISTERESE:
        _quente = False

    digitalWrite(AC, HIGH if _quente else LOW)  # AC e digital (confirmado)
    customWrite(FAN, "2" if _quente else "0")  # Fan e Custom (confirmado)
    if _quente:
        rgb(1023, 512, 0)  # laranja: ambiente quente
    else:
        rgb(0, 900, 0)  # verde: conforto ok

    if _quente != anterior_quente:
        log(
            "Climatizacao: {} (temp={}C, limiar={}C)".format(
                "LIGOU (AC+Fan)" if _quente else "desligou", temp, LIM_TEMP_ALTA
            )
        )


def processar_sensores():
    """Polling dos analogicos (nao geram evento) + logica de conforto.
    Temperatura publicada em C (inteiro) e umidade em % (inteiro) --
    o arredondamento ja evita flood no broker; luz segue crua/quantizada."""
    temp_raw = analogRead(TEMP)
    temp_c = round(para_celsius(temp_raw))
    umid_pct = round(para_percentual(analogRead(UMID)))
    luz = analogRead(LUZ)

    atualizar_climatizacao(temp_c)

    if anterior.get("temp") != temp_c:
        # Conferencia da conversao: compara com o termometro do simulador
        try:
            ambiente = round(Environment.get("Ambient Temperature"), 1)
        except:
            ambiente = "?"
        log(
            "Temp {}C (raw {} | ambiente do PT: {}C)".format(temp_c, temp_raw, ambiente)
        )
    publicar_se_mudou("temp", temp_c)
    publicar_se_mudou("umidade", umid_pct)
    publicar_se_mudou("luz", quantizar(luz))


def processar_movimento(*args):
    """Interrupcao GPIO: so reage quando o sensor VAI para HIGH; o
    retorno a LOW (~5s, automatico no PT) e ignorado -- o hold decide."""
    global _mov_expira_em
    if digitalRead(MOV) == HIGH:
        novo = _mov_expira_em == 0
        _mov_expira_em = uptime() + DURACAO_MOVIMENTO
        if novo:
            publicar("movimento", 1)
            log("Movimento detectado (mantido por {}s)".format(DURACAO_MOVIMENTO))


def verificar_movimento():
    """Encerra o estado de movimento apos DURACAO_MOVIMENTO segundos."""
    global _mov_expira_em
    if _mov_expira_em and uptime() >= _mov_expira_em:
        _mov_expira_em = 0
        publicar("movimento", 0)
        log("Movimento encerrado")


def ao_receber(data):
    """Comando do broker: casa/sala/cmd/<atuador> ou o broadcast de modo
    casa/todas/cmd/modo."""
    global _modo_viagem
    try:
        cmd = loads(data)
    except:
        return
    alvo = cmd.get("topic", "")
    v = cmd.get("payload", 0)
    if alvo.endswith("/cmd/ac"):
        digitalWrite(AC, HIGH if v else LOW)
        log("Comando recebido: ac = {}".format(v))
    elif alvo.endswith("/cmd/fan"):
        customWrite(FAN, "2" if v else "0")
        log("Comando recebido: fan = {}".format(v))
    elif alvo.endswith("/cmd/rgb"):
        # payload esperado: lista [r, g, b] na escala 0-1023
        try:
            rgb(v[0], v[1], v[2])
            log("Comando recebido: rgb = {}".format(v))
        except:
            log("cmd/rgb invalido (esperado [r,g,b]): {}".format(v))
    elif alvo.endswith("/cmd/modo"):
        _modo_viagem = bool(v)
        log("Modo viagem = {}".format(_modo_viagem))


def setup():
    for p in [TEMP, UMID, LUZ, MOV]:
        pinMode(p, IN)
    for p in [AC, FAN, LED_R, LED_G, LED_B]:
        pinMode(p, OUT)
    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)
    log("Sala conectando ao broker {}".format(BROKER_IP))
    add_event_detect(MOV, processar_movimento)


def main():
    setup()
    while True:
        manter_conexao()  # reconecta se o broker tiver reiniciado
        processar_sensores()  # analogico -> polling periodico
        verificar_movimento()  # encerra o "movimento ativo" apos o prazo
        sleep(2)


if __name__ == "__main__":
    main()
