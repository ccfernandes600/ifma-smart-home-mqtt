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


def reconexao_usa_cliente_novo(nome):
    """No PT, repetir connect() no mesmo TCPClient nunca conecta (medido em 03/11)."""
    def teste():
        z = carregar(nome, {"CO": 0.0, "CO2": 0.0, "Smoke": 0.0})
        m = z["m"]
        antes = m.cliente
        z["rede"]["conectado"] = False
        for _ in range(3):
            m.manter_conexao()
        confere(z["rede"]["tentativas"] == 1, "nao tentou reconectar")
        confere(m.cliente is not antes, "reconectou com o mesmo TCPClient")
        confere(z["rede"].get("fechados") == 1, "nao fechou a tentativa anterior")

    return teste


def conexao_nova_sobrevive_a_limpeza():
    """Conexao recem-aceita pode dar connected() falso no 1o ciclo (medido em 03/11)."""
    z = carregar("broker_central")
    m = z["m"]
    m.clientes.append(z["Cliente"]())
    z["rede"]["conectado"] = False
    m.limpar_clientes()
    confere(len(m.clientes) == 1, "removeu a conexao no primeiro ciclo")
    z["rede"]["conectado"] = True
    m.limpar_clientes()
    z["rede"]["conectado"] = False
    m.limpar_clientes()
    confere(len(m.clientes) == 1, "voltou a ficar conectada: precisava de novos 2 ciclos")
    m.limpar_clientes()
    confere(len(m.clientes) == 0, "conexao morta ficou na lista")


def setup_limpa_sobras(nome, saidas):
    """A saida de um pino sobrevive ao Stop (medido em 03/11): o setup e o 1o ciclo
    precisam deixar tudo em estado conhecido, com o ambiente em condicao normal."""
    def teste():
        z = carregar(nome, {"Water Level": 40.0})
        m = z["m"]
        z["entradas"][getattr(m, "TEMP", 0)] = TEMP_AMENA
        if hasattr(m, "UMID"):
            z["entradas"][m.UMID] = 600
        if hasattr(m, "LUZ"):
            z["entradas"][m.LUZ] = 1023
        for s in saidas:
            z["saidas"][getattr(m, s)] = m.HIGH  # sobra de uma execução anterior
        m.setup()
        for ciclo in ("processar_sensores", "verificar_perigo", "processar_ambiente"):
            if hasattr(m, ciclo):
                getattr(m, ciclo)()
        presas = [s for s in saidas if z["saidas"][getattr(m, s)] not in (m.LOW, "0", 0)]
        confere(not presas, "ficaram ligadas: {}".format(presas))

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


# --- Central: envio ao site público ----------------------------------------- #
def central_com_chave():
    z = carregar("broker_central")
    z["m"].NUVEM_CHAVE = "chave-de-teste"
    return z


def sem_chave_nao_toca_na_internet():
    z = carregar("broker_central")
    m = z["m"]
    confere(m.NUVEM_CHAVE == "", "o arquivo fonte traz uma chave")
    z["relogio"]["t"] = 1000
    m.enviar_nuvem()
    confere(z["nuvem"]["criados"] == 0, "criou cliente sem chave: abriria o aviso do PT")
    confere(not z["nuvem"]["posts"], "enviou sem chave")


def nuvem_envia_o_resumo():
    z = central_com_chave()
    m = z["m"]
    m.clientes.append(z["Cliente"]())
    m.modo_viagem = True
    publicacao(m, "casa/sala/temp", 27)
    z["relogio"]["t"] = 100
    m.enviar_nuvem()
    url, corpo = z["nuvem"]["posts"][-1]
    confere(url == m.NUVEM_URL and corpo["chave"] == "chave-de-teste", "url ou chave erradas")
    confere(corpo["estado"]["casa/sala/temp"] == 27, "estado nao foi")
    confere(corpo["modo"] == "viagem" and corpo["titulo"] == "MODO VIAGEM", "modo ou titulo errados")
    confere(corpo["conectados"] == 1 and corpo["publicando"] == 1, "contagens erradas")
    confere(corpo["lcd"] == ["MODO VIAGEM", "Monitorando"], "lcd: {}".format(corpo["lcd"]))


def nuvem_respeita_intervalo_e_pulso():
    z = central_com_chave()
    m = z["m"]
    posts = z["nuvem"]["posts"]
    z["relogio"]["t"] = 100
    m.enviar_nuvem()
    m.ao_responder_nuvem(200, "{}")
    publicacao(m, "casa/sala/temp", 27)
    z["relogio"]["t"] = 100 + m.NUVEM_INTERVALO - 1
    m.enviar_nuvem()
    confere(len(posts) == 1, "enviou antes do intervalo")
    z["relogio"]["t"] = 100 + m.NUVEM_INTERVALO
    m.enviar_nuvem()
    confere(len(posts) == 2, "nao enviou a mudanca")
    m.ao_responder_nuvem(200, "{}")
    enviado_em = z["relogio"]["t"]
    z["relogio"]["t"] = enviado_em + m.NUVEM_INTERVALO
    m.enviar_nuvem()
    confere(len(posts) == 2, "reenviou sem mudanca")
    z["relogio"]["t"] = enviado_em + m.NUVEM_PULSO
    m.enviar_nuvem()
    confere(len(posts) == 3, "sem o pulso, o site acharia que o simulador desligou")


def nuvem_nao_empilha_nem_prende():
    z = central_com_chave()
    m = z["m"]
    posts = z["nuvem"]["posts"]
    z["relogio"]["t"] = 100
    m.enviar_nuvem()
    z["relogio"]["t"] = 100 + m.NUVEM_ESPERA - 1
    publicacao(m, "casa/sala/temp", 27)
    m.enviar_nuvem()
    confere(len(posts) == 1, "empilhou envio sem resposta")
    z["relogio"]["t"] = 100 + m.NUVEM_ESPERA + 1
    m.enviar_nuvem()
    confere(len(posts) == 2, "ficou preso sem resposta")
    confere(z["nuvem"]["criados"] == 2, "nao trocou o cliente depois da falta de resposta")


def nuvem_falha_nao_derruba_a_central():
    z = central_com_chave()
    m = z["m"]
    z["nuvem"]["falhar"] = True
    z["relogio"]["t"] = 100
    m.enviar_nuvem()
    z["relogio"]["t"] = 200
    m.enviar_nuvem()
    m.ao_responder_nuvem(500, "erro")
    m.ao_responder_nuvem(500, "erro")
    avisos = [x for x in z["logs"] if "Nuvem" in x and "falhou" in x]
    confere(len(avisos) == 1, "repetiu o aviso: {}".format(avisos))
    z["nuvem"]["falhar"] = False
    z["relogio"]["t"] = 300
    m.enviar_nuvem()
    m.ao_responder_nuvem(200, "{}")
    confere(any("Nuvem" in x and "ok" in x for x in z["logs"]), "nao registrou a volta")


def nuvem_sobrevive_a_publicacao_simultanea():
    """As zonas publicam em outra linha de execução: montar o JSON pode dar
    "dict changed size during iteration" (medido em 04/11). A Central não pode cair."""
    z = central_com_chave()
    m = z["m"]
    original = m.dumps

    def falha(*a, **k):
        raise RuntimeError("dictionary changed size during iteration")

    m.dumps = falha
    z["relogio"]["t"] = 100
    m.enviar_nuvem()  # não pode propagar a exceção
    confere(any("falhou" in x for x in z["logs"]), "a falha nao foi registrada")
    m.dumps = original
    z["relogio"]["t"] = 100 + m.NUVEM_INTERVALO
    m.enviar_nuvem()
    confere(len(z["nuvem"]["posts"]) == 1, "nao tentou de novo no ciclo seguinte")


def garagem_reconhece_o_carro_ligado():
    """Com o clima de São Luís, o Old Car ligado deixa o CO em torno de 0,008 % e não
    acumula (medido em 04/11). Com o ar limpo, o CO é 0 e a rampa não pode subir."""
    z = carregar("zona_garagem", {"CO": 0.0, "CO2": 0.0})
    m = z["m"]
    confere(not m.carro_ligado(), "ar limpo contou como carro ligado")
    z["env"]["CO"] = 0.008
    confere(m.carro_ligado(), "nao reconheceu o carro ligado")


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
    m.atualizar_agua(40)  # nível intermediário, em cm: nada muda
    confere(not any("Irrigacao" in x or "Dreno" in x for x in z["logs"]), "log falso na partida")


def jardim_le_agua_do_ambiente():
    """Water Level e Wind não têm GPIO (Direct Control: N/A): analogRead dá 0."""
    z = carregar("zona_jardim", {"Water Level": 42.0, "Wind Speed": 12.3, "Atmospheric Pressure": 101.3})
    m = z["m"]
    m.processar_sensores()
    confere(z["saidas"][m.IRRIGACAO] == "0", "irrigou com 42 cm de agua")
    publicados = {e["topic"].split("/")[-1]: e["payload"] for e in z["enviados"]}
    confere(publicados["agua"] == 42, "agua publicada: {}".format(publicados["agua"]))
    confere(publicados["pressao"] == 101.3, "pressao publicada: {}".format(publicados["pressao"]))


def jardim_alagado_drena():
    z = carregar("zona_jardim", {"Water Level": 88.0})
    m = z["m"]
    m.processar_sensores()
    confere(z["saidas"][m.DRENO] == "1", "nao drenou com 88 cm")
    z["env"]["Water Level"] = 12.0
    m.processar_sensores()
    confere(z["saidas"][m.DRENO] == "0", "dreno nao desligou com 12 cm")
    confere(z["saidas"][m.IRRIGACAO] == "1", "nao irrigou com 12 cm")


caso("Quarto: umidificador nao religa em modo viagem", umidificador_fica_desligado_em_viagem)
caso("Quarto: umidificador volta depois da viagem", umidificador_volta_apos_viagem)
for zona in ("zona_garagem", "zona_sala", "zona_quarto", "zona_perimetro"):
    caso("{}: movimento perdido e reenviado".format(zona), movimento_perdido_e_reenviado(zona))
for zona in ("zona_sala", "zona_cozinha", "zona_quarto", "zona_jardim", "zona_garagem", "zona_perimetro"):
    caso("{}: reconexao volta a publicar o estado".format(zona), reconexao_republica(zona))
for zona in ("zona_sala", "zona_cozinha", "zona_quarto", "zona_jardim", "zona_garagem", "zona_perimetro"):
    caso("{}: reconexao usa um TCPClient novo".format(zona), reconexao_usa_cliente_novo(zona))
for zona, saidas in (
    ("zona_sala", ("AC", "FAN")),
    ("zona_quarto", ("AC", "UMIDIFICADOR", "LED", "JANELA")),
    ("zona_cozinha", ("SPRINKLER", "JANELA", "FAN", "ALARME")),
    ("zona_jardim", ("IRRIGACAO", "DRENO")),
    ("zona_garagem", ("PORTA", "FAN", "ALARME")),
    ("zona_perimetro", ("PORTA", "SIRENE", "CAMERA")),
):
    caso("{}: setup limpa sobras da execucao anterior".format(zona), setup_limpa_sobras(zona, saidas))
caso("Central: sem chave nao toca na internet", sem_chave_nao_toca_na_internet)
caso("Central: envia o resumo ao site", nuvem_envia_o_resumo)
caso("Central: envio respeita intervalo e pulso", nuvem_respeita_intervalo_e_pulso)
caso("Central: envio nao empilha nem prende", nuvem_nao_empilha_nem_prende)
caso("Central: falha de rede nao derruba", nuvem_falha_nao_derruba_a_central)
caso("Central: publicacao simultanea nao derruba", nuvem_sobrevive_a_publicacao_simultanea)
caso("Garagem: reconhece o carro ligado", garagem_reconhece_o_carro_ligado)
caso("Central: conexao nova sobrevive a limpeza", conexao_nova_sobrevive_a_limpeza)
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
caso("Jardim: nivel de agua vem do ambiente", jardim_le_agua_do_ambiente)
caso("Jardim: alagado drena e seco irriga", jardim_alagado_drena)

sys.exit(1 if falhas else 0)
