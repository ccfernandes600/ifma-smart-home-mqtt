# =====================================================================
# DIAGNOSTICO TEMPERATURA — script temporario de depuracao
# ---------------------------------------------------------------------
# Por que existe: na bancada de 24/09 a umidade batia com o painel
# Environments e a temperatura nao. Tres explicacoes possiveis, e este
# script separa as tres numa rodada so.
#
#   H1  LIMITE DE TAXA. No XML do ambiente, so Ambient Temperature tem
#       MIN_RATE/MAX_RATE = +-0.00138889 por segundo, que da 5 C por
#       hora simulada. Todas as outras grandezas saem com +-1000, que e
#       instantaneo. Se o comodo comecou longe da curva, ele RAMPA ate
#       chegar -- e todo valor lido no meio do caminho esta "errado" por
#       estar em transito.
#       ASSINATURA: a coluna C/h fica colada em +5.0 ou -5.0.
#
#   H2  CONTEINER ERRADO. Conteiner aninhado nasce de outro template e
#       roda o clima generico da Cisco, nao o de Sao Luis.
#       ASSINATURA: a coluna C/h fica perto de 0 e o valor esta parado
#       num numero que a curva de Sao Luis nunca produz.
#
#   H3  SENSOR x AMBIENTE. O script da zona le por analogRead (GPIO) e o
#       painel mostra Ambient Temperature. Se os dois discordarem, o
#       problema nao e o clima: e o caminho da leitura.
#       ASSINATURA: as colunas SENSOR e AMBIENTE divergem.
#
#   H4  EFEITO RESIDUAL DOS ATUADORES. O AC vence o limite da curva (medido
#       em 23/09: -3,31 C/min real) e a divergencia apareceu depois de ele
#       funcionar. Hipotese da revisao de 03/11, nao provada.
#       ATENCAO: a recuperacao depois do AC tambem da C/h em +5, igual a H1.
#       Para separar: rodar num conteiner SEM atuadores e depois no da Sala.
#
# Como usar: cole no MESMO no da zona que esta sob teste (na Sala,
# D0 = Temperature Sensor), Run, e deixe rodando uns 3 minutos. Se
# quiser acelerar, ligue o multiplicador de tempo do simulador -- a
# coluna C/h e calculada sobre o RELOGIO SIMULADO, entao continua valida.
#
# Ao terminar o diagnostico, apague este arquivo do no.
# =====================================================================

from gpio import *
from time import *
from environment import *

PINO_TEMP = 0  # D0 -- ajuste se o sensor estiver em outra porta
INTERVALO = 5  # segundos reais entre amostras

# IDs a tentar no pacote environment. O primeiro que responder vira o
# oficial da rodada -- os outros ficam so para o caso de esta build do
# PT usar outro nome.
IDS = ["Ambient Temperature", "Temperature", "Ambient Temp"]

_id_bom = None
_anterior = None  # (segundos_simulados, celsius_ambiente)


def para_celsius(raw):
    """Mesma formula da zona: raw 0-1023 -> -100..+100 C."""
    return -100.0 + (raw / 1023.0) * 200.0


def ler_ambiente():
    """Devolve (id_usado, valor) ou (None, None) se nenhum ID responder."""
    global _id_bom
    tentativas = [_id_bom] if _id_bom else IDS
    for nome in tentativas:
        try:
            valor = Environment.get(nome)
            if valor is not None:
                _id_bom = nome
                return nome, float(valor)
        except Exception:
            continue
    _id_bom = None
    return None, None


def tempo_simulado():
    """Segundos do relogio do simulador. Se a build nao expuser, cai
    para o relogio real -- a taxa perde precisao se o multiplicador
    estiver ligado, e o cabecalho avisa."""
    try:
        return float(Environment.getTimeInSeconds()), True
    except Exception:
        return float(time()), False


def main():
    pinMode(PINO_TEMP, IN)
    print("=== DIAG TEMPERATURA ===")

    _, simulado = tempo_simulado()
    if not simulado:
        print("AVISO: relogio simulado indisponivel, usando o real.")
        print("       Nao ligue o multiplicador de tempo nesta rodada.")

    print("Limite do XML para Ambient Temperature: 5.0 C por hora simulada.")
    print("Se a coluna C/h colar em +5.0 ou -5.0, e a rampa (H1).")
    print("")
    print("  SENSOR(D{})  AMBIENTE     C/h      dt_sim   id".format(PINO_TEMP))
    print("  ----------  ----------  -------  -------  --------------------")

    global _anterior
    while True:
        bruto = analogRead(PINO_TEMP)
        sensor_c = para_celsius(bruto)
        nome, ambiente_c = ler_ambiente()
        agora, _ = tempo_simulado()

        taxa = "   --  "
        dt = "   --  "
        if ambiente_c is not None and _anterior is not None:
            delta_t = agora - _anterior[0]
            if delta_t > 0:
                dt = "{:7.1f}".format(delta_t)
                # C por hora simulada: delta de temperatura sobre delta
                # de tempo, em horas
                taxa = "{:+7.2f}".format(
                    (ambiente_c - _anterior[1]) / (delta_t / 3600.0)
                )

        print(
            "  {:6.2f} C    {}  {}  {}  {}".format(
                sensor_c,
                "{:6.2f} C  ".format(ambiente_c)
                if ambiente_c is not None
                else " sem id  ",
                taxa,
                dt,
                nome if nome else "-",
            )
        )

        if ambiente_c is not None:
            _anterior = (agora, ambiente_c)

        sleep(INTERVALO)


if __name__ == "__main__":
    main()
