# =====================================================================
# ZONA PERIMETRO — no MCU (192.168.1.21)
# ---------------------------------------------------------------------
# Zona 100% digital/custom (cabe folgada nas 6 portas D0-D5 da MCU).
# Baseada no padrao ja validado em zona_garagem.py (TCP + hold de estado).
#
# Camera liga em QUALQUER movimento (monitoramento, como no V3).
# Sirene so soa se houver movimento E a casa estiver em modo_viagem --
# mesma logica ja validada no Alarm da Garagem, evita disparo falso
# no dia a dia. modo_viagem chega via broadcast casa/todas/cmd/modo.
#
# RFID Reader NAO E GPIO (doc do device: Direct/Local/Remote Control
# N/A) -- por isso NAO aparece nas portas abaixo. Mas ele foi
# REABILITADO como no de rede independente: o script embutido dele
# (src/thing_rfid_reader.py, aba Programming do proprio Thing) publica
# casa/perimetro/rfid direto no broker via tcp. A Porta desta zona
# abre por comando remoto (cmd/porta) -- ex.: a Central pode abri-la
# ao receber um cartao valido.
#
# VALIDADO 100% NO PT 9.0.0 (02/07/2026): conexao, broadcast de modo,
# campainha (hold 8s), fluxo RFID completo (Card -> Reader -> broker ->
# whitelist -> cmd/porta -> Door abre/fecha em 5s), Camera ligando em
# movimento e Siren soando em movimento+modo_viagem. Siren e Camera
# confirmados como Custom com "0"/"1" (liga/desliga).
# Push Button da campainha e momentaneo (dispara ao apertar E soltar),
# tratado igual ao Motion da Garagem (hold + so reage a HIGH).
# =====================================================================

from gpio import *
from time import *
from tcp import *
from json import *

ZONA = "perimetro"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883

# --- Portas (MCU: usar somente D0-D5) ---
MOV = 0  # D0: Motion Sensor            (digitalRead)
CAMPAINHA = 1  # D1: Push Button (campainha)  (digitalRead)
PORTA = 2  # D2: Door                     (customWrite)
SIRENE = 3  # D3: Siren                    (customWrite)
CAMERA = 4  # D4: Camera                   (customWrite)
# D5 livre para expansao futura

DURACAO_MOVIMENTO = 10  # segundos que "movimento" fica reportado ativo
DURACAO_CAMPAINHA = 8  # segundos que "campainha" fica reportada tocada

_mov_expira_em = 0
_campainha_expira_em = 0
_modo_viagem = False  # recebido via broadcast da Central (cmd/modo)
_seguranca_anterior = (None, None)  # (camera, sirene) -- so loga quando muda

cliente = TCPClient()
_loops_sem_conexao = 0
_republicar = False  # conexao caiu: reenviar tudo ao voltar
anterior = {}  # ultimo valor publicado de cada grandeza


def log(msg):
    print("[{}] {}".format(ctime(), msg))


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
        cliente.connect(BROKER_IP, BROKER_PORT)


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


def atualizar_seguranca():
    """Camera liga em qualquer movimento (monitoramento). Sirene so
    soa se houver movimento ATIVO e a casa estiver em modo viagem.

    Loga a mudanca de estado dos dois atuadores: no simulador o unico
    retorno visivel e a cor do icone, que some da tela quando a janela
    do terminal esta aberta. Sem esta linha, "a sirene nao tocou" e
    "a sirene tocou e eu nao vi" ficam indistinguiveis na bancada."""
    global _seguranca_anterior
    movimento_ativo = _mov_expira_em != 0
    camera = movimento_ativo
    sirene = movimento_ativo and _modo_viagem
    customWrite(CAMERA, "1" if camera else "0")
    customWrite(SIRENE, "1" if sirene else "0")
    if (camera, sirene) != _seguranca_anterior:
        _seguranca_anterior = (camera, sirene)
        log(
            "Camera {} | Sirene {}".format(
                "LIGADA" if camera else "desligada",
                "LIGADA" if sirene else "desligada",
            )
        )


def processar_movimento(*args):
    """So reage a transicao para HIGH; o retorno a LOW (que o PT faz
    sozinho) e ignorado -- verificar_movimento() decide quando encerrar."""
    global _mov_expira_em
    if digitalRead(MOV) == HIGH:
        novo = _mov_expira_em == 0
        _mov_expira_em = uptime() + DURACAO_MOVIMENTO
        atualizar_seguranca()
        if novo:
            publicar_se_mudou("movimento", 1)
            log("Movimento detectado (mantido por {}s)".format(DURACAO_MOVIMENTO))


def verificar_movimento():
    """Encerra o estado de movimento apos DURACAO_MOVIMENTO segundos."""
    global _mov_expira_em
    if _mov_expira_em and uptime() >= _mov_expira_em:
        _mov_expira_em = 0
        atualizar_seguranca()
        publicar_se_mudou("movimento", 0)
        log("Movimento encerrado")


def processar_campainha(*args):
    """Push Button e momentaneo (dispara ao apertar E soltar) -- so
    reage a HIGH, igual ao botao de modo da Central."""
    global _campainha_expira_em
    if digitalRead(CAMPAINHA) == HIGH:
        novo = _campainha_expira_em == 0
        _campainha_expira_em = uptime() + DURACAO_CAMPAINHA
        if novo:
            publicar_se_mudou("campainha", 1)
            log("Campainha tocada (visivel por {}s)".format(DURACAO_CAMPAINHA))


def verificar_campainha():
    """Encerra o estado de campainha apos DURACAO_CAMPAINHA segundos."""
    global _campainha_expira_em
    if _campainha_expira_em and uptime() >= _campainha_expira_em:
        _campainha_expira_em = 0
        publicar_se_mudou("campainha", 0)
        log("Campainha encerrada")


def reenviar_estado():
    """Reenvia o estado atual a cada ciclo. Como esta zona so publica em
    evento, uma publicacao perdida (broker fora do ar naquele instante)
    ficaria perdida para sempre -- e a Central seguiria mostrando
    campainha tocando ou movimento ativo indefinidamente, com o Home
    Speaker ligado. O publicar_se_mudou so poe no fio quando o valor
    mudou OU quando o envio anterior falhou, entao em regime isto nao
    gera trafego nenhum."""
    if not cliente.connected():
        return  # sem broker nao adianta tentar, e o log viraria enxurrada
    publicar_se_mudou("movimento", 1 if _mov_expira_em else 0)
    publicar_se_mudou("campainha", 1 if _campainha_expira_em else 0)


def ao_receber(data):
    """Comando vindo do broker: casa/perimetro/cmd/<atuador> ou o
    broadcast de modo casa/todas/cmd/modo."""
    global _modo_viagem
    try:
        cmd = loads(data)
    except:
        return
    alvo = cmd.get("topic", "")
    v = cmd.get("payload", 0)
    if alvo.endswith("/cmd/porta"):
        customWrite(PORTA, "1" if v else "0")  # abertura remota (RFID/Central)
        log("Comando recebido: porta = {}".format(v))
    elif alvo.endswith("/cmd/sirene"):
        customWrite(SIRENE, "1" if v else "0")
        log("Comando recebido: sirene = {}".format(v))
    elif alvo.endswith("/cmd/camera"):
        customWrite(CAMERA, "1" if v else "0")
        log("Comando recebido: camera = {}".format(v))
    elif alvo.endswith("/cmd/modo"):
        _modo_viagem = bool(v)
        atualizar_seguranca()  # se ja havia movimento ativo, reavalia na hora
        log("Modo viagem = {}".format(_modo_viagem))


def setup():
    pinMode(MOV, IN)
    pinMode(CAMPAINHA, IN)
    for p in [PORTA, SIRENE, CAMERA]:
        pinMode(p, OUT)

    cliente.onReceive(ao_receber)
    cliente.connect(BROKER_IP, BROKER_PORT)
    log("Perimetro conectando ao broker {}".format(BROKER_IP))

    add_event_detect(MOV, processar_movimento)
    add_event_detect(CAMPAINHA, processar_campainha)
    atualizar_seguranca()


def main():
    setup()
    while True:
        manter_conexao()  # reconecta se o broker tiver reiniciado
        verificar_movimento()
        verificar_campainha()
        reenviar_estado()  # recupera publicacao perdida sem broker
        sleep(2)


if __name__ == "__main__":
    main()
