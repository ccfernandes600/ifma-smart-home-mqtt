# =====================================================================
# DIAGNOSTICO ENVIRONMENT (Garagem) — script temporario de depuracao
# ---------------------------------------------------------------------
# Objetivo: descobrir a forma correta de ler o nivel de CO/CO2 ambiente
# via o pacote `environment`, sem depender do device "CO Detector"
# (que e um Smart Thing sem API programavel).
#
# IDs confirmados pela doc oficial da Cisco: "CO" e "CO2".
# Testa varias assinaturas possiveis do metodo, sem travar se alguma
# nao existir nesta versao do PT.
#
# Como usar: cole na Garagem (MCU ou SBC), Run, e observe qual das
# chamadas funciona e qual valor aparece. Ligue o Old Car e deixe
# rodando — o nivel sobe DEVAGAR (~1%/hora para CO), entao pode nao
# mudar muito num teste curto.
# =====================================================================

from environment import *
from time import *


def testar(nome, chamada):
    try:
        resultado = chamada()
        print("{} = {}".format(nome, resultado))
    except Exception as e:
        print("{} FALHOU: {}".format(nome, e))


def main():
    print("=== DIAG ENVIRONMENT INICIADO ===")
    while True:
        testar("Environment.get('CO')", lambda: Environment.get("CO"))
        testar("Environment.get('CO2')", lambda: Environment.get("CO2"))
        testar(
            "Environment.getMetricValue('CO')", lambda: Environment.getMetricValue("CO")
        )
        testar(
            "Environment.getValueWithUnit('CO')",
            lambda: Environment.getValueWithUnit("CO"),
        )
        testar("Environment.getUnit('CO')", lambda: Environment.getUnit("CO"))
        testar("Environment.getTimeInSeconds()", lambda: Environment.getTimeInSeconds())
        print("---")
        sleep(3)


if __name__ == "__main__":
    main()
