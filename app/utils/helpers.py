# -*- coding: utf-8 -*-
"""
Funções Auxiliares (Helpers)

Este módulo contém funções utilitárias usadas em diferentes partes da aplicação,
principalmente nos controladores, para realizar cálculos, formatações e buscas
comuns relacionadas aos dados de ponto, feriados, afastamentos e atividades.
"""

import calendar
import logging
from datetime import date, datetime, time, timedelta

# Importar modelos necessários para buscas (cuidado com imports circulares)
# É mais seguro importar dentro das funções ou garantir que não haja ciclos.
# from app.models import Feriado, Afastamento, Atividade # Exemplo

logger = logging.getLogger(__name__)

def formatar_timedelta(delta, mostrar_sinal=False):
    """
    Formata um objeto timedelta no formato HH:MM ou +HH:MM / -HH:MM.

    Args:
        delta (timedelta or None): O timedelta a ser formatado.
        mostrar_sinal (bool): Se True, adiciona '+' para valores positivos.

    Returns:
        str: String formatada (ex: "08:30", "+01:15", "-00:45") ou "--:--" se delta for None.
    """
    if delta is None:
        return "--:--"

    try:
        total_seconds = int(delta.total_seconds())
        sign = ""
        if total_seconds < 0:
            sign = "-"
        elif mostrar_sinal:
            sign = "+"

        total_seconds = abs(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return f"{sign}{hours:02d}:{minutes:02d}"
    except Exception as e:
        logger.error(f"Erro ao formatar timedelta {delta}: {e}")
        return "Erro"


def calcular_horas_trabalhadas_dia(pontos_dia):
    """
    Calcula as horas trabalhadas em um dia com base em uma lista de pontos ordenados.

    Args:
        pontos_dia (list[Ponto]): Lista de objetos Ponto do dia, ordenados por hora.

    Returns:
        tuple[timedelta, list[str]]: Uma tupla contendo:
            - O total de horas trabalhadas (timedelta).
            - Uma lista de comentários/avisos (ex: "Saída sem Entrada").
    """
    horas_trabalhadas = timedelta(0)
    entrada_pendente = None
    comentarios = []

    if not pontos_dia:
        return horas_trabalhadas, comentarios

    # Garante que a lista está ordenada por timestamp (ou hora)
    pontos_dia.sort(key=lambda p: p.timestamp)

    for ponto in pontos_dia:
        if ponto.tipo == 'Entrada':
            if entrada_pendente is None:
                entrada_pendente = ponto.timestamp
            else:
                # Entrada dupla sem saída intermediária - ignora a segunda entrada? Ou loga?
                comentarios.append(f"Entrada às {ponto.hora.strftime('%H:%M')} sem Saída anterior.")
                # Mantém a primeira entrada pendente
        elif ponto.tipo == 'Saída':
            if entrada_pendente is not None:
                horas_trabalhadas += (ponto.timestamp - entrada_pendente)
                entrada_pendente = None # Reseta a entrada pendente
            else:
                # Saída sem entrada correspondente
                 comentarios.append(f"Saída às {ponto.hora.strftime('%H:%M')} sem Entrada correspondente.")

    # Se terminou o dia com uma entrada pendente (esqueceu de bater saída)
    if entrada_pendente is not None:
        comentarios.append(f"Entrada às {entrada_pendente.strftime('%H:%M')} sem Saída correspondente no final do dia.")
        # Opcional: Poderia calcular até um horário limite (ex: 23:59) ou apenas ignorar.
        # Por padrão, não adiciona tempo por entrada sem saída.

    return horas_trabalhadas, comentarios


def calcular_saldo_banco_horas(user_id, ano=None, mes=None):
    """
    Calcula o saldo total ou mensal do banco de horas para um usuário.

    Args:
        user_id (int): ID do usuário.
        ano (int, optional): Ano para cálculo mensal. Default None (calcula total).
        mes (int, optional): Mês para cálculo mensal. Default None (calcula total).

    Returns:
        timedelta: Saldo de horas (positivo ou negativo).
    """
    from app.models.ponto import Ponto, Afastamento, Atividade
    from app.models.feriado import Feriado
    from app.models.user import User # Importa User aqui

    user = User.query.get(user_id)
    if not user:
        logger.warning(f"Usuário {user_id} não encontrado para cálculo de saldo.")
        return timedelta(0)

    jornada_diaria = timedelta(hours=user.jornada_diaria)
    saldo_total = timedelta(0)

    query = Ponto.query.filter_by(user_id=user_id)
    if ano and mes:
        inicio_periodo = date(ano, mes, 1)
        fim_periodo = date(ano, mes, calendar.monthrange(ano, mes)[1])
        query = query.filter(Ponto.data >= inicio_periodo, Ponto.data <= fim_periodo)
        logger.info(f"Calculando saldo para {user.username} - {mes:02d}/{ano}")
    elif ano: # Calcula para o ano inteiro se só o ano for fornecido
        inicio_periodo = date(ano, 1, 1)
        fim_periodo = date(ano, 12, 31)
        query = query.filter(Ponto.data >= inicio_periodo, Ponto.data <= fim_periodo)
        logger.info(f"Calculando saldo para {user.username} - Ano {ano}")
    else:
        # Calcula saldo total (desde o início)
        logger.info(f"Calculando saldo total para {user.username}")
        # Define um período inicial razoável se necessário, ou busca todos os pontos
        # inicio_periodo = date(2000, 1, 1) # Exemplo
        # fim_periodo = date.today()
        # query = query.filter(Ponto.data >= inicio_periodo, Ponto.data <= fim_periodo)
        pass # Sem filtro de data para saldo total

    pontos_periodo = query.order_by(Ponto.data, Ponto.hora).all()

    # Agrupa pontos por dia
    pontos_por_dia = {}
    datas_com_ponto = set()
    if pontos_periodo:
        for ponto in pontos_periodo:
            if ponto.data not in pontos_por_dia:
                pontos_por_dia[ponto.data] = []
            pontos_por_dia[ponto.data].append(ponto)
            datas_com_ponto.add(ponto.data)

        # Define o intervalo de datas a serem consideradas (para incluir dias sem ponto)
        if ano and mes:
            primeiro_dia = inicio_periodo
            ultimo_dia = fim_periodo
        elif pontos_periodo: # Se não for mensal, pega do primeiro ao último ponto
            primeiro_dia = min(datas_com_ponto)
            ultimo_dia = max(datas_com_ponto)
        else: # Sem pontos no período
             return timedelta(0)

        # Busca feriados, afastamentos e atividades uma vez para o período
        feriados = {f.data: f.descricao for f in Feriado.query.filter(Feriado.data >= primeiro_dia, Feriado.data <= ultimo_dia).all()}
        afastamentos = Afastamento.query.filter(Afastamento.user_id == user_id, Afastamento.data_fim >= primeiro_dia, Afastamento.data_inicio <= ultimo_dia).all()
        atividades = {a.data: a.descricao for a in Atividade.query.filter(Atividade.user_id == user_id, Atividade.data >= primeiro_dia, Atividade.data <= ultimo_dia).all()}

        # Itera por todos os dias do período
        current_date = primeiro_dia
        while current_date <= ultimo_dia:
            dia_semana = current_date.weekday() # Segunda=0, Domingo=6
            e_fim_semana = dia_semana >= 5
            e_feriado = current_date in feriados
            e_afastamento = any(a.data_inicio <= current_date <= a.data_fim for a in afastamentos)
            e_atividade = current_date in atividades

            pontos_do_dia = pontos_por_dia.get(current_date, [])
            horas_trabalhadas, _ = calcular_horas_trabalhadas_dia(pontos_do_dia)

            saldo_dia = timedelta(0)
            # Calcula saldo apenas para dias úteis sem afastamento/atividade
            if not e_fim_semana and not e_feriado and not e_afastamento and not e_atividade:
                 saldo_dia = horas_trabalhadas - jornada_diaria
            # Para outros dias, o saldo é apenas as horas trabalhadas (horas extras)
            elif horas_trabalhadas > timedelta(0):
                 saldo_dia = horas_trabalhadas

            saldo_total += saldo_dia
            current_date += timedelta(days=1)

    logger.info(f"Saldo calculado para {user.username} ({'Total' if not mes else f'{mes:02d}/{ano}'}): {formatar_timedelta(saldo_total, True)}")
    return saldo_total


def get_dias_uteis_no_mes(ano, mes):
    """Retorna um conjunto de datas que são dias úteis no mês/ano especificado."""
    dias_uteis = set()
    num_dias = calendar.monthrange(ano, mes)[1]
    feriados_mes = get_feriados_no_mes(ano, mes) # Busca feriados

    for dia in range(1, num_dias + 1):
        data = date(ano, mes, dia)
        # Verifica se não é fim de semana (Seg=0 a Sex=4) e não é feriado
        if data.weekday() < 5 and data not in feriados_mes:
            dias_uteis.add(data)
    return dias_uteis

def get_feriados_no_mes(ano, mes):
    """Retorna um dicionário de feriados {data: descricao} para o mês/ano."""
    from app.models.feriado import Feriado # Import local para evitar ciclos
    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    feriados = Feriado.query.filter(Feriado.data >= inicio_mes, Feriado.data <= fim_mes).all()
    return {f.data: f.descricao for f in feriados}

def get_afastamentos_no_mes(user_id, ano, mes):
    """Retorna uma lista de objetos Afastamento que ocorrem no mês/ano para o usuário."""
    from app.models.ponto import Afastamento # Import local
    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    # Busca afastamentos que *interceptam* o mês
    afastamentos = Afastamento.query.filter(
        Afastamento.user_id == user_id,
        Afastamento.data_fim >= inicio_mes,   # Termina no mês ou depois
        Afastamento.data_inicio <= fim_mes # Começa no mês ou antes
    ).all()
    return afastamentos

def get_atividades_no_mes(user_id, ano, mes):
    """Retorna uma lista de objetos Atividade que ocorrem no mês/ano para o usuário."""
    from app.models.ponto import Atividade # Import local
    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    atividades = Atividade.query.filter(
        Atividade.user_id == user_id,
        Atividade.data >= inicio_mes,
        Atividade.data <= fim_mes
    ).all()
    return atividades
