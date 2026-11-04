# =====================================================================
# ZONA GARAGEM — no MCU (192.168.1.26)
# ---------------------------------------------------------------------
# Zona HIBRIDA: Movimento e GPIO puro (evento). CO/CO2 NAO sao lidos
# por GPIO -- o CO Detector / CO2 Detector do PT sao "Smart Things"
# sem API programavel (doc oficial: Direct/Local/Remote Control: N/A,
# so reportam a um Registration Server/dashboard visual). A leitura
# real de gas usa o pacote `environment`, que le a concentracao
# AMBIENTE simulada diretamente -- CONFIRMADO empiricamente no PT.
#
# Old Car contribui ~1%/h de CO e ~2%/h de CO2 (doc oficial Cisco).
# Limiar de alarme = 20% (mesmo valor usado pelo CO Detector oficial).
#
# Portas fisicas usadas (MCU, D0-D5): so Motion, Porta, Fan, Alarme.
# CO/CO2 NAO ocupam porta fisica -- sobram D4-D5 livres na MCU.
#
# Cliente TCP: publica os estados no broker (192.168.1.100:1883) e
# recebe comandos casa/garagem/cmd/<atuador>.
#
# MODO_DEMO: a taxa real do Old Car (~1%/h CO, ~2%/h CO2) e lenta demais
# para uma demonstracao em aula. Em vez de escrever no Environment do PT
# (possivel com setContribution, ver diag_smoke.py), simulamos uma rampa LOCAL --
# sobe, dispara o alarme, desce (como se o exaustor limpasse o ar).
# Trocar MODO_DEMO para False usa o Environment.get() real (producao).
#
# A rampa so avanca se o Old Car estiver REALMENTE ligado -- detectado
# comparando a leitura real do Environment com a linha de base medida
# empiricamente no PT (desligado: CO=0.0017%, CO2=0.039% -- este ultimo
# bate com a concentracao real de CO2 na atmosfera). Sem fonte de gas
# real, a rampa desce ate zero em vez de subir sozinha.
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *
from environment import *

ZONA = "garagem"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

LIMIAR_GAS = 20  # % -- mesmo limiar do CO Detector oficial do PT

MODO_DEMO = True  # True = rampa sintetica p/ aula; False = ambiente real do PT
INCREMENTO_DEMO = 2.5  # % por chamada de verificar_gas() (a cada 2s)
TETO_DEMO = 30  # % onde a rampa inverte e comeca a "ventilar"

# Limiares p/ detectar o Old Car ligado, calibrados com medicoes reais no PT:
# desligado -> CO=0.0017%, CO2=0.039% | ligado (alguns min) -> CO=0.06%, CO2=0.157%
# Medido em 04/11/2026, com o clima de Sao Luis: ar limpo da 0, e o Old Car ligado
# deixa o CO perto de 0.008%, sem acumular.
LIMIAR_CO_LIGADO = 0.005  # % -- acima disso, ha uma fonte real de CO ativa
LIMIAR_CO2_LIGADO = 0.08  # % -- acima da linha de base atmosferica (~0.04%)

_co_demo = 0.0
_co2_demo = 0.0
_direcao_demo = 1  # 1 = subindo, -1 = descendo

# O Motion Sensor do PT volta a LOW sozinho em ~5s -- tempo curto demais
# para a Central perceber. Em vez de publicar o estado cru do sensor,
# "seguramos" movimento=1 por DURACAO_MOVIMENTO segundos no software.
DURACAO_MOVIMENTO = 10  # segundos que o movimento fica reportado como ativo
_mov_expira_em = 0  # uptime() em que o estado deve voltar a 0

# O Alarm soa por duas fontes possiveis: gas perigoso (sempre) OU
# movimento detectado enquanto a casa esta em modo viagem (ninguem
# esperado). _modo_viagem chega da Central via comando (cmd/modo).
_perigo_gas = False
_modo_viagem = False

# --- Portas (MCU: usar somente D0-D5) ---
MOV = 0  # D0: Motion Sensor   (digitalRead)
PORTA = 1  # D1: Garage Door     (customWrite)
FAN = 2  # D2: Fan / exaustao  (customWrite "0"/"1"/"2")
ALARME = 3  # D3: Alarm           (digitalWrite)
# D4, D5 livres para expansao futura

cliente = TCPClient()
_loops_sem_conexao = 0
_republicar = False  # conexao caiu: reenviar tudo ao voltar
anterior = {}  # ultimo valor publicado de cada grandeza


def log(msg):
    print("[{}] {}".format(ctime(), msg))


def reconectar():
    """Cada tentativa precisa de um TCPClient novo: no PT, repetir connect()
    no mesmo objeto nunca conecta, mesmo com a Central ja no ar (medido em
    03/11/2026). Sem isto, a zona que sobe antes da Central fica muda."""
    global cliente
    cliente.close()
    cliente = TCPClient()
    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)


def manter_conexao():
    """Reconecta ao broker se a conexao cair (ex.: broker reiniciado).
    Backport do padrao validado no RFID Reader / zona_sala.py."""
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
        reconectar()


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


def carro_ligado():
    """Detecta se ha uma fonte real de gas ativa (ex.: Old Car ligado),
    comparando a leitura REAL do ambiente com a linha de base medida
    empiricamente no PT (desligado: CO~0.0017%, CO2~0.039%)."""
    return (Environment.get("CO") >= LIMIAR_CO_LIGADO) or (
        Environment.get("CO2") >= LIMIAR_CO2_LIGADO
    )


def ler_gas():
    """Le CO/CO2. Em MODO_DEMO, simula uma rampa (sobe/dispara/desce)
    em vez do Environment.get() real -- pensado para demonstracao em
    aula, onde a taxa real do PT (~1%/h) e lenta demais. A rampa so
    avanca se o Old Car estiver realmente ligado; senao, desce."""
    global _co_demo, _co2_demo, _direcao_demo
    if not MODO_DEMO:
        return Environment.get("CO"), Environment.get("CO2")

    if not carro_ligado():
        # Sem fonte real de gas: dispersa (desce) em vez de subir sozinho
        _co_demo = max(0, _co_demo - INCREMENTO_DEMO)
        _co2_demo = max(0, _co2_demo - INCREMENTO_DEMO * 1.5)
        _direcao_demo = 1  # proxima vez que ligar, comeca subindo de novo
        return _co_demo, _co2_demo

    if _co_demo >= TETO_DEMO:
        _direcao_demo = -1  # comeca a "ventilar": nivel cai
    elif _co_demo <= 0:
        _direcao_demo = 1  # novo "vazamento": nivel volta a subir

    passo = _direcao_demo * INCREMENTO_DEMO
    _co_demo = max(0, min(_co_demo + passo, 100))
    _co2_demo = max(
        0, min(_co2_demo + passo * 1.5, 100)
    )  # CO2 sobe mais rapido, como no Old Car real
    return _co_demo, _co2_demo


def atualizar_alarme():
    """Consolida as duas fontes do Alarm: gas perigoso OU movimento
    durante o modo viagem. Chamado sempre que qualquer uma das duas
    condicoes muda, para elas nao se sobrescreverem."""
    movimento_ativo = _mov_expira_em != 0
    ligar = _perigo_gas or (movimento_ativo and _modo_viagem)
    digitalWrite(ALARME, HIGH if ligar else LOW)


def verificar_gas():
    """Le CO/CO2 (real ou demo) e aciona os atuadores. Chamado por polling."""
    global _perigo_gas
    co, co2 = ler_gas()
    perigo = (co >= LIMIAR_GAS) or (co2 >= LIMIAR_GAS)
    _perigo_gas = perigo

    # Atuadores locais (reacao imediata)
    # Fan e "Custom" no PT, nao "Digital": Message Format [state], onde
    # 0=off, 1=velocidade baixa, 2=velocidade alta (doc oficial do device).
    # Usamos velocidade alta no perigo, para exaustao maxima.
    customWrite(FAN, "2" if perigo else "0")
    atualizar_alarme()
    customWrite(PORTA, "1" if perigo else "0")  # abre p/ ventilar

    publicar_se_mudou("co", round(co, 2))
    publicar_se_mudou("co2", round(co2, 2))
    if perigo:
        log("GAS ALTO: CO={} CO2={}".format(co, co2))


def processar_movimento(*args):
    """Interrupcao GPIO: so reage quando o sensor VAI para HIGH. O
    retorno a LOW (que o PT faz sozinho em ~5s) e ignorado aqui --
    quem decide quando publicar movimento=0 e verificar_movimento(),
    apos DURACAO_MOVIMENTO segundos."""
    global _mov_expira_em
    if digitalRead(MOV) == HIGH:
        novo = _mov_expira_em == 0
        _mov_expira_em = uptime() + DURACAO_MOVIMENTO
        atualizar_alarme()  # em modo viagem, o alarme local soa na hora
        if novo:
            publicar_se_mudou("movimento", 1)
            log("Movimento detectado (mantido por {}s)".format(DURACAO_MOVIMENTO))


def verificar_movimento():
    """Encerra o estado de movimento apos DURACAO_MOVIMENTO segundos.
    Chamado por polling, junto com verificar_gas()."""
    global _mov_expira_em
    if _mov_expira_em and uptime() >= _mov_expira_em:
        _mov_expira_em = 0
        atualizar_alarme()  # desliga o alarme de movimento (gas continua valendo)
        publicar_se_mudou("movimento", 0)
        log("Movimento encerrado")


def reenviar_estado():
    """Recupera publicacao de movimento perdida com o broker fora do ar.
    Sem isto, um movimento=0 que falhou deixaria a Central presa em
    MOVIMENTO ou INTRUSAO. Em regime nao gera trafego: publicar_se_mudou
    so envia se o valor mudou ou se o envio anterior falhou."""
    if not cliente.connected():
        return  # sem broker nao adianta tentar, e o log viraria enxurrada
    publicar_se_mudou("movimento", 1 if _mov_expira_em else 0)


def ao_receber(data):
    """Comando vindo do broker: casa/garagem/cmd/<atuador> ou o
    broadcast de modo casa/todas/cmd/modo."""
    global _modo_viagem
    try:
        cmd = loads(data)
    except:
        return
    alvo = cmd.get("topic", "")
    v = cmd.get("payload", 0)
    if alvo.endswith("/cmd/fan"):
        customWrite(FAN, "2" if v else "0")  # Fan e Custom, nao Digital
    elif alvo.endswith("/cmd/porta"):
        customWrite(PORTA, "1" if v else "0")
    elif alvo.endswith("/cmd/alarme"):
        digitalWrite(ALARME, HIGH if v else LOW)  # override manual da Central
    elif alvo.endswith("/cmd/modo"):
        _modo_viagem = bool(v)
        atualizar_alarme()  # se ja havia movimento ativo, reavalia na hora
        log("Modo viagem = {}".format(_modo_viagem))


def setup():
    pinMode(MOV, IN)
    for p in [PORTA, FAN, ALARME]:
        pinMode(p, OUT)

    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)
    log("Garagem conectando ao broker {}".format(BROKER_IP))

    # Movimento e evento GPIO; gas exige polling (ver main())
    add_event_detect(MOV, processar_movimento)
    verificar_gas()


def main():
    setup()
    while True:
        manter_conexao()  # reconecta se o broker tiver reiniciado
        verificar_gas()  # ambiente nao gera evento -- checar periodicamente
        verificar_movimento()  # encerra o "movimento ativo" apos o prazo
        reenviar_estado()  # recupera publicacao perdida sem broker
        sleep(2)


if __name__ == "__main__":
    main()
