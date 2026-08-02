# =====================================================================
# DIAGNOSTICO TIME MULTIPLIER — script temporario de depuracao
# ---------------------------------------------------------------------
# Objetivo: descobrir se e possivel acelerar a simulacao ambiental
# (CO/CO2 sobem so ~1-2%/hora, lento demais para testar em aula).
#
# Testa Environment.setTimeMultiplier() — metodo confirmado na API
# C++ do PT, mas AINDA NAO confirmado no pacote Python `environment`.
#
# Como usar: cole na Garagem, Run, e compare a subida do CO em ~30s
# com o teste anterior (diag_environment.py). Se o valor subir bem
# mais rapido que antes, o multiplicador funcionou.
# =====================================================================

from environment import *
from time import *


def testar(nome, chamada):
    try:
        resultado = chamada()
        print("{} = {}".format(nome, resultado))
        return True
    except Exception as e:
        print("{} FALHOU: {}".format(nome, e))
        return False


def main():
    print("=== DIAG TIME MULTIPLIER INICIADO ===")

    # Tenta acelerar a simulacao 60x (1 seg real = 1 min simulado)
    testar(
        "Environment.setTimeMultiplier(60)", lambda: Environment.setTimeMultiplier(60)
    )

    inicio = Environment.getMetricValue("CO")
    print("CO inicial = {}".format(inicio))

    while True:
        atual = testar("Environment.get('CO')", lambda: Environment.get("CO"))
        print("---")
        sleep(3)


if __name__ == "__main__":
    main()
