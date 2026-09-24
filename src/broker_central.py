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
from http import *

# --- Portas do proprio SBC Central ---
BTN_MODO = 0  # D0: Push Button (alterna modo casa/viagem)
LCD_MESTRE = 1  # D1: LCD mestre (2 linhas)
SPEAKER = 2  # D2: Home Speaker (avisos sonoros)

PORTA_BROKER = 1883
PORTA_WEB = 80  # painel HTTP servido pela propria Central

# --- Painel web ---------------------------------------------------------
# Rotulo e unidade de cada grandeza publicada pelas zonas. O que nao
# estiver aqui aparece com o nome cru do topico -- zona nova nao quebra
# o painel, so entra sem rotulo bonito.
GRANDEZAS = {
    "temp": ("Temperatura", " C"),
    "umidade": ("Umidade", " %"),
    "luz": ("Luminosidade", ""),
    "co": ("CO", " %"),
    "co2": ("CO2", " %"),
    "fumaca": ("Fumaca", " %"),
    "agua": ("Nivel de agua", ""),
    "vento": ("Vento", ""),
    "pressao": ("Pressao", ""),
    "movimento": ("Movimento", ""),
    "campainha": ("Campainha", ""),
    "rfid": ("Ultimo cartao", ""),
}
BINARIAS = ("movimento", "campainha")  # 0/1 viram texto, nao numero
ATUALIZA_EM = 5  # segundos entre recargas automaticas da pagina

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


def situacao_da_casa():
    """Classifica o estado da casa UMA vez, para o LCD e o painel web
    nunca discordarem. Devolve (linha1, linha2, titulo_web, cor, som).

    Antes disto o calculo de gas estava escrito duas vezes -- aqui e no
    painel -- e a faixa do painel nao conhecia a intrusao: o LCD podia
    gritar INTRUSAO! enquanto a tela seguia azul de modo viagem.

    As duas primeiras linhas cabem em 14 caracteres: o LCD do PT corta o
    excedente sem avisar (bancada de 23/09, "Casa monitorada" virou
    "Casa monitorad"). Texto novo aqui: contar antes de escrever."""
    # Gas/fumaca so conta como perigo a partir do mesmo limiar usado nas
    # zonas (LIMIAR_GAS) -- nao basta ser != 0, senao alerta cedo demais
    gas = (
        estado.get("casa/garagem/co", 0) >= LIMIAR_GAS
        or estado.get("casa/garagem/co2", 0) >= LIMIAR_GAS
        or estado.get("casa/cozinha/co", 0) >= LIMIAR_GAS
        or estado.get("casa/cozinha/fumaca", 0) >= LIMIAR_GAS
    )
    campainha = estado.get("casa/perimetro/campainha", 0)
    # ONDE houve movimento importa mais que ter havido: a linha 2 do LCD
    # e a unica pista de para onde a pessoa deve olhar.
    if estado.get("casa/garagem/movimento", 0):
        onde = "Na garagem"
    elif estado.get("casa/perimetro/movimento", 0):
        onde = "No portao"
    else:
        onde = ""

    som = bool(gas or campainha)  # o que merece acordar o Home Speaker

    if gas:
        return "ALERTA DE GAS", "Verifique casa", "ALERTA DE GAS", "#c62828", som
    if onde and modo_viagem:  # movimento + ninguem esperado em casa
        return "INTRUSAO!", onde, "INTRUSAO " + onde.upper(), "#b71c1c", som
    if campainha:
        return "VISITANTE", "Campainha", "VISITANTE NA PORTA", "#ef6c00", som
    if onde:
        return "MOVIMENTO", onde, "MOVIMENTO " + onde.upper(), "#ef6c00", som
    if modo_viagem:
        return "MODO VIAGEM", "Monitorando", "MODO VIAGEM", "#1565c0", som
    return "CASA OK", "Modo normal", "CASA OK", "#0b7a3b", som


def avaliar_regras():
    """O 'cerebro' da casa: decisoes que dependem de varias zonas."""
    linha1, linha2, _titulo, _cor, som = situacao_da_casa()
    digitalWrite(SPEAKER, HIGH if som else LOW)
    if (linha1, linha2) != _ultima_tela:  # so escreve/loga quando muda
        mostrar(linha1, linha2)


def formatar(grandeza, valor):
    """Valor pronto para leitura humana: binario vira palavra, o resto
    ganha a unidade da grandeza."""
    rotulo, unidade = GRANDEZAS.get(grandeza, (grandeza, ""))
    if grandeza in BINARIAS:
        return rotulo, ("SIM" if valor else "nao")
    return rotulo, "{}{}".format(valor, unidade)


def linhas_por_zona():
    """Agrupa o estado por zona: {"sala": [("Temperatura", "24 C"), ...]}.

    Le o mesmo dicionario que as regras usam, entao o painel nunca mostra
    um valor diferente do que a Central decidiu -- nao ha segunda copia
    do estado para sair de sincronia."""
    zonas = {}
    for topico in estado:
        partes = topico.split("/")
        if len(partes) != 3:
            continue  # comando ou topico fora do padrao casa/<zona>/<grandeza>
        zona, grandeza = partes[1], partes[2]
        rotulo, texto = formatar(grandeza, estado[topico])
        zonas.setdefault(zona, []).append((rotulo, texto))
    return zonas


def pagina_painel():
    """Monta o HTML do painel a partir do estado atual.

    Layout em tabela e CSS enxuto de proposito: o navegador do Packet
    Tracer renderiza isso com folga, e a pagina e montada dentro do laco
    do SBC -- string grande custa tempo que o broker precisa."""
    _l1, _l2, situacao, cor, _som = situacao_da_casa()

    p = []
    p.append("<html><head><meta charset='utf-8'>")
    p.append("<meta http-equiv='refresh' content='{}'>".format(ATUALIZA_EM))
    p.append("<title>Casa Inteligente - Central</title><style>")
    p.append("body{font-family:Arial;background:#f4f6f5;color:#101010;margin:0;padding:18px}")
    p.append("h1{font-size:20px;margin:0}")
    p.append(".faixa{background:%s;color:#fff;padding:14px 18px;border-radius:6px}" % cor)
    p.append(".faixa p{margin:6px 0 0;font-size:13px}")
    p.append("table{border-collapse:collapse;width:100%;margin-top:14px;background:#fff}")
    p.append("caption{text-align:left;font-weight:bold;padding:10px 8px;background:#e8efeb}")
    p.append("td{border:1px solid #cfe7d7;padding:7px 10px;font-size:14px}")
    p.append("td.v{text-align:right;font-weight:bold;width:30%}")
    p.append("footer{margin-top:16px;font-size:12px;color:#5b6b63}")
    p.append("</style></head><body>")
    p.append("<div class='faixa'><h1>{}</h1>".format(situacao))
    zonas = linhas_por_zona()
    # Dois numeros diferentes de proposito: conectado e quem abriu a conexao
    # (zonas + o RFID Reader); publicando e quem ja mandou algum valor. Zona
    # de eventos, como o Perimetro, fica conectada sem publicar nada.
    p.append("<p>Modo: {} &middot; conectados: {} &middot; publicando: {} &middot; atualiza a cada {}s</p></div>".format(
        "viagem" if modo_viagem else "casa", len(clientes), len(zonas), ATUALIZA_EM))

    if not zonas:
        p.append("<p>Nenhuma publicacao recebida ainda.</p>")
    for zona in sorted(zonas):
        p.append("<table><caption>{}</caption>".format(zona.upper()))
        for rotulo, texto in sorted(zonas[zona]):
            p.append("<tr><td>{}</td><td class='v'>{}</td></tr>".format(rotulo, texto))
        p.append("</table>")

    p.append("<footer>Central 192.168.1.100 &middot; broker na porta {} &middot; ".format(PORTA_BROKER))
    p.append("dados brutos em <b>/estado</b></footer></body></html>")
    return "".join(p)


def rota_painel(url, response):
    response.setContentType("text/html")
    response.send(pagina_painel())


def rota_estado(url, response):
    """Mesma informacao em JSON, para conferir valor por valor sem depender
    do layout -- util quando a duvida e 'a Central recebeu ou nao?'."""
    response.setContentType("application/json")
    response.send(dumps(estado))


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
            mostrar("ACESSO OK", "Cartao {}".format(tag_num))
    else:
        mostrar("CARTAO NEGADO", "ID {}".format(tag_num))


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


def limpar_clientes():
    """Tira da lista quem ja desconectou.

    Sem isso a lista so cresce: cada Run de uma zona abre uma conexao nova
    e a antiga fica ali, fazendo o painel anunciar mais zonas do que
    existem de fato. Chamado a cada ciclo do main()."""
    vivos = [c for c in clientes if c.connected()]
    if len(vivos) != len(clientes):
        log("Conexoes encerradas removidas: {} -> {}".format(len(clientes), len(vivos)))
        clientes[:] = vivos


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

    # Painel web na mesma placa: a Central ja tem o estado completo, entao
    # servir daqui evita replicar dado e nao exige fan-out para um no web.
    HTTPServer.route("/", rota_painel)
    HTTPServer.route("/estado", rota_estado)
    HTTPServer.start(PORTA_WEB)
    log("Painel web em http://192.168.1.100:{}".format(PORTA_WEB))
    avaliar_regras()


def main():
    setup()
    while True:
        limpar_clientes()  # mantem a contagem do painel honesta
        verificar_porta_rfid()  # fecha a porta do perimetro apos o prazo
        sleep(1)


if __name__ == "__main__":
    main()
