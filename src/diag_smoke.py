# =====================================================================
# DIAGNOSTICO SMOKE (Cozinha) — script temporario de depuracao
# ---------------------------------------------------------------------
# Objetivo: descobrir com que ID o pacote `environment` expoe a FUMACA
# no PT 9, porque o zona_cozinha.py depende de Environment.get("Smoke")
# e esse nome nunca foi confirmado no simulador. O CO ja esta confirmado
# ("CO", float em %), entao ele entra aqui so como controle: se o CO
# responde e a fumaca nao, o problema e o ID, nao o pacote.
#
# Este script NAO substitui o diag_environment.py — aquele testa as
# assinaturas do metodo com CO/CO2; este varre nomes de grandeza.
#
# Como usar:
#   1. Cole num SBC qualquer da topologia e Run.
#   2. Leia a primeira rodada: o nome que imprimir um numero >= 0 e o ID
#      valido. O que devolver -1 nao existe e aparece como FALHOU.
#   3. Se algum ID valer, o script passa a injetar fumaca nele para o
#      valor sair do zero dentro da sessao (ver INJETAR abaixo).
#
# Por que injetar: a emissao natural do Old Car e de ~3%/hora de tempo
# simulado. Numa bancada de duas horas o valor mal sai do lugar, e daria
# para concluir errado que a leitura nao funciona. O setContribution faz
# o ambiente subir num ritmo que da para ver.
#
# A injecao segue o formato do script embutido do Heating Element: chamada
# repetida a cada segundo, com o quarto argumento True.
#
# MEDIDO em 03/11/2026 (PT 9.0.1.0858, escala 1:30): a fumaca NAO acumula. Ela
# estabiliza em taxa x 30, e por isso 0.25 ficou parada em 7.5%.
# Um ID inexistente NAO levanta excecao: Environment.get() devolve -1.
# =====================================================================

from environment import *
from time import *

# Nomes candidatos para a fumaca, do mais provavel ao menos.
CANDIDATOS = ["Smoke", "Smoke Detector", "smoke", "SMOKE", "Fire", "Fire Smoke"]

CONTROLE = "CO"  # ja confirmado: serve para provar que o pacote responde

INJETAR = True  # False = so le, nao mexe no ambiente
TAXA = 1.0  # a fumaca estabiliza em taxa x 30: 1.0 da 30%, acima do limiar de 20%
LIMITE_API = 1.0e6  # 3o argumento, com o mesmo valor do Heating Element
TETO = 40.0  # % em que este script para de injetar
INTERVALO = 1  # segundos entre ciclos (a contribuicao e renovada em cada um)


def ler(nome):
    """Tenta ler uma grandeza. Devolve (deu_certo, valor_ou_erro)."""
    try:
        valor = Environment.get(nome)
    except Exception as erro:
        return False, erro
    if valor < 0:  # o PT devolve -1 para um ID que nao existe
        return False, "ID inexistente ({})".format(valor)
    return True, valor


def descobrir_id():
    """Varre os candidatos e devolve o primeiro que responder."""
    print("=== procurando o ID da fumaca ===")

    ok, valor = ler(CONTROLE)
    if ok:
        print("controle {} = {} (o pacote responde)".format(CONTROLE, valor))
    else:
        print("ATENCAO: nem o {} respondeu ({}).".format(CONTROLE, valor))
        print("Se isso acontecer, o problema nao e o nome da grandeza.")

    encontrado = None
    for nome in CANDIDATOS:
        ok, valor = ler(nome)
        if ok:
            print("  OK     {} = {}".format(nome, valor))
            if encontrado is None:
                encontrado = nome
        else:
            print("  FALHOU {} -> {}".format(nome, valor))

    if encontrado:
        print(">>> ID valido: {}".format(encontrado))
    else:
        print(">>> Nenhum candidato respondeu.")
        print(
            ">>> A Cozinha passa a depender so do CO -- anotar e decidir fora da bancada."
        )
    return encontrado


def injetar(nome, taxa):
    """Renova a contribuicao no ambiente. Devolve False se a chamada falhar."""
    try:
        Environment.setContribution(nome, taxa, LIMITE_API, True)
        return True
    except Exception as erro:
        print("setContribution falhou: {}".format(erro))
        return False


def acompanhar(nome):
    """Imprime a leitura a cada ciclo e injeta ate o TETO."""
    print("=== acompanhando {} (Stop para encerrar) ===".format(nome))
    injetando = INJETAR
    while True:
        ok, valor = ler(nome)
        _, controle = ler(CONTROLE)
        if ok:
            print("{} = {}   |   {} = {}".format(nome, valor, CONTROLE, controle))
            if injetando:
                injetando = injetar(nome, TAXA if valor < TETO else 0.0)
        else:
            print("leitura falhou: {}".format(valor))
        sleep(INTERVALO)


def main():
    nome = descobrir_id()
    if not nome:
        return  # sem ID nao ha o que acompanhar; a conclusao ja foi impressa
    acompanhar(nome)


if __name__ == "__main__":
    main()
