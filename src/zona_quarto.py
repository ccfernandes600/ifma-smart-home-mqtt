# =====================================================================
# ZONA QUARTO — no SBC (192.168.1.24)
# ---------------------------------------------------------------------
# Zona de descanso e qualidade do ar. Clone do template validado da
# Sala (zona_sala.py), com tres automacoes locais:
#
#   1. CLIMATIZACAO: temp >= 30C liga o AC (histerese de 2C, desliga
#      só abaixo de 28C) -- mesmo padrao validado na Sala.
#   2. UMIDIFICADOR: umidade < 40% liga; so desliga ao recuperar 50%
#      (histerese) -- ar seco atrapalha o sono.
#   3. LUZ DE PRESENCA: movimento detectado + ambiente ESCURO acende
#      o Smart LED; apaga quando o movimento expira (hold de 10s) ou
#      quando clareia. De dia, movimento nao acende nada.
#
# Janela abre so por comando remoto (cmd/janela), como Door/Garage Door.
#
# ATENCAO -- NAO CONFIRMADO no PT ainda (checar doc dos devices ao
# montar, mesma diligencia do Fan/AC):
#   - Humidifier: assumido digitalWrite binario (catalogo diz +1%/h).
#   - Smart LED: assumido digitalWrite binario (o catalogo diz
#     "Dimmable", pode aceitar niveis via custom/analog -- usamos so
#     liga/desliga por enquanto).
#   - Window: assumido customWrite "1"/"0" (analogia a Door -- ainda
#     nao confirmado em teste; mesmo assumido na Cozinha).
# Ja confirmados em outras zonas: AC (digitalWrite), Temperature/
# Humidity/Photo (analogRead), Motion (digitalRead + hold).
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *

ZONA = "quarto"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

# --- Entradas ---
TEMP = 0  # D0: Temperature   (analogRead 0-1023)
UMID = 1  # D1: Humidity      (analogRead 0-1023)
LUZ = 2  # D2: Photo Sensor  (analogRead 0-1023)
MOV = 3  # D3: Motion        (digitalRead, evento)
# --- Saidas ---
AC = 4  # D4: AC / Air Conditioner (digitalWrite -- confirmado)
UMIDIFICADOR = 5  # D5: Humidifier    (digitalWrite -- NAO CONFIRMADO)
LED = 6  # D6: Smart LED      (digitalWrite -- NAO CONFIRMADO)
JANELA = 7  # D7: Window        (customWrite -- NAO CONFIRMADO)
# D8, D9 livres

# Climatizacao (graus Celsius; conversao confirmada por doc + teste)
LIM_TEMP_ALTA = 30.0  # liga AC a partir daqui
HISTERESE_TEMP = 2.0  # so desliga abaixo de LIM_TEMP_ALTA - HISTERESE

# Umidificador (percentual; histerese p/ nao ligar/desligar no limiar)
UMID_MIN = 40.0  # liga o umidificador abaixo daqui
UMID_OK = 50.0  # so desliga ao recuperar este nivel

# Luz de presenca
LIM_ESCURO = 200  # raw 0-1023 do Photo Sensor -- CALIBRAR no PT
DURACAO_MOVIMENTO = 10  # segundos que "movimento" fica reportado ativo

PASSO_PUBLICACAO = 10  # quantizacao da luz (raw) antes de publicar

_mov_expira_em = 0
_quente = False
_umidificando = False
_led_aceso = False
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


def para_celsius(raw):
    """raw 0-1023 -> -100..+100 C (confirmado por doc + teste na Sala)."""
    return -100.0 + (raw / 1023.0) * 200.0


def para_percentual(raw):
    """raw 0-1023 -> 0-100%."""
    return raw * 100.0 / 1023.0


def atualizar_climatizacao(temp_c):
    """AC com histerese -- mesmo padrao validado na Sala.

    Em modo viagem o AC fica desligado: quarto vazio nao precisa de
    climatizacao, e e o maior consumo da zona."""
    global _quente
    if _modo_viagem:
        if _quente:
            log("Modo viagem: AC desligado")
        _quente = False
        digitalWrite(AC, LOW)
        return
    anterior_quente = _quente
    if temp_c >= LIM_TEMP_ALTA:
        _quente = True
    elif temp_c <= LIM_TEMP_ALTA - HISTERESE_TEMP:
        _quente = False
    digitalWrite(AC, HIGH if _quente else LOW)
    if _quente != anterior_quente:
        log("AC: {} (temp={}C)".format("LIGOU" if _quente else "desligou", temp_c))


def atualizar_umidificador(umid_pct):
    """Umidificador com histerese: liga <40%, so desliga ao voltar a 50%."""
    global _umidificando
    anterior_estado = _umidificando
    if umid_pct < UMID_MIN:
        _umidificando = True
    elif umid_pct >= UMID_OK:
        _umidificando = False
    digitalWrite(UMIDIFICADOR, HIGH if _umidificando else LOW)
    if _umidificando != anterior_estado:
        log(
            "Umidificador: {} (umidade={}%)".format(
                "LIGOU" if _umidificando else "desligou", umid_pct
            )
        )


def atualizar_luz_presenca(luz_raw):
    """Smart LED acende com movimento ATIVO + ambiente escuro; apaga
    quando o movimento expira ou quando clareia.

    Em modo viagem a luz de presenca nao acende: movimento com a casa
    vazia e assunto de vigilancia, tratado pela Central, e nao motivo
    para iluminar o comodo para quem quer que esteja ali."""
    global _led_aceso
    escuro = luz_raw <= LIM_ESCURO
    movimento_ativo = _mov_expira_em != 0
    acender = movimento_ativo and escuro and not _modo_viagem
    if acender != _led_aceso:
        _led_aceso = acender
        digitalWrite(LED, HIGH if acender else LOW)
        log("Luz de presenca: {}".format("acendeu" if acender else "apagou"))


def processar_sensores():
    """Polling dos analogicos + as tres automacoes locais."""
    temp_c = round(para_celsius(analogRead(TEMP)))
    umid_pct = round(para_percentual(analogRead(UMID)))
    luz_raw = analogRead(LUZ)

    atualizar_climatizacao(temp_c)
    atualizar_umidificador(umid_pct)
    atualizar_luz_presenca(luz_raw)

    publicar_se_mudou("temp", temp_c)
    publicar_se_mudou("umidade", umid_pct)
    publicar_se_mudou("luz", quantizar(luz_raw))


def processar_movimento(*args):
    """So reage a transicao para HIGH (hold decide o fim)."""
    global _mov_expira_em
    if digitalRead(MOV) == HIGH:
        novo = _mov_expira_em == 0
        _mov_expira_em = uptime() + DURACAO_MOVIMENTO
        atualizar_luz_presenca(analogRead(LUZ))  # acende na hora se escuro
        if novo:
            publicar("movimento", 1)
            log("Movimento detectado (mantido por {}s)".format(DURACAO_MOVIMENTO))


def verificar_movimento():
    """Encerra o estado de movimento apos DURACAO_MOVIMENTO segundos."""
    global _mov_expira_em
    if _mov_expira_em and uptime() >= _mov_expira_em:
        _mov_expira_em = 0
        atualizar_luz_presenca(analogRead(LUZ))  # apaga a luz de presenca
        publicar("movimento", 0)
        log("Movimento encerrado")


def ao_receber(data):
    """Comando do broker: casa/quarto/cmd/<atuador> ou o broadcast de modo
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
    elif alvo.endswith("/cmd/umidificador"):
        digitalWrite(UMIDIFICADOR, HIGH if v else LOW)
        log("Comando recebido: umidificador = {}".format(v))
    elif alvo.endswith("/cmd/led"):
        digitalWrite(LED, HIGH if v else LOW)
        log("Comando recebido: led = {}".format(v))
    elif alvo.endswith("/cmd/janela"):
        customWrite(JANELA, "1" if v else "0")
        log("Comando recebido: janela = {}".format(v))
    elif alvo.endswith("/cmd/modo"):
        _modo_viagem = bool(v)
        if _modo_viagem:
            digitalWrite(UMIDIFICADOR, LOW)  # corta na hora, sem esperar o ciclo
        log("Modo viagem = {}".format(_modo_viagem))


def setup():
    for p in [TEMP, UMID, LUZ, MOV]:
        pinMode(p, IN)
    for p in [AC, UMIDIFICADOR, LED, JANELA]:
        pinMode(p, OUT)
    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)
    log("Quarto conectando ao broker {}".format(BROKER_IP))
    add_event_detect(MOV, processar_movimento)


def main():
    setup()
    while True:
        manter_conexao()
        processar_sensores()
        verificar_movimento()
        sleep(2)


if __name__ == "__main__":
    main()
