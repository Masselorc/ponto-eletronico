# -*- coding: utf-8 -*-
import logging
from datetime import datetime, date, timedelta, time
from calendar import monthrange
from app import db # Importa db diretamente
from app.models.user import User
from app.models.ponto import Ponto, Atividade
from app.models.feriado import Feriado
from sqlalchemy import extract # Necessário para filtros de data

# Configura um logger para este módulo
logger = logging.getLogger(__name__)

def calcular_horas(data_ref, entrada, saida, saida_almoco=None, retorno_almoco=None):
    """Calcula as horas trabalhadas em um dia, considerando o almoço."""
    if not entrada or not saida:
        return None

    try:
        dt_entrada = datetime.combine(data_ref, entrada)
        dt_saida = datetime.combine(data_ref, saida)

        # Se a saída for no dia seguinte (ex: virou meia-noite)
        if dt_saida < dt_entrada:
            dt_saida += timedelta(days=1)

        total_seconds = (dt_saida - dt_entrada).total_seconds()

        if saida_almoco and retorno_almoco:
            dt_saida_almoco = datetime.combine(data_ref, saida_almoco)
            dt_retorno_almoco = datetime.combine(data_ref, retorno_almoco)

            # Se o retorno do almoço for no dia seguinte
            if dt_retorno_almoco < dt_saida_almoco:
                dt_retorno_almoco += timedelta(days=1)

            # Verifica se o intervalo de almoço está dentro do período de trabalho
            if dt_saida_almoco >= dt_entrada and dt_retorno_almoco <= dt_saida:
                almoco_seconds = (dt_retorno_almoco - dt_saida_almoco).total_seconds()
                # Garante que o almoço não seja negativo e tenha pelo menos 1 hora (3600s)
                if almoco_seconds >= 3600:
                     total_seconds -= almoco_seconds
                else:
                     # Se o almoço for menor que 1h, não desconta ou loga um aviso
                     logger.warning(f"Intervalo de almoço inválido ou menor que 1h para {data_ref}. Não descontado.")
            else:
                 logger.warning(f"Intervalo de almoço fora do período de trabalho para {data_ref}. Não descontado.")


        # Retorna horas com duas casas decimais
        return round(total_seconds / 3600, 2)

    except (TypeError, ValueError) as e:
        logger.error(f"Erro ao calcular horas para {data_ref} com horários: E={entrada}, S={saida}, SA={saida_almoco}, RA={retorno_almoco}. Erro: {e}")
        return None # Retorna None em caso de erro no cálculo


def _get_relatorio_mensal_data(user_id, mes, ano, order_desc=True):
    """Busca e calcula dados para o relatório mensal."""
    usuario = User.query.get_or_404(user_id) # get_or_404 pode precisar do contexto da app, talvez get() seja melhor
    # Alternativa: usuario = db.session.get(User, user_id) # A partir SQLAlchemy 1.4+
    # Ou: usuario = User.query.get(user_id) # Clássico
    if not usuario:
         logger.error(f"Usuário com ID {user_id} não encontrado ao buscar dados do relatório.")
         raise ValueError(f"Usuário ID {user_id} não encontrado.")

    try:
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
    except ValueError:
        logger.error(f"Data inválida fornecida: Mês={mes}, Ano={ano}")
        raise ValueError("Mês ou ano inválido.")

    # Busca registros de ponto
    query_ponto = Ponto.query.filter(
        Ponto.user_id == user_id,
        Ponto.data >= primeiro_dia,
        Ponto.data <= ultimo_dia
    )
    if order_desc:
        query_ponto = query_ponto.order_by(Ponto.data.desc())
    else:
        query_ponto = query_ponto.order_by(Ponto.data.asc())
    registros = query_ponto.all()

    # Busca feriados
    feriados = Feriado.query.filter(
        extract('year', Feriado.data) == ano,
        extract('month', Feriado.data) == mes
    ).all()
    feriados_dict = {f.data: f.descricao for f in feriados}
    feriados_datas = set(feriados_dict.keys())

    # Busca atividades (otimizado)
    ponto_ids = [r.id for r in registros]
    atividades_por_ponto = {}
    if ponto_ids: # Só busca atividades se houver pontos
        atividades = Atividade.query.filter(Atividade.ponto_id.in_(ponto_ids)).all()
        for atv in atividades:
            if atv.ponto_id not in atividades_por_ponto:
                atividades_por_ponto[atv.ponto_id] = []
            atividades_por_ponto[atv.ponto_id].append(atv.descricao)

    # Dicionário de registros para acesso rápido
    registros_por_data = {r.data: r for r in registros}

    # Cálculo de estatísticas
    dias_uteis_potenciais = 0
    dias_afastamento = 0
    dias_trabalhados = 0
    horas_trabalhadas = 0.0

    for dia_num in range(1, ultimo_dia.day + 1):
        data_atual = date(ano, mes, dia_num)
        # Considera dia útil se não for fim de semana E não for feriado
        if data_atual.weekday() < 5 and data_atual not in feriados_datas:
            dias_uteis_potenciais += 1
            registro_dia = registros_por_data.get(data_atual)
            # Conta como afastamento se for dia útil E tiver registro marcado como afastamento
            if registro_dia and registro_dia.afastamento:
                dias_afastamento += 1

    # Calcula dias e horas trabalhadas (apenas em dias que deveriam ser úteis)
    for r_data, r_obj in registros_por_data.items():
        # Só conta se NÃO for afastamento E tiver horas calculadas
        if not r_obj.afastamento and r_obj.horas_trabalhadas is not None:
             # E se o dia do registro era um dia útil potencial
             if r_data.weekday() < 5 and r_data not in feriados_datas:
                 dias_trabalhados += 1
                 horas_trabalhadas += r_obj.horas_trabalhadas

    # Carga horária devida = (Dias úteis potenciais - dias de afastamento nesses dias úteis) * 8h
    carga_horaria_devida = (dias_uteis_potenciais - dias_afastamento) * 8.0
    saldo_horas = horas_trabalhadas - carga_horaria_devida
    media_diaria = horas_trabalhadas / dias_trabalhados if dias_trabalhados > 0 else 0.0

    nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    nome_mes = nomes_meses[mes]

    # Navegação entre meses
    mes_anterior, ano_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano)
    proximo_mes, proximo_ano = (1, ano + 1) if mes == 12 else (mes + 1, ano)

    return {
        'usuario': usuario,
        'registros': registros,
        'registros_por_data': registros_por_data,
        'mes_atual': mes,
        'ano_atual': ano,
        'nome_mes': nome_mes,
        'dias_uteis': dias_uteis_potenciais,
        'dias_trabalhados': dias_trabalhados,
        'dias_afastamento': dias_afastamento,
        'horas_trabalhadas': horas_trabalhadas,
        'carga_horaria_devida': carga_horaria_devida,
        'saldo_horas': saldo_horas,
        'media_diaria': media_diaria,
        'feriados_dict': feriados_dict,
        'feriados_datas': feriados_datas,
        'atividades_por_ponto': atividades_por_ponto,
        'ultimo_dia': ultimo_dia,
        'mes_anterior': mes_anterior,
        'ano_anterior': ano_anterior,
        'proximo_mes': proximo_mes,
        'proximo_ano': proximo_ano,
        'date_obj': date # Passa o construtor date para o template
    }
