# =====================================================================
# DIAGNOSTICO RFID — script temporario de depuracao
# ---------------------------------------------------------------------
# Objetivo: descobrir POR QUE aproximar o Card nao produz leitura. O
# thing_rfid_reader.py depende de duas coisas que falham em silencio:
#
#   1. devicesAt() enxergar o Card. A proximidade e medida no PHYSICAL
#      WORKSPACE, nao na tela logica -- arrastar o Card para perto do
#      leitor no diagrama logico nao muda a posicao fisica dele, e o
#      leitor continua sozinho no raio de leitura.
#   2. getDeviceProperty(nome, "CardID") devolver algo. Card sem o
#      CARD_ID definido no script JS dele responde vazio, e o Reader
#      descarta a leitura como invalida (e certo: e assim que ele
#      ignora o proprio switch e os vizinhos que nao sao cartao).
#
# Este script nao publica nada e nao usa rede: so imprime o que o
# leitor enxerga, a cada ciclo. Se a lista vier vazia, o problema e
# posicao; se vier com o Card mas CardID vazio, o problema e o Card.
#
# Como usar:
#   1. No RFID Reader: Programming -> New -> "Empty - Python"
#      (assim o thing_rfid_reader.py continua guardado no nó)
#   2. Colar este arquivo e Run.
#   3. Aproximar o Card no PHYSICAL WORKSPACE e acompanhar a saida.
#   4. Ao terminar, Stop e voltar a rodar o thing_rfid_reader.py.
# =====================================================================

from time import *
from physical import *

INTERVALO = 2000  # ms entre varreduras

# Raio de leitura. O thing_rfid_reader.py usa 50 x 50; aqui comeca
# maior de proposito, para separar "o Card esta longe" de "o Card nao
# existe para o leitor". Se ele so aparecer com raio grande, a correcao
# e aproximar no physical, nao aumentar o raio do script de producao.
RAIO_X = 200
RAIO_Y = 200

RAIO_PRODUCAO = 50  # o que o script real usa, para comparar


def distancia_ok(x, y):
    """Diz se o vizinho cairia tambem dentro do raio de producao."""
    return abs(x) <= RAIO_PRODUCAO and abs(y) <= RAIO_PRODUCAO


def varrer():
    """Imprime todos os vizinhos e o CardID de cada um."""
    cx = getCenterX()
    cy = getCenterY()
    # devicesAt() neste motor devolve um DICT {'0': 'NomeDevice', ...}:
    # as chaves sao indices em string e os VALORES sao os nomes.
    vizinhos = devicesAt(cx, cy, RAIO_X, RAIO_Y)

    encontrados = 0
    for chave in vizinhos:
        nome = vizinhos[chave]
        if nome == getName():
            continue  # o proprio leitor sempre aparece na lista
        encontrados += 1
        try:
            cartao = getDeviceProperty(nome, "CardID")
        except Exception as erro:
            cartao = "ERRO: {}".format(erro)
        print("  vizinho: {} | CardID = {}".format(nome, cartao))

    if encontrados == 0:
        print(
            "  nenhum vizinho no raio {}x{} -- o Card esta longe no physical".format(
                RAIO_X, RAIO_Y
            )
        )


def main():
    print("=== diagnostico RFID ===")
    print("Leitor: {}".format(getName()))
    print("Centro: x={} y={}".format(getCenterX(), getCenterY()))
    print("Varrendo raio {}x{} (producao usa {})".format(RAIO_X, RAIO_Y, RAIO_PRODUCAO))
    print("Aproxime o Card no Physical Workspace e acompanhe.")
    while True:
        varrer()
        delay(INTERVALO)
        idle()


if __name__ == "__main__":
    main()
