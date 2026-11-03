#!/usr/bin/env python3
"""Testes de comportamento dos scripts, rodando com dublês do Packet Tracer.

Cada teste reproduz um defeito achado na revisão de 03/11/2026
(docs/REVISAO_ESTATICA_2026-11-03.md). Chamado pelo verificar.py; imprime uma linha
por teste e sai com 1 se algum falhar.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dubles import carregar, comando, publicacao  # noqa: E402

TEMP_AMENA = 650  # raw de cerca de 27 C
QUENTE = 680  # raw de cerca de 33 C
falhas = 0


def caso(nome, fn):
    global falhas
    try:
        fn()
        print("  ok    " + nome)
    except Exception as erro:  # noqa: BLE001
        falhas += 1
        print("  FALHA {} -- {}".format(nome, erro))


def confere(condicao, mensagem):
    if not condicao:
        raise AssertionError(mensagem)


def central_com_perimetro():
    """Central com o Perímetro conectado."""
    z = carregar("broker_central")
    z["m"].clientes.append(z["Cliente"]())
    return z


# --- Quarto: modo viagem ---------------------------------------------------- #
def umidificador_fica_desligado_em_viagem():
    z = carregar("zona_quarto")
    m = z["m"]
    z["entradas"][m.UMID] = 204  # 20 %
    z["entradas"][m.TEMP] = TEMP_AMENA
    m.processar_sensores()
    confere(z["saidas"][m.UMIDIFICADOR] == m.HIGH, "ar seco deveria ligar o umidificador")
    comando(m, "casa/todas/cmd/modo", True)
    m.processar_sensores()
    confere(z["saidas"][m.UMIDIFICADOR] == m.LOW, "religou em modo viagem")


def umidificador_volta_apos_viagem():
    z = carregar("zona_quarto")
    m = z["m"]
    z["entradas"][m.UMID] = 204
    z["entradas"][m.TEMP] = TEMP_AMENA
    comando(m, "casa/todas/cmd/modo", True)
    m.processar_sensores()
    comando(m, "casa/todas/cmd/modo", False)
    m.processar_sensores()
    confere(z["saidas"][m.UMIDIFICADOR] == m.HIGH, "nao voltou ao sair do modo viagem")


# --- Movimento perdido ------------------------------------------------------ #
def movimento_perdido_e_reenviado(nome):
    def teste():
        z = carregar(nome)
        m = z["m"]
        z["entradas"][m.MOV] = m.HIGH
        m.processar_movimento()
        confere(z["enviados"][-1]["payload"] == 1, "movimento=1 nao publicado")
        z["rede"]["conectado"] = False
        z["relogio"]["t"] = m.DURACAO_MOVIMENTO + 1
        m.verificar_movimento()
        z["rede"]["conectado"] = True
        m.reenviar_estado()
        ultimos = [e for e in z["enviados"] if e["topic"].endswith("/movimento")]
        confere(ultimos[-1]["payload"] == 0, "movimento=0 nunca foi reenviado")

    return teste


# --- Reconexão -------------------------------------------------------------- #
def reconexao_republica(nome):
    def teste():
        z = carregar(nome, {"CO": 0.0, "CO2": 0.0, "Smoke": 0.0})
        m = z["m"]
        z["entradas"][0] = TEMP_AMENA
        m.anterior["temp"] = 27  # valor que a Central antiga já conhecia
        z["rede"]["conectado"] = False
        m.manter_conexao()
        z["rede"]["conectado"] = True
        m.manter_conexao()
        confere("temp" not in m.anterior, "reconectou sem esquecer o que ja tinha publicado")

    return teste


# --- Central: situação da casa ---------------------------------------------- #
def movimento_interno_em_viagem_e_intrusao():
    for topico, onde in (("casa/sala/movimento", "Na sala"), ("casa/quarto/movimento", "No quarto")):
        z = carregar("broker_central")
        m = z["m"]
        m.modo_viagem = True
        publicacao(m, topico, 1)
        confere(m._ultima_tela == ("INTRUSAO!", onde), "tela: {}".format(m._ultima_tela))


def movimento_interno_em_casa_nao_alarma():
    z = carregar("broker_central")
    m = z["m"]
    publicacao(m, "casa/sala/movimento", 1)
    confere(m.situacao_da_casa()[0] == "CASA OK", "gente em casa virou alerta")


def intrusao_aciona_speaker():
    z = carregar("broker_central")
    m = z["m"]
    m.modo_viagem = True
    publicacao(m, "casa/garagem/movimento", 1)
    confere(z["saidas"][m.SPEAKER] == m.HIGH, "Speaker calado na intrusao")


def movimento_externo_em_casa_nao_toca_speaker():
    z = carregar("broker_central")
    m = z["m"]
    publicacao(m, "casa/garagem/movimento", 1)
    confere(z["saidas"][m.SPEAKER] == m.LOW, "Speaker tocou sem intrusao")


# --- Central: RFID ---------------------------------------------------------- #
def tela_de_acesso_tem_prazo():
    z = central_com_perimetro()
    m = z["m"]
    m.processar_rfid(1005)
    publicacao(m, "casa/sala/temp", 27)
    confere(m._ultima_tela[0] == "ACESSO OK", "tela sumiu com a porta aberta")
    z["relogio"]["t"] = m.DURACAO_TELA_RFID + 1
    m.verificar_tela_rfid()
    confere(m._ultima_tela[0] == "CASA OK", "tela nao voltou apos o prazo")


def cartao_negado_nao_fica_preso():
    z = central_com_perimetro()
    m = z["m"]
    m.processar_rfid(9999)
    confere(m._ultima_tela[0] == "CARTAO NEGADO", "tela: {}".format(m._ultima_tela))
    z["relogio"]["t"] = m.DURACAO_TELA_RFID + 1
    m.verificar_tela_rfid()
    confere(m._ultima_tela[0] == "CASA OK", "CARTAO NEGADO ficou preso")


def alerta_vence_tela_de_acesso():
    z = central_com_perimetro()
    m = z["m"]
    m.processar_rfid(1005)
    publicacao(m, "casa/cozinha/fumaca", 40)
    confere(m._ultima_tela[0] == "ALERTA DE GAS", "gas nao apareceu no LCD")


def fechamento_nao_entregue_e_repetido():
    z = central_com_perimetro()
    m = z["m"]
    m.processar_rfid(1005)
    z["rede"]["conectado"] = False
    z["relogio"]["t"] = m.DURACAO_PORTA_RFID + 1
    m.verificar_porta_rfid()
    confere(m._porta_fecha_em != 0, "desistiu de fechar a porta")
    z["rede"]["conectado"] = True
    z["relogio"]["t"] = m._porta_fecha_em + 1
    m.verificar_porta_rfid()
    confere(z["enviados"][-1]["payload"] == 0, "porta nao recebeu o fechamento")
    confere(m._porta_fecha_em == 0, "prazo nao foi encerrado apos fechar")


def json_invalido_fica_no_log():
    z = carregar("broker_central")
    m = z["m"]
    m.ao_receber('{"topic":"a","payload":1}{"topic":"b","payload":2}')
    confere(any("descartada" in linha for linha in z["logs"]), "mensagem perdida em silencio")


# --- Zonas: estado inicial e logs ------------------------------------------- #
def cozinha_nasce_com_atuadores_desligados():
    z = carregar("zona_cozinha", {"Smoke": 0.0, "CO": 0.0})
    m = z["m"]
    z["saidas"][m.ALARME] = m.HIGH  # sobra de uma execução anterior
    z["saidas"][m.SPRINKLER] = m.HIGH
    m.setup()
    confere(z["saidas"][m.ALARME] == m.LOW, "alarme ficou ligado")
    confere(z["saidas"][m.SPRINKLER] == m.LOW, "sprinkler ficou ligado")


def quarto_nasce_com_luz_apagada():
    z = carregar("zona_quarto")
    m = z["m"]
    z["saidas"][m.LED] = m.HIGH
    m.setup()
    confere(z["saidas"][m.LED] == m.LOW, "luz de presenca ficou acesa")


def jardim_nao_loga_mudanca_na_partida():
    z = carregar("zona_jardim")
    m = z["m"]
    m.atualizar_agua(400)  # nível intermediário: nada muda
    confere(not any("Irrigacao" in x or "Dreno" in x for x in z["logs"]), "log falso na partida")


caso("Quarto: umidificador nao religa em modo viagem", umidificador_fica_desligado_em_viagem)
caso("Quarto: umidificador volta depois da viagem", umidificador_volta_apos_viagem)
for zona in ("zona_garagem", "zona_sala", "zona_quarto", "zona_perimetro"):
    caso("{}: movimento perdido e reenviado".format(zona), movimento_perdido_e_reenviado(zona))
for zona in ("zona_sala", "zona_cozinha", "zona_quarto", "zona_jardim", "zona_garagem", "zona_perimetro"):
    caso("{}: reconexao volta a publicar o estado".format(zona), reconexao_republica(zona))
caso("Central: movimento na sala/quarto em viagem e intrusao", movimento_interno_em_viagem_e_intrusao)
caso("Central: movimento na sala com gente em casa nao alarma", movimento_interno_em_casa_nao_alarma)
caso("Central: intrusao aciona o Speaker", intrusao_aciona_speaker)
caso("Central: movimento em casa nao aciona o Speaker", movimento_externo_em_casa_nao_toca_speaker)
caso("Central: tela de acesso dura o prazo", tela_de_acesso_tem_prazo)
caso("Central: CARTAO NEGADO nao fica preso", cartao_negado_nao_fica_preso)
caso("Central: alerta de gas vence a tela de acesso", alerta_vence_tela_de_acesso)
caso("Central: fechamento nao entregue e repetido", fechamento_nao_entregue_e_repetido)
caso("Central: JSON invalido fica registrado no log", json_invalido_fica_no_log)
caso("Cozinha: nasce com os atuadores desligados", cozinha_nasce_com_atuadores_desligados)
caso("Quarto: nasce com a luz apagada", quarto_nasce_com_luz_apagada)
caso("Jardim: sem log falso de mudanca na partida", jardim_nao_loga_mudanca_na_partida)

sys.exit(1 if falhas else 0)
