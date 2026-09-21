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
#   2. Leia a primeira rodada: o nome que imprimir um numero (mesmo 0.0)
#      e o ID valido. O que falhar levanta excecao e aparece como FALHOU.
#   3. Se algum ID valer, o script passa a injetar fumaca nele para o
#      valor sair do zero dentro da sessao (ver INJETAR abaixo).
#
# Por que injetar: a emissao natural do Old Car e de ~3%/hora de tempo
# simulado. Numa bancada de duas horas o valor mal sai do lugar, e daria
# para concluir errado que a leitura nao funciona. O setContribution faz
# o ambiente subir num ritmo que da para ver.
# =====================================================================

from environment import *
from time import *

# Nomes candidatos para a fumaca, do mais provavel ao menos.
CANDIDATOS = ["Smoke", "Smoke Detector", "smoke", "SMOKE", "Fire", "Fire Smoke"]

CONTROLE = "CO"  # ja confirmado: serve para provar que o pacote responde

INJETAR = True  # False = so le, nao mexe no ambiente
TAXA = 30.0  # unidades por hora simulada injetadas no ID que funcionar
LIMITE = 80.0  # teto da injecao, em %
INTERVALO = 3  # segundos entre leituras


def ler(nome):
    """Tenta ler uma grandeza. Devolve (deu_certo, valor_ou_erro)."""
    try:
        return True, Environment.get(nome)
    except Exception as erro:
        return False, erro


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


def injetar(nome):
    """Faz o ambiente subir rapido o bastante para o teste andar.

    A assinatura do setContribution varia entre versoes do PT, entao
    tentamos as formas conhecidas e ficamos com a que nao levantar erro."""
    tentativas = (
        (
            "setContribution(id, taxa, limite)",
            lambda: Environment.setContribution(nome, TAXA, LIMITE),
        ),
        (
            "setContribution(id, taxa, limite, True)",
            lambda: Environment.setContribution(nome, TAXA, LIMITE, True),
        ),
        ("setContribution(id, taxa)", lambda: Environment.setContribution(nome, TAXA)),
    )
    for rotulo, chamada in tentativas:
        try:
            chamada()
            print(
                "Injecao ativa via {} -- taxa {}/h, limite {}".format(
                    rotulo, TAXA, LIMITE
                )
            )
            return True
        except Exception as erro:
            print("  {} nao serviu: {}".format(rotulo, erro))
    print(
        "Nenhuma forma de setContribution funcionou: o valor vai subir no ritmo natural."
    )
    return False


def acompanhar(nome):
    """Imprime a leitura a cada ciclo, para ver o valor se mover."""
    print("=== acompanhando {} (Ctrl+C ou Stop para encerrar) ===".format(nome))
    while True:
        ok, valor = ler(nome)
        _, controle = ler(CONTROLE)
        if ok:
            print("{} = {}   |   {} = {}".format(nome, valor, CONTROLE, controle))
        else:
            print("leitura falhou: {}".format(valor))
        sleep(INTERVALO)


def main():
    nome = descobrir_id()
    if not nome:
        return  # sem ID nao ha o que acompanhar; a conclusao ja foi impressa
    if INJETAR:
        injetar(nome)
    acompanhar(nome)


if __name__ == "__main__":
    main()
