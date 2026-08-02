# =====================================================================
# DIAGNOSTICO GARAGEM (MCU) — script temporario de depuracao
# ---------------------------------------------------------------------
# Objetivo: isolar o GPIO da rede para descobrir por que "nada acontece".
# - NAO usa tcp (se o problema for a rede na MCU, este script roda mesmo assim)
# - NAO usa add_event_detect (usa polling: le a cada 2s)
# - Imprime a leitura DIGITAL e ANALOGICA de cada sensor, para revelar
#   se o CO/CO2/Movimento respondem por digitalRead ou analogRead.
#
# Como usar: cole no lugar do zona_garagem.py, clique Run e acione o
# Old Car / sensor de movimento observando o console.
# =====================================================================

from gpio import *
from time import *

CO = 0  # D0
CO2 = 1  # D1
MOV = 2  # D2


def setup():
    for p in [CO, CO2, MOV]:
        pinMode(p, IN)
    print("=== DIAG INICIADO ===")


def main():
    setup()
    while True:
        print(
            "digital -> CO={} CO2={} MOV={}".format(
                digitalRead(CO), digitalRead(CO2), digitalRead(MOV)
            )
        )
        print(
            "analog  -> CO={} CO2={} MOV={}".format(
                analogRead(CO), analogRead(CO2), analogRead(MOV)
            )
        )
        print("---")
        sleep(2)


if __name__ == "__main__":
    main()
